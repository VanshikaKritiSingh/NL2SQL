"""
tests/test_os_engine.py — Unit tests for Core OS Concurrency & Resource Engine
"""

import time
import pytest

from core.os_engine.scheduler import WFQScheduler, QueryKind, ScheduledQuery
from core.os_engine.deadlock import WaitForGraph, DeadlockDetector, _tarjan_sccs
from core.os_engine.lock_manager import LockManager, LockMode
from core.os_engine.context_pager import WorkingSetPager
from core.os_engine.audit_log import PipelineAuditLog, AuditEvent


def testWeightedFairQueueSchedulerExecutionLifecycle():
    scheduler = WFQScheduler()
    scheduler.startSchedulerWorkerThread()
    try:
        def job():
            return 42

        task = scheduler.submitQueryTaskToScheduler("q-1", QueryKind.READ, "analyst", job)
        task.done_event.wait(timeout=2.0)
        assert task.result == 42
        assert task.error is None
    finally:
        scheduler.stopSchedulerWorkerThread()


def testDeadlockDetectionAndVictimAbortionCycle():
    wfg = WaitForGraph()
    detector = DeadlockDetector(wfg)
    
    # Create cycle: txn-A waits for txn-B, txn-B waits for txn-A
    wfg.registerTransactionInGraph("txn-A")
    wfg.registerTransactionInGraph("txn-B")
    wfg.recordTransactionWaitDependency("txn-A", "txn-B")
    wfg.recordTransactionWaitDependency("txn-B", "txn-A")

    adj, txns = wfg.captureWaitGraphSnapshot()
    cycles = _tarjan_sccs(adj)
    assert len(cycles) == 1
    assert "txn-A" in cycles[0] and "txn-B" in cycles[0]

    # Run one sweep
    detector.executeDeadlockDetectionSweep()
    assert len(detector.abort_log) == 1


def testLockManagerAcquireSharedLocksAndReleaseAll():
    wfg = WaitForGraph()
    lm = LockManager(wfg=wfg)

    wfg.registerTransactionInGraph("txn-1")
    wfg.registerTransactionInGraph("txn-2")

    # Shared lock can be acquired by both
    assert lm.acquireResourceLockWithTimeout("txn-1", "users", LockMode.S) is True
    assert lm.acquireResourceLockWithTimeout("txn-2", "users", LockMode.S) is True

    # Release
    lm.releaseAllHeldResourceLocks("txn-1")
    lm.releaseAllHeldResourceLocks("txn-2")


def testContextPagerTracksActiveWorkingSetTables():
    pager = WorkingSetPager()
    pager.recordQueryTablesForUserSession("user-1", ["users", "orders"])
    ws = pager.retrieveActiveWorkingSetTablesForUser("user-1")
    assert "users" in ws
    assert "orders" in ws


def testPipelineAuditLogAppendsAndFiltersEventRecords(tmp_path):
    log_file = str(tmp_path / "test_audit.jsonl")
    log = PipelineAuditLog(path=log_file)
    ev = AuditEvent(
        event_id="ev-1",
        timestamp=time.time(),
        user_id="test-user",
        operation="SUBMIT",
        query_id="q-100",
        stage=1,
        stage_name="Intake",
        details={"status": "ok"},
    )
    log.appendAuditTrailEventRecord(ev)
    items = log.listAuditTrailEventRecords(user_id="test-user")
    assert len(items) == 1
    assert items[0].query_id == "q-100"


def testLockManagerWaiterPromotionReleasesProperly():
    """Verify that waiter-promoted locks are recorded in _txn_locks and released without leaking (DA-08)."""
    import threading
    lm = LockManager()

    # txn-1 takes exclusive lock
    assert lm.acquire("txn-1", "accounts", LockMode.X) is True

    promoted_event = threading.Event()
    def waiter_thread():
        # txn-2 will block until txn-1 releases
        assert lm.acquire("txn-2", "accounts", LockMode.X, timeout_s=3.0) is True
        promoted_event.set()

    t = threading.Thread(target=waiter_thread)
    t.start()

    # Wait briefly to ensure txn-2 is enqueued as waiter
    time.sleep(0.05)
    assert len(lm._table["accounts"].waiters) == 1

    # txn-1 releases, promoting txn-2
    lm.release_all("txn-1")
    assert promoted_event.wait(timeout=1.0) is True
    t.join()

    # Verify txn-2 is registered in _txn_locks
    assert "accounts" in lm._txn_locks["txn-2"]
    assert "txn-2" in lm._table["accounts"].holders

    # txn-2 releases all locks
    lm.release_all("txn-2")

    # Table entry must be cleanly removed or empty
    assert "accounts" not in lm._table or not lm._table["accounts"].holders


def testWFQSchedulerConcurrentReaders():
    """Verify WFQScheduler runs concurrent READ tasks using worker thread pool (DA-11)."""
    import threading
    scheduler = WFQScheduler(max_inflight_reads=4)
    scheduler.start()

    active_reads = 0
    max_concurrent = 0
    lock = threading.Lock()
    barrier = threading.Barrier(3)

    def slow_read():
        nonlocal active_reads, max_concurrent
        with lock:
            active_reads += 1
            if active_reads > max_concurrent:
                max_concurrent = active_reads
        try:
            barrier.wait(timeout=2.0)
            time.sleep(0.05)
        finally:
            with lock:
                active_reads -= 1
        return "ok"

    try:
        t1 = scheduler.submit("q-1", QueryKind.READ, "analyst", slow_read)
        t2 = scheduler.submit("q-2", QueryKind.READ, "analyst", slow_read)
        t3 = scheduler.submit("q-3", QueryKind.READ, "analyst", slow_read)

        t1.done_event.wait(timeout=3.0)
        t2.done_event.wait(timeout=3.0)
        t3.done_event.wait(timeout=3.0)

        assert t1.result == "ok"
        assert t2.result == "ok"
        assert t3.result == "ok"
        assert max_concurrent >= 2  # Proves concurrent execution occurred!
    finally:
        scheduler.stop()
