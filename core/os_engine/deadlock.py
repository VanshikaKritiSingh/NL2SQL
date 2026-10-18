"""
core/os_engine/deadlock.py — Wait-For Graph (WFG) with Periodic Tarjan SCC Deadlock Detection

Algorithm:
  - WFG is a directed graph: edge T_i → T_j means transaction i is waiting for a resource held by j.
  - Tarjan's SCC runs every 500ms on a background thread.
  - Any SCC of size > 1 is a deadlock cycle; the youngest transaction in the cycle is aborted.
  - Victim transactions receive a DeadlockAbort exception surfaced through their done_event.
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set


class DeadlockAbort(Exception):
    """Raised in victim transaction to break a deadlock cycle."""


@dataclass
class TxnNode:
    txn_id: str
    start_time: float = field(default_factory=time.time)
    on_abort: Optional[Callable[[], None]] = field(default=None, repr=False)


class WaitForGraph:
    """
    Thread-safe directed Wait-For Graph.
    Edge (waiter → holder) means waiter is blocked waiting for a resource held by holder.
    """

    def __init__(self):
        self._adj: Dict[str, Set[str]] = defaultdict(set)  # waiter → set of holders
        self._txns: Dict[str, TxnNode] = {}
        self._lock = threading.Lock()

    def registerTransactionInGraph(self, txn_id: str, on_abort: Optional[Callable[[], None]] = None):
        with self._lock:
            if txn_id not in self._txns:
                self._txns[txn_id] = TxnNode(txn_id=txn_id, on_abort=on_abort)

    def unregisterTransactionFromGraph(self, txn_id: str):
        with self._lock:
            self._txns.pop(txn_id, None)
            self._adj.pop(txn_id, None)
            for holders in self._adj.values():
                holders.discard(txn_id)

    def recordTransactionWaitDependency(self, waiter_id: str, holder_id: str):
        """Record that waiter is now blocked on holder."""
        with self._lock:
            self._adj[waiter_id].add(holder_id)

    def removeTransactionWaitDependency(self, waiter_id: str, holder_id: str):
        with self._lock:
            self._adj[waiter_id].discard(holder_id)

    def captureWaitGraphSnapshot(self) -> tuple[Dict[str, Set[str]], Dict[str, TxnNode]]:
        with self._lock:
            adj_copy = {k: set(v) for k, v in self._adj.items()}
            txns_copy = dict(self._txns)
        return adj_copy, txns_copy

    # Aliases for backward compatibility
    register = registerTransactionInGraph
    unregister = unregisterTransactionFromGraph
    add_wait = recordTransactionWaitDependency
    remove_wait = removeTransactionWaitDependency
    snapshot = captureWaitGraphSnapshot


def _tarjan_sccs(adj: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Tarjan's strongly connected components on an adjacency dict.
    Returns all SCCs of size >= 2 (those are deadlock cycles).
    Standard iterative-stack Tarjan — no recursion limit issues.
    """
    index_counter = [0]
    stack = []
    lowlink: Dict[str, int] = {}
    index: Dict[str, int] = {}
    on_stack: Dict[str, bool] = {}
    sccs: List[List[str]] = []

    nodes = set(adj.keys())
    for v in adj.values():
        nodes.update(v)

    def strongconnect(v):
        index[v] = lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in adj.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w, False):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:
                sccs.append(scc)

    for node in nodes:
        if node not in index:
            strongconnect(node)

    return sccs


class DeadlockDetector:
    """
    Runs Tarjan SCC every 500ms.  Aborts the youngest txn in each cycle.
    """

    SWEEP_INTERVAL_S = 0.5  # ponytail: fixed interval; tune down when lock contention is proven high

    def __init__(self, wfg: WaitForGraph):
        self._wfg = wfg
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DeadlockDetector")
        self._running = False
        self.abort_log: List[str] = []  # for telemetry / tests

    def startPeriodicDetectionLoop(self):
        self._running = True
        self._thread.start()

    def stopPeriodicDetectionLoop(self):
        self._running = False

    def _loop(self):
        while self._running:
            time.sleep(self.SWEEP_INTERVAL_S)
            self.executeDeadlockDetectionSweep()

    def executeDeadlockDetectionSweep(self):
        adj, txns = self._wfg.captureWaitGraphSnapshot()
        cycles = _tarjan_sccs(adj)
        for cycle in cycles:
            # pick youngest (highest start_time) as victim
            victim_id = max(
                (t for t in cycle if t in txns),
                key=lambda t: txns[t].start_time,
                default=None,
            )
            if victim_id and victim_id in txns:
                self.abort_log.append(victim_id)
                node = txns[victim_id]
                self._wfg.unregisterTransactionFromGraph(victim_id)
                if node.on_abort:
                    try:
                        node.on_abort()
                    except Exception:
                        pass

    # Aliases for backward compatibility
    start = startPeriodicDetectionLoop
    stop = stopPeriodicDetectionLoop
    _sweep = executeDeadlockDetectionSweep



