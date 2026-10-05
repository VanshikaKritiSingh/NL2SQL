"""M10 — Cost Estimator contracts and configuration.

Defines CostReport, PlanAdapter, PlanRunner, SchemaProvider, and loads
thresholds from a config file (JSON/YAML). All are pure data structures;
no DB interaction happens here.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ------------------------------------------------------------------
# CostReport
# ------------------------------------------------------------------

@dataclass
class CostReport:
    """Result of a Cost Estimation run."""
    decision: str  # "ALLOW" | "ESCALATE" | "REJECT"
    estimated_cost: Optional[float]  # cost metric per dialect
    estimated_rows_scanned: Optional[int]  # rows the plan estimates to read
    estimated_rows_affected: Optional[int]  # for UPDATE/DELETE only
    full_table_scans: List[str]  # tables hit by full scans
    index_used: Optional[bool]  # whether any index scan/only scan used
    reasons: List[str]  # human‑readable, actionable reasons
    method: str  # "explain" | "heuristic"
    method_detail: Optional[str] = None  # extra info (e.g., table name for DDL)

    def is_allow(self) -> bool:
        return self.decision == "ALLOW"

    def is_escalate(self) -> bool:
        return self.decision == "ESCALATE"

    def is_reject(self) -> bool:
        return self.decision == "REJECT"


# ------------------------------------------------------------------
# PlanAdapter protocol
# ------------------------------------------------------------------

class PlanAdapter:
    """Parse raw EXPLAIN output into a normalized structure."""

    def plan(self, sql: str, timeout_ms: int = 2000) -> Dict[str, Any]:
        """
        Return a normalized plan dict.

        Sub‑classes must implement the dialect‑specific parsing.
        The base method raises NotImplementedError.
        """
        raise NotImplementedError


# ------------------------------------------------------------------
# PlanRunner protocol
# ------------------------------------------------------------------

class PlanRunner:
    """Execute EXPLAIN (or COUNT) against a DB via a PlanAdapter."""

    def plan(self, sql: str, timeout_ms: int = 2000) -> Dict[str, Any]:
        """Run EXPLAIN on *sql* and return the normalized plan dict."""
        raise NotImplementedError

    def count(self, sql: str, table_name: str, timeout_ms: int = 2000) -> int:
        """
        Return estimated rows affected (UPDATE/DELETE) by running a COUNT(*) on
        a read‑only replica. The implementation may use the replica's statistics.
        """
        raise NotImplementedError


# ------------------------------------------------------------------
# SchemaProvider protocol
# ------------------------------------------------------------------

class SchemaProvider:
    """Read‑only metadata about tables, columns, indexes, row counts."""

    def get_tables(self) -> Tuple[str, ...]:
        """Return all table names in the schema."""
        raise NotImplementedError

    def get_table(self, name: str) -> Optional[Dict[str, Any]]:
        """Return metadata for *name* or None if missing."""
        raise NotImplementedError

    def get_row_count(self, table_name: str) -> int:
        """Return estimated or actual row count for *table_name*."""
        raise NotImplementedError


# ------------------------------------------------------------------
# Threshold configuration (canonical definitions in .thresholds)
# ------------------------------------------------------------------

from .thresholds import Thresholds, ThresholdsError, load_thresholds, DEFAULT_THRESHOLDS
ConfigError = ThresholdsError
