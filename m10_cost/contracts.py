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
# Threshold configuration
# ------------------------------------------------------------------

@dataclass
class Thresholds:
    """Configuration values for decision thresholds."""
    # READ thresholds (cost, rows, full‑scan)
    escalate_cost: int = 50000
    reject_cost: int = 1000000
    escalate_rows_scanned: int = 100000
    reject_rows_scanned: int = 20000000
    full_scan_min_table_rows: int = 100000

    # WRITE thresholds
    escalate_rows_affected: int = 100

    # DDL thresholds
    escalate_table_rows: int = 500000

    # Runtime limits
    explain_timeout_ms: int = 2000


class ConfigError(Exception):
    """Raised when threshold config is invalid or missing."""


def load_thresholds(path: str = "config/thresholds.json") -> Thresholds:
    """Load thresholds from a JSON file. Supports a minimal fallback if file missing."""
    if not os.path.exists(path):
        # Minimal default – can be overridden by user later
        return Thresholds()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Basic validation – ensure required keys exist; otherwise use defaults
        def get_int(key: str, default: int) -> int:
            return int(data.get(key, default))

        def get_float(key: str, default: float) -> float:
            return float(data.get(key, default))

        escalate_cost = int(data.get("escalate_cost", 50000))
        reject_cost = int(data.get("reject_cost", 1000000))
        escalate_rows_scanned = int(data.get("escalate_rows_scanned", 100000))
        reject_rows_scanned = int(data.get("reject_rows_scanned", 20000000))
        full_scan_min_table_rows = int(data.get("full_scan_min_table_rows", 100000))
        escalate_rows_affected = int(data.get("escalate_rows_affected", 100))
        escalate_table_rows = int(data.get("escalate_table_rows", 500000))
        explain_timeout_ms = int(data.get("explain_timeout_ms", 2000))

        return Thresholds(
            escalate_cost=escalate_cost,
            reject_cost=reject_cost,
            escalate_rows_scanned=escalate_rows_scanned,
            reject_rows_scanned=reject_rows_scanned,
            full_scan_min_table_rows=full_scan_min_table_rows,
            escalate_rows_affected=escalate_rows_affected,
            escalate_table_rows=escalate_table_rows,
            explain_timeout_ms=explain_timeout_ms,
        )
    except Exception as exc:
        raise ConfigError(f"Failed to load thresholds from {path}: {exc}") from exc