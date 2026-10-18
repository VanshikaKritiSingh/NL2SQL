"""M7 — Parameterized Query Sanitizer Module.

Provides AST-based parameterization for SQL queries using sqlglot,
extracting raw literals into typed parameters to prevent SQL injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple

import sqlglot
from sqlglot import exp


@dataclass(frozen=True, slots=True)
class ParameterizedStatement:
    sql: str
    params: Tuple[Any, ...]
    dialect: str


class SanitizationError(ValueError):
    pass


def parse_sql(sql: str, dialect: str = "postgres") -> exp.Expression:
    try:
        return sqlglot.parse_one(sql, dialect=dialect, read=dialect)
    except Exception as exc:
        raise SanitizationError(f"Failed to parse SQL: {exc}") from exc


def sanitize_sql(sql: str, dialect: str = "postgres") -> ParameterizedStatement:
    parsed = parse_sql(sql, dialect=dialect)
    params: List[Any] = []
    param_counter = 1

    def transform(node: exp.Expression) -> exp.Expression:
        nonlocal param_counter
        if isinstance(node, (exp.Literal, exp.Boolean)):
            if isinstance(node, exp.Literal) and node.this is None:
                return node
            if isinstance(node, exp.Boolean):
                val = bool(node.this)
            elif getattr(node, "is_int", False):
                val = int(node.name)
            elif getattr(node, "is_number", False):
                try:
                    val = int(node.name)
                except ValueError:
                    val = float(node.name)
            else:
                val = node.this

            params.append(val)
            idx = param_counter
            param_counter += 1

            if dialect in ("postgres", "postgresql"):
                return exp.Parameter(this=exp.Literal.number(idx))
            else:
                return exp.Placeholder()
        return node

    transformed = parsed.transform(transform, copy=False)
    result_sql = transformed.sql(dialect=dialect)

    # Sanity check: no unparameterized raw literals left
    check = sqlglot.parse_one(result_sql, dialect=dialect)
    for node in check.walk():
        if (
            isinstance(node, exp.Literal)
            and not isinstance(node, exp.Boolean)
            and not node.find_ancestor(exp.Parameter)
        ):
            raise SanitizationError(
                "Literal value still present after transformation — unsafe input detected"
            )

    return ParameterizedStatement(
        sql=result_sql,
        params=tuple(params),
        dialect=dialect,
    )


def sanitize_with_postgres(sql: str) -> ParameterizedStatement:
    return sanitize_sql(sql, dialect="postgres")


__all__ = [
    "ParameterizedStatement",
    "SanitizationError",
    "parse_sql",
    "sanitize_sql",
    "sanitize_with_postgres",
]
