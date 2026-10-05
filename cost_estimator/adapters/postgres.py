"""PostgresAdapter for M10 Cost Estimator.

Parses EXPLAIN (FORMAT JSON) output into a normalized plan dict.
Implements PlanAdapter and PlanRunner protocols.
Uses a fake DB connection for now (FakePlanRunner) that reads JSON fixtures.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .contracts import PlanAdapter, PlanRunner, SchemaProvider, CostReport, Thresholds

# ------------------------------------------------------------------
# FakePlanRunner
# ------------------------------------------------------------------

class FakePlanRunner(PlanRunner):
    """Fake DB connection that reads EXPLAIN JSON fixtures from disk.

    The fixture directory structure:
        tests/fixtures/explain_json/<dialect>/<scenario>.json
    """

    def __init__(self, fixture_dir: str = "tests/fixtures/explain_json"):
        self.fixture_dir = Path(fixture_dir)
        self._last_load = 0
        self._last_sql = ""

    def plan(self, sql: str, timeout_ms: int = 2000) -> Dict[str, Any]:
        """
        Return a normalized plan dict for *sql*.

        The fake implementation looks up a matching fixture file based on a
        simple hash of the SQL (ignoring literals). If no fixture exists,
        returns a minimal "full scan" stub.
        """
        # Normalize SQL: strip whitespace and replace literals with placeholders
        normalized = self._normalize_sql(sql)
        hash_key = f"{normalized[:30]}__{len(normalized)}"  # crude hash
        fixture_path = self.fixture_dir / "postgres" / f"{hash_key}.json"

        # Simple fallback: if no fixture, assume full table scan
        if not fixture_path.exists():
            return self._fallback_full_scan(sql)

        # Load fixture (simulate I/O delay)
        if time.time() - self._last_load > 0.1:  # avoid rapid reloads in tests
            with open(fixture_path, "r", encoding="utf-8") as f:
                raw_plan = json.load(f)
            self._last_load = time.time()
            return self._postprocess_plan(raw_plan, sql)

        # Reuse cached plan if same SQL
        if self._last_sql == normalized:
            return self._cached_plan

        # Otherwise load new plan
        with open(fixture_path, "r", encoding="utf-8") as f:
            raw_plan = json.load(f)
        self._last_sql = normalized
        self._cached_plan = self._postprocess_plan(raw_plan, sql)
        return self._cached_plan

    def _normalize_sql(self, sql: str) -> str:
        """Very naive normalization: strip whitespace and replace string literals."""
        import re

        # Remove newlines/tabs
        sql = " ".join(sql.split())
        # Replace string literals with placeholder
        sql = re.sub(r"('|\")([^'\"]+)(?:'|\")", "PLACEHOLDER", sql)
        return sql

    def _fallback_full_scan(self, sql: str) -> Dict[str, Any]:
        """Return a stub plan indicating a full table scan."""
        return {
            "method": "explain",
            "dialect": "postgres",
            "total_cost": 1.0,
            "estimated_rows_scanned": 1000000,  # placeholder
            "estimated_rows_affected": 0,
            "estimated_rows_returned": 0,
            "full_table_scans": ["unknown_table"],
            "index_used": False,
            "node_types": ["Seq Scan"],
            "explain_raw": {"Plan": {"Node Type": "Seq Scan"}},
        }

    def _postprocess_plan(self, raw: Dict[str, Any], sql: str) -> Dict[str, Any]:
        """Extract and normalize fields from raw EXPLAIN JSON."""
        plan = raw.get("Plan", {})
        node_type = plan.get("Node Type", "Unknown")

        # Basic cost fields (Postgres specific)
        total_cost = float(plan.get("Total Cost", 0.0))

        # Estimate rows scanned: look for "Plan Rows" or similar
        rows_scanned = int(plan.get("Plan Rows", 0))

        # Determine if any index is used (simple heuristic)
        index_used = any(
            node.get("Index Name") or node.get("Access Type") == "Index Scan"
            for node in self._walk_plan_nodes(plan)
        )

        # Full table scans: collect table names from node types
        full_table_scans = self._collect_full_scans(plan)

        # Rows affected: for UPDATE/DELETE we need a separate count()
        rows_affected = None  # will be filled by count()

        # Rows returned: top-level plan node's "Plan Rows" or "Plan Rows" from child
        rows_returned = rows_scanned  # approximate

        return {
            "method": "explain",
            "dialect": "postgres",
            "total_cost": total_cost,
            "estimated_rows_scanned": rows_scanned,
            "estimated_rows_affected": rows_affected,
            "estimated_rows_returned": rows_returned,
            "full_table_scans": full_table_scans,
            "index_used": index_used,
            "node_types": [node_type] + self._collect_node_types(plan),
            "explain_raw": raw,
        }

    def _walk_plan_nodes(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recursively walk the plan tree to find nodes."""
        nodes = [node]
        if "Plans" in node:
            for child in node["Plans"]:
                nodes.extend(self._walk_plan_nodes(child))
        return nodes

    def _collect_node_types(self, node: Dict[str, Any]) -> List[str]:
        """Collect node type strings from the plan tree."""
        types = []
        if "Node Type" in node:
            types.append(node["Node Type"])
        if "Plans" in node:
            for child in node["Plans"]:
                types.extend(self._collect_node_types(child))
        return types

    def _collect_full_scans(self, node: Dict[str, Any]) -> List[str]:
        """Collect table names that appear in full scans (Seq Scan, etc.)."""
        tables = set()
        if "Node Type" in node and node["Node Type"].startswith("Seq Scan"):
            # In real plans, table name is in "Relation Name"
            tables.add(node.get("Relation Name", "unknown"))
        if "Plans" in node:
            for child in node["Plans"]:
                tables.update(self._collect_full_scans(child))
        return list(tables)

    # ------------------------------------------------------------------
    # count() implementation – uses SchemaProvider to get row counts
    # ------------------------------------------------------------------

    def count(self, sql: str, table_name: str, timeout_ms: int = 2000) -> int:
        """
        Estimate rows affected by UPDATE/DELETE.

        The fake implementation just returns a placeholder based on table size
        and whether the WHERE clause contains a literal filter.
        """
        # Very naive heuristic: if WHERE contains a literal value, assume 1 row.
        # Otherwise assume full table scan.
        normalized = self._normalize_sql(sql)
        has_literal_filter = "'" in normalized or '"' in normalized
        row_count = self._get_table_row_count(table_name)
        return row_count if has_literal_filter else row_count

    def _get_table_row_count(self, table_name: str) -> int:
        """Look up row count from a fake fixture (if exists)."""
        # In a real system this would query the replica; here we simulate.
        # For now, return a placeholder value.
        return 500_000  # assume 500k rows per table in fixtures


# ------------------------------------------------------------------
# PostgresAdapter (PlanAdapter + PlanRunner)
# ------------------------------------------------------------------

class PostgresAdapter(PlanAdapter, PlanRunner):
    """Adapter that talks to a real Postgres instance via psycopg2."""

    def __init__(self, plan_runner: PlanRunner, schema_provider: SchemaProvider):
        self.plan_runner = plan_runner
        self.schema_provider = schema_provider

    # PlanAdapter implementation -------------------------------------------------
    def plan(self, sql: str, timeout_ms: int = 2000) -> Dict[str, Any]:
        """
        Run EXPLAIN on *sql* using the underlying plan_runner (which may be fake
        or real). The adapter itself does not execute SQL; it delegates.
        """
        return self.plan_runner.plan(sql, timeout_ms=timeout_ms)

    # PlanRunner implementation -------------------------------------------------
    def plan(self, sql: str, timeout_ms: int = 2000) -> Dict[str, Any]:
        """
        Execute EXPLAIN on *sql* using a real Postgres connection.

        This stub uses FakePlanRunner for now; replace with real psycopg2 logic
        when the adapter is production‑ready.
        """
        return self.plan_runner.plan(sql, timeout_ms=timeout_ms)

    def count(self, sql: str, table_name: str, timeout_ms: int = 2000) -> int:
        """
        Estimate rows affected by UPDATE/DELETE.

        For now, delegate to FakePlanRunner's count() which uses row counts
        from the schema provider.
        """
        return self.plan_runner.count(sql, table_name, timeout_ms=timeout_ms)


# ------------------------------------------------------------------
# FakeSchemaProvider (for testing only)
# ------------------------------------------------------------------

class FakeSchemaProvider(SchemaProvider):
    """Simple in‑memory schema that mimics the shape needed for count()."""

    def __init__(self, tables: Dict[str, int]):
        """
        tables: mapping from table name to estimated row count.
        """
        self._tables = tables

    def get_tables(self) -> tuple[str, ...]:
        return tuple(self._tables.keys())

    def get_table(self, name: str) -> Optional[Dict[str, Any]]:
        return {"rows": self._tables.get(name, 0)} if name in self._tables else None

    def get_row_count(self, table_name: str) -> int:
        return self._tables.get(table_name, 0)


# ------------------------------------------------------------------
# Example factory (not used in tests, but convenient)
# ------------------------------------------------------------------

def make_postgres_adapter(
    fixture_dir: str = "tests/fixtures/explain_json",
    tables_row_counts: Optional[Dict[str, int]] = None,
) -> tuple[PostgresAdapter, FakePlanRunner]:
    """
    Returns (adapter, fake_plan_runner) for quick testing.

    *fixture_dir* points to the directory with JSON EXPLAIN fixtures.
    *tables_row_counts* maps table names to row counts for the fake count()
    implementation.
    """
    plan_runner = FakePlanRunner(fixture_dir)
    schema_provider = FakeSchemaProvider(tables_row_counts or {})
    adapter = PostgresAdapter(plan_runner, schema_provider)
    return adapter, plan_runner