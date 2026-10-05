"""cost_estimator/engine.py — Heuristic & AST-driven Database Query Cost & Blast-Radius Engine

Calculates estimated query cost, row scans, blast-radius metrics, and threshold decisions
(ALLOW, ESCALATE, REJECT) directly from AST constructs and schema statistics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
import sqlglot
from sqlglot import exp

from .contracts import CostReport, SchemaProvider
from .thresholds import Thresholds, DEFAULT_THRESHOLDS


class HeuristicCostEngine:
    """
    Evaluates query computational cost and blast radius via AST inspection.
    """

    def __init__(self, thresholds: Optional[Thresholds] = None, schema_provider: Optional[SchemaProvider] = None):
        self.thresholds = thresholds or Thresholds.defaults()
        self.schema = schema_provider

    def estimate_cost(
        self,
        sql_or_ast: sqlglot.Expression | str,
        dialect: str = "postgres"
    ) -> CostReport:
        """
        Estimates query execution cost and makes safety gate decision.
        """
        if isinstance(sql_or_ast, str):
            try:
                parsed = sqlglot.parse_one(sql_or_ast, read=dialect)
            except Exception:
                return CostReport(
                    decision="REJECT",
                    estimated_cost=None,
                    estimated_rows_scanned=None,
                    estimated_rows_affected=None,
                    full_table_scans=[],
                    index_used=False,
                    reasons=["Failed to parse SQL AST for cost estimation."],
                    method="heuristic",
                )
        else:
            parsed = sql_or_ast

        reasons: List[str] = []
        full_table_scans: List[str] = []
        index_used: bool = False

        # Identify Statement Type
        if isinstance(parsed, exp.Select):
            return self._estimate_read_cost(parsed, reasons)
        elif isinstance(parsed, (exp.Update, exp.Delete)):
            return self._estimate_write_cost(parsed, reasons)
        elif isinstance(parsed, exp.Insert):
            return self._estimate_insert_cost(parsed, reasons)
        elif isinstance(parsed, (exp.Create, exp.Alter, exp.Drop)):
            return self._estimate_ddl_cost(parsed, reasons)
        else:
            return CostReport(
                decision="ALLOW",
                estimated_cost=10.0,
                estimated_rows_scanned=10,
                estimated_rows_affected=0,
                full_table_scans=[],
                index_used=True,
                reasons=["Generic statement type within baseline thresholds."],
                method="heuristic",
            )

    def _get_table_rows(self, table_name: str) -> int:
        if self.schema:
            try:
                return self.schema.get_rows(table_name)
            except Exception:
                pass
        return 50_000  # Default nominal table size

    def _estimate_read_cost(self, parsed: exp.Select, reasons: List[str]) -> CostReport:
        tables = [t.name for t in parsed.find_all(exp.Table) if t.name]
        joins = parsed.args.get("joins", [])
        where_clause = parsed.args.get("where")
        limit_clause = parsed.args.get("limit")
        order_clause = parsed.args.get("order")

        base_rows = sum(self._get_table_rows(t) for t in tables) if tables else 1_000
        full_table_scans = []
        index_used = False

        # Check filter selectivity
        if where_clause:
            # Check for equality on PK/ID
            pk_eq = False
            for eq in where_clause.find_all(exp.EQ):
                col_name = eq.left.name.lower() if isinstance(eq.left, exp.Column) else ""
                if "id" in col_name or "pk" in col_name or "key" in col_name:
                    pk_eq = True
                    break

            if pk_eq:
                index_used = True
                estimated_rows_scanned = min(100, base_rows)
                cost = 5.0 + len(joins) * 10.0
                reasons.append("Indexed point/range filter utilized.")
            else:
                index_used = False
                estimated_rows_scanned = base_rows
                cost = base_rows * 0.05 + len(joins) * 50.0
                full_table_scans = list(set(tables))
                reasons.append(f"Sequential scan required across {len(tables)} tables.")
        else:
            estimated_rows_scanned = base_rows
            cost = base_rows * 0.08 + len(joins) * 100.0
            full_table_scans = list(set(tables))
            reasons.append("Unfiltered SELECT query performs full table scan.")

        # Join multiplier
        if len(joins) > 0:
            cost *= (1.0 + 0.5 * len(joins))
            reasons.append(f"Query executes {len(joins)} relational JOIN operation(s).")

        # Order by without limit penalty
        if order_clause and not limit_clause:
            cost += estimated_rows_scanned * 0.02
            reasons.append("Unbounded ORDER BY requires full in-memory sorting.")

        # Bounded by limit
        if limit_clause:
            try:
                limit_val = int(limit_clause.expression.sql())
                cost = min(cost, cost * 0.6 + limit_val * 0.1)
                reasons.append(f"Execution bounded by LIMIT {limit_val}.")
            except ValueError:
                pass

        # Gate decision
        decision = "ALLOW"
        if cost >= self.thresholds.reject_cost or estimated_rows_scanned >= self.thresholds.reject_rows_scanned:
            decision = "REJECT"
            reasons.append(f"Estimated cost {cost:.1f} or scan rows {estimated_rows_scanned} exceeds rejection threshold.")
        elif cost >= self.thresholds.escalate_cost or estimated_rows_scanned >= self.thresholds.escalate_rows_scanned:
            decision = "ESCALATE"
            reasons.append(f"Estimated cost {cost:.1f} exceeds automatic approval threshold.")

        return CostReport(
            decision=decision,
            estimated_cost=round(cost, 2),
            estimated_rows_scanned=estimated_rows_scanned,
            estimated_rows_affected=0,
            full_table_scans=full_table_scans,
            index_used=index_used,
            reasons=reasons,
            method="heuristic",
        )

    def _estimate_write_cost(self, parsed: exp.Expression, reasons: List[str]) -> CostReport:
        table_node = parsed.find(exp.Table)
        t_name = table_node.name if table_node else "unknown"
        total_rows = self._get_table_rows(t_name)
        where_clause = parsed.args.get("where")

        if where_clause:
            # Check if filtered by PK/ID
            pk_eq = any("id" in str(eq.left).lower() for eq in where_clause.find_all(exp.EQ))
            if pk_eq:
                rows_affected = 1
                rows_scanned = 1
                cost = 25.0
                reasons.append("Mutating operation restricted to single primary key.")
            else:
                rows_affected = max(1, int(total_rows * 0.10))
                rows_scanned = total_rows
                cost = 150.0 + rows_affected * 0.5
                reasons.append(f"Mutating operation affects estimated ~{rows_affected} rows.")
        else:
            rows_affected = total_rows
            rows_scanned = total_rows
            cost = 1000.0 + rows_affected * 1.0
            reasons.append(f"Unbounded mutation affects entire table ({total_rows} rows).")

        decision = "ALLOW"
        if rows_affected >= self.thresholds.escalate_rows_affected:
            decision = "ESCALATE"
            reasons.append(f"Rows affected ({rows_affected}) exceeds automated mutation threshold ({self.thresholds.escalate_rows_affected}).")

        return CostReport(
            decision=decision,
            estimated_cost=round(cost, 2),
            estimated_rows_scanned=rows_scanned,
            estimated_rows_affected=rows_affected,
            full_table_scans=[t_name] if rows_scanned > 100 else [],
            index_used=rows_scanned <= 10,
            reasons=reasons,
            method="heuristic",
        )

    def _estimate_insert_cost(self, parsed: exp.Insert, reasons: List[str]) -> CostReport:
        table_node = parsed.find(exp.Table)
        t_name = table_node.name if table_node else "unknown"
        values_node = parsed.expression
        num_rows = len(values_node.expressions) if isinstance(values_node, exp.Values) else 1

        cost = 10.0 * num_rows
        reasons.append(f"INSERT statement adding {num_rows} record(s) to '{t_name}'.")

        decision = "ESCALATE" if num_rows >= self.thresholds.escalate_rows_affected else "ALLOW"
        return CostReport(
            decision=decision,
            estimated_cost=round(cost, 2),
            estimated_rows_scanned=0,
            estimated_rows_affected=num_rows,
            full_table_scans=[],
            index_used=True,
            reasons=reasons,
            method="heuristic",
        )

    def _estimate_ddl_cost(self, parsed: exp.Expression, reasons: List[str]) -> CostReport:
        table_node = parsed.find(exp.Table)
        t_name = table_node.name if table_node else "target_table"
        total_rows = self._get_table_rows(t_name)

        reasons.append(f"DDL structural modification on table '{t_name}'.")
        decision = "ESCALATE" if total_rows >= self.thresholds.escalate_table_rows else "ALLOW"

        return CostReport(
            decision=decision,
            estimated_cost=500.0,
            estimated_rows_scanned=total_rows,
            estimated_rows_affected=0,
            full_table_scans=[t_name] if total_rows > 0 else [],
            index_used=False,
            reasons=reasons,
            method="heuristic",
            method_detail=t_name,
        )
