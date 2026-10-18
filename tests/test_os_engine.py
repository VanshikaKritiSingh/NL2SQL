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


def test_wfq_scheduler_execution():
    scheduler = WFQScheduler()
    scheduler.start()
    try:
        def job():
            return 42

        task = scheduler.submit("q-1", QueryKind.READ, "analyst", job)
        task.done_event.wait(timeout=2.0)
        assert task.result == 42
        assert task.error is None
    finally:
        scheduler.stop()


def test_deadlock_detection_cycle():
    wfg = WaitForGraph()
    detector = DeadlockDetector(wfg)
    
    # Create cycle: txn-A waits for txn-B, txn-B waits for txn-A
    wfg.register("txn-A")
    wfg.register("txn-B")
    wfg.add_wait("txn-A", "txn-B")
    wfg.add_wait("txn-B", "txn-A")

    adj, txns = wfg.snapshot()
    cycles = _tarjan_sccs(adj)
    assert len(cycles) == 1
    assert "txn-A" in cycles[0] and "txn-B" in cycles[0]

    # Run one sweep
    detector._sweep()
    assert len(detector.abort_log) == 1


def test_lock_manager_acquire_and_release():
    wfg = WaitForGraph()
    lm = LockManager(wfg=wfg)

    wfg.register("txn-1")
    wfg.register("txn-2")

    # Shared lock can be acquired by both
    assert lm.acquire("txn-1", "users", LockMode.S) is True
    assert lm.acquire("txn-2", "users", LockMode.S) is True

    # Release
    lm.release_all("txn-1")
    lm.release_all("txn-2")


def test_context_pager_working_set():
    pager = WorkingSetPager()
    pager.record("user-1", ["users", "orders"])
    ws = pager.active_tables("user-1")
    assert "users" in ws
    assert "orders" in ws


def test_pipeline_audit_log_append_and_filter(tmp_path):
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
    log.append(ev)
    items = log.list_events(user_id="test-user")
    assert len(items) == 1
    assert items[0].query_id == "q-100"
