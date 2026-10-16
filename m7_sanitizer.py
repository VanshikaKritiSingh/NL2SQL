"""M7 — Parameterized Query Sanitizer Module.

The path is wrong, so let's create the sanitized version directly under the workspace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple

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
    params: list[Any] = []
    placeholder_map: dict[int, int] = {}
    param_counter = 1

    def walk(node: exp.Expression) -> None:
        nonlocal param_counter
        if isinstance(node, exp.Literal):
            if node.this is None:
                return
            placeholder_map[id(node)] = param_counter
            if isinstance(node, exp.Boolean):
                val = node.this
            elif isinstance(node, exp.Number):
                val = float(node.name) if node.is_float else int(node.name)
            else:
                val = node.this
            params.append(val)
            param_counter += 1
        else:
            for child in node.iter_expressions():
                walk(child)

    walk(parsed)

    def transform(node: exp.Expression) -> exp.Expression:
        if isinstance(node, exp.Literal) and id(node) in placeholder_map:
            idx = placeholder_map[id(node)]
            if dialect == "postgres":
                return exp.Placeholder(this=f"${idx}")
            else:
                return exp.Placeholder(this="?")
        return node.transform(transform)

    transformed = parsed.transform(transform)
    result_sql = transformed.sql(dialect=dialect)

    # Sanity check: no raw literals left
    check = sqlglot.parse_one(result_sql, dialect=dialect)
    for node in check.walk():
        if isinstance(node, exp.Literal) and not isinstance(node, exp.Boolean):
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