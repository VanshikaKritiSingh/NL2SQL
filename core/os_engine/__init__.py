"""
core/os_engine/__init__.py — OS Engine public surface

Exposes the four OS kernel modules as a single coherent engine.
"""

from core.os_engine.scheduler import WFQScheduler, QueryKind, ScheduledQuery, ROLE_WEIGHT
from core.os_engine.deadlock import WaitForGraph, DeadlockDetector, DeadlockAbort
from core.os_engine.lock_manager import LockManager, LockMode
from core.os_engine.context_pager import WorkingSetPager
from core.os_engine.audit_log import PipelineAuditLog, AuditEvent

__all__ = [
    "WFQScheduler", "QueryKind", "ScheduledQuery", "ROLE_WEIGHT",
    "WaitForGraph", "DeadlockDetector", "DeadlockAbort",
    "LockManager", "LockMode",
    "WorkingSetPager",
    "PipelineAuditLog", "AuditEvent",
]
