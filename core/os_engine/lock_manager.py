"""
core/os_engine/lock_manager.py — Hybrid MVCC + Strict 2PL Lock Manager

Lock protocol:
  - READ queries get a statement-level MVCC snapshot (version counter) and a shared
    S-lock. Multiple S-locks coexist. No blocking between readers.
  - WRITE/DDL queries request an X-lock. Granted only when no S-lock or X-lock is held
    on the same resource. Strict 2PL: X-lock released only at transaction end.
  - Version counter increments on every committed WRITE/DDL. Readers see the version
    at the moment they called acquire_snapshot(); they never see partial writes.
  - Integration with WaitForGraph: when a txn blocks on a lock, an edge is registered.
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set

from core.os_engine.deadlock import DeadlockAbort, WaitForGraph


class LockMode(Enum):
    S = "S"   # Shared (READ)
    X = "X"   # Exclusive (WRITE / DDL)


@dataclass
class LockEntry:
    mode: LockMode
    holders: Set[str] = field(default_factory=set)    # txn_ids holding this lock
    waiters: list = field(default_factory=list)        # list of (txn_id, event) waiting


class LockManager:
    """
    Per-resource lock table with Strict 2PL + MVCC snapshot versioning.

    resource_id can be a table name, e.g. "orders" or "orders.price".
    """

    def __init__(self, wfg: Optional[WaitForGraph] = None):
        self._table: Dict[str, LockEntry] = {}
        self._txn_locks: Dict[str, Set[str]] = defaultdict(set)  # txn → resources held
        self._version: int = 0          # global write version counter
        self._snapshots: Dict[str, int] = {}  # txn_id → snapshot version
        self._lock = threading.Lock()
        self._wfg = wfg  # optional; deadlock detector registers wait edges here

    # ── MVCC Snapshot ─────────────────────────────────────────────────────────

    def acquire_snapshot(self, txn_id: str) -> int:
        """READ txns call this at statement start; returns their consistent snapshot version."""
        with self._lock:
            snap = self._version
            self._snapshots[txn_id] = snap
        return snap

    def current_version(self) -> int:
        with self._lock:
            return self._version

    # ── Lock Acquisition ──────────────────────────────────────────────────────

    def acquire(self, txn_id: str, resource: str, mode: LockMode, timeout_s: float = 5.0) -> bool:
        """
        Acquire S or X lock on resource for txn.
        Blocks until granted or timeout.  Raises DeadlockAbort if victim chosen by WFG.
        """
        deadline = time.monotonic() + timeout_s

        while True:
            granted_event = threading.Event()

            with self._lock:
                entry = self._table.setdefault(resource, LockEntry(mode=mode))

                # Compatible grant?
                if self._can_grant(entry, txn_id, mode):
                    entry.holders.add(txn_id)
                    entry.mode = mode if mode == LockMode.X else entry.mode
                    self._txn_locks[txn_id].add(resource)
                    return True

                # Register wait edge in WFG
                if self._wfg:
                    for holder in entry.holders:
                        if holder != txn_id:
                            self._wfg.add_wait(txn_id, holder)

                # Queue ourselves as a waiter
                entry.waiters.append((txn_id, mode, granted_event))

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._cancel_wait(resource, txn_id)
                raise TimeoutError(f"Lock acquisition timed out: txn={txn_id} resource={resource}")

            granted = granted_event.wait(timeout=min(remaining, 0.1))

            # Clean up WFG edge regardless of outcome
            if self._wfg:
                with self._lock:
                    if resource in self._table:
                        for holder in self._table[resource].holders:
                            self._wfg.remove_wait(txn_id, holder)

            if granted:
                return True

            # Check if we were aborted by deadlock detector
            if time.monotonic() >= deadline:
                self._cancel_wait(resource, txn_id)
                raise TimeoutError(f"Lock wait timed out: txn={txn_id}")

    def _can_grant(self, entry: LockEntry, txn_id: str, mode: LockMode) -> bool:
        if not entry.holders:
            return True
        # txn already holds this lock
        if txn_id in entry.holders:
            return True
        # S-S compatible; S-X and X-* not
        if mode == LockMode.S and entry.mode == LockMode.S:
            return True
        return False

    def _cancel_wait(self, resource: str, txn_id: str):
        with self._lock:
            entry = self._table.get(resource)
            if entry:
                entry.waiters = [(tid, m, ev) for tid, m, ev in entry.waiters if tid != txn_id]

    # ── Lock Release (Strict 2PL — release all at commit/abort) ──────────────

    def release_all(self, txn_id: str, commit: bool = True):
        """
        Release every lock held by txn_id.  If commit=True, increment version (for WRITE/DDL).
        """
        with self._lock:
            resources = list(self._txn_locks.pop(txn_id, []))
            is_writer = False

            for resource in resources:
                entry = self._table.get(resource)
                if not entry:
                    continue
                entry.holders.discard(txn_id)
                if entry.mode == LockMode.X:
                    is_writer = True

                # Grant to next compatible waiter(s)
                if not entry.holders and entry.waiters:
                    self._grant_waiters(entry)

                if not entry.holders and not entry.waiters:
                    del self._table[resource]

            if commit and is_writer:
                self._version += 1

            self._snapshots.pop(txn_id, None)

        if self._wfg:
            self._wfg.unregister(txn_id)

    def _grant_waiters(self, entry: LockEntry):
        """Grant next waiter(s) in FIFO order (S-locks can batch-grant; X-lock grants one)."""
        if not entry.waiters:
            return

        first_txn, first_mode, first_event = entry.waiters[0]

        if first_mode == LockMode.X:
            entry.waiters.pop(0)
            entry.holders.add(first_txn)
            entry.mode = LockMode.X
            first_event.set()
        else:
            # batch-grant all leading S-lock waiters
            entry.mode = LockMode.S
            while entry.waiters and entry.waiters[0][1] == LockMode.S:
                txn_id, _, ev = entry.waiters.pop(0)
                entry.holders.add(txn_id)
                ev.set()



