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
