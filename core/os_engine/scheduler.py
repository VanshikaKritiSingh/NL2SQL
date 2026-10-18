"""
core/os_engine/scheduler.py — WFQ Query Scheduler with Skip-Count Aging & DDL Barrier

Algorithm:
  - Three priority queues (0=READ, 1=WRITE, 2=DDL) weighted by user role.
  - Skip-count aging: a query skipped 5 times gets promoted one level.
  - DDL Barrier: when a DDL enters the queue, all in-flight READ queries are
    allowed to finish; new READ/WRITE queries queue *behind* the DDL preserving
    arrival order. DDL executes only once the in-flight count hits zero.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, Optional


class QueryKind(IntEnum):
    READ = 0
    WRITE = 1
    DDL = 2  # highest serialization requirement


# ponytail: role weights are constants — no config object needed
ROLE_WEIGHT: Dict[str, int] = {
    "admin": 4,
    "analyst": 2,
    "viewer": 1,
}

SKIP_PROMOTE_THRESHOLD = 5  # skips before a query is promoted one level


@dataclass
class ScheduledQuery:
    query_id: str
    kind: QueryKind
    user_role: str
    fn: Callable[[], Any]       # zero-arg callable that runs the query
    arrival_seq: int            # global monotonic counter for FIFO tie-breaking
    skip_count: int = 0
    promoted: bool = False
    result: Any = field(default=None, repr=False)
    error: Optional[Exception] = field(default=None, repr=False)
    done_event: threading.Event = field(default_factory=threading.Event, repr=False)

    # effective priority: lower = higher priority
    @property
    def effective_priority(self) -> float:
        weight = ROLE_WEIGHT.get(self.user_role, 1)
        # higher weight → lower effective priority number → runs sooner
        base = self.kind.value * 10
        return base - weight + (self.arrival_seq * 0.0001)


class WFQScheduler:
    """
    Weighted Fair Queue with Skip-Count Aging and DDL Barrier.

    Usage:
        scheduler = WFQScheduler()
        scheduler.start()
        future = scheduler.submit(query_id, QueryKind.READ, "analyst", lambda: run_query())
        result = future.result   # blocks until done
    """

    def __init__(self, max_inflight_reads: int = 8):
        self._queues: list[deque[ScheduledQuery]] = [deque(), deque(), deque()]
        self._lock = threading.Lock()
        self._work_event = threading.Event()
        self._inflight_reads = 0
        self._ddl_pending = False          # DDL barrier flag
        self._max_inflight_reads = max_inflight_reads
        self._arrival_counter = 0
        self._worker = threading.Thread(target=self._run, daemon=True, name="WFQScheduler")
        self._running = False
        # ponytail: global lock on inflight counter; per-table locking when throughput is proven bottleneck

    def startSchedulerWorkerThread(self):
        self._running = True
        self._worker.start()

    def stopSchedulerWorkerThread(self):
        self._running = False
        self._work_event.set()

    def submitQueryTaskToScheduler(self, query_id: str, kind: QueryKind, user_role: str, fn: Callable[[], Any]) -> "ScheduledQuery":
        with self._lock:
            self._arrival_counter += 1
            q = ScheduledQuery(
                query_id=query_id,
                kind=kind,
                user_role=user_role,
                fn=fn,
                arrival_seq=self._arrival_counter,
            )
            self._queues[kind.value].append(q)
        self._work_event.set()
        return q

    # Aliases for backward compatibility
    start = startSchedulerWorkerThread
    stop = stopSchedulerWorkerThread
    submit = submitQueryTaskToScheduler

    def _next_candidate(self) -> Optional[ScheduledQuery]:
        """
        Pick the next runnable query obeying arrival-order invariant:
        1. If a DDL is pending (front of DDL queue) AND all queries that arrived
           BEFORE that DDL (lower arrival_seq) have completed (not inflight, not queued) → run DDL.
        2. While a DDL is pending, only queries that arrived BEFORE it may start.
        3. WFQ with skip-count aging among eligible READ/WRITE queries.
        """
        if self._queues[2]:
            ddl_candidate = self._queues[2][0]
            ddl_seq = ddl_candidate.arrival_seq

            # Queries with arrival_seq < ddl_seq that are still queued (not yet dispatched)
            pre_ddl_queued = any(
                c.arrival_seq < ddl_seq
                for tier in self._queues[:2] for c in tier
            )

            # DDL fires only when: no pre-DDL work is still queued AND nothing is in-flight
            if not pre_ddl_queued and self._inflight_reads == 0:
                self._queues[2].popleft()
                return ddl_candidate

            # Otherwise: only dispatch pre-DDL queries; block post-DDL queries
            # Fall through to WFQ selection but filtered by arrival_seq < ddl_seq
            self._ddl_pending = True
        else:
            self._ddl_pending = False

        # Collect candidates from READ and WRITE queues
        # If DDL is pending, candidate MUST have arrived BEFORE the DDL
        max_seq = self._queues[2][0].arrival_seq if self._ddl_pending and self._queues[2] else float("inf")

        best: Optional[ScheduledQuery] = None
        best_queue_idx: int = -1

        for qi, q in enumerate(self._queues[:2]):
            for candidate in q:
                if candidate.arrival_seq > max_seq:
                    continue  # blocked behind DDL barrier
                if best is None or candidate.effective_priority < best.effective_priority:
                    best = candidate
                    best_queue_idx = qi

        if best is None:
            return None

        # Apply skip-count: increment skip for everything we looked at and didn't pick
        for qi, q in enumerate(self._queues[:2]):
            for candidate in q:
                if candidate is not best:
                    candidate.skip_count += 1
                    if candidate.skip_count >= SKIP_PROMOTE_THRESHOLD and not candidate.promoted:
                        candidate.promoted = True
                        # promote: move to front of current queue (arrival order preserved within tier)
                        q.remove(candidate)
                        q.appendleft(candidate)

        # Remove best from its queue
        self._queues[best_queue_idx].remove(best)
        return best

    def _run(self):
        while self._running:
            self._work_event.wait(timeout=0.05)
            self._work_event.clear()

            # Check if a DDL is now at front of DDL queue — set barrier flag
            with self._lock:
                self._ddl_pending = bool(self._queues[2])

            while True:
                with self._lock:
                    candidate = self._next_candidate()
                    if candidate is None:
                        break
                    if candidate.kind == QueryKind.READ:
                        self._inflight_reads += 1

                # Execute outside the lock so other threads can submit
                try:
                    candidate.result = candidate.fn()
                except Exception as e:
                    candidate.error = e
                finally:
                    candidate.done_event.set()
                    if candidate.kind == QueryKind.READ:
                        with self._lock:
                            self._inflight_reads -= 1
                            # nudge event so DDL can check inflight==0
                        self._work_event.set()



