"""
M8 — Multi-Dialect SQL Converter Module

Takes parameterized SQL from M7 and converts it for target DBMS dialects:
PostgreSQL, MySQL, Oracle, SQL Server, Access.

All transformations are rule-based and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import sqlglot
from sqlglot import exp


@dataclass(frozen=True, slots=True)
class DialectSQL:
    """Single dialect conversion result."""
    dialect: str
    sql: str


@dataclass(frozen=True, slots=True)
class ConvertedStatement:
    """All dialect conversions for one input statement."""
    original: str  # original parameterized SQL from M7
    conversions: Tuple[DialectSQL, ...]  # one per target dialect


class DialectConversionError(ValueError):
    """Raised when conversion to a dialect fails."""
    pass


def convert_sql(
    parameterized_statement: ParameterizedStatement,
    target_dialects: Optional[List[str]] = None,
) -> ConvertedStatement:
    """
    Convert a parameterized SQL statement to one or more target dialects.

    Args:
        parameterized_statement: Output from M7 (sanitize_sql).
        target_dialects: List of dialect strings. Defaults to
            ["postgres", "mysql", "oracle", "sqlserver", "access"].

    Returns:
        ConvertedStatement containing original + all conversions.

    Raises:
        DialectConversionError: if any dialect conversion fails.
    """
    if target_dialects is None:
        target_dialects = ["postgres", "mysql", "oracle", "sqlserver", "access"]

    original_sql = parameterized_statement.sql
    conversions: List[DialectSQL] = []

    # Parse once into AST
    try:
        ast = sqlglot.parse_one(
            original_sql,
            dialect=parameterized_statement.dialect,
            read=parameterized_statement.dialect,
        )
    except Exception as exc:
        raise DialectConversionError(
            f"Failed to parse input SQL for conversion: {exc}"
        ) from exc

    for target in target_dialects:
        try:
            converted = ast.sql(dialect=target, read=parameterized_statement.dialect)
        except Exception as exc:
            raise DialectConversionError(
                f"Conversion to '{target}' failed: {exc}"
            ) from exc

        conversions.append(DialectSQL(dialect=target, sql=converted))

    return ConvertedStatement(
        original=original_sql,
        conversions=tuple(conversions),
    )


def convert_to_postgres(parameterized_statement: ParameterizedStatement) -> DialectSQL:
    result = convert_sql(parameterized_statement, target_dialects=["postgres"])
    return result.conversions[0]


def convert_to_mysql(parameterized_statement: ParameterizedStatement) -> DialectSQL:
    result = convert_sql(parameterized_statement, target_dialects=["mysql"])
    return result.conversions[0]


def convert_to_oracle(parameterized_statement: ParameterizedStatement) -> DialectSQL:
    result = convert_sql(parameterized_statement, target_dialects=["oracle"])
    return result.conversions[0]


def convert_to_sqlserver(parameterized_statement: ParameterizedStatement) -> DialectSQL:
    result = convert_sql(parameterized_statement, target_dialects=["sqlserver"])
    return result.conversions[0]


def convert_to_access(parameterized_statement: ParameterizedStatement) -> DialectSQL:
    result = convert_sql(parameterized_statement, target_dialects=["access"])
    return result.conversions[0]


__all__ = [
    "DialectSQL",
    "ConvertedStatement",
    "DialectConversionError",
    "convert_sql",
    "convert_to_postgres",
    "convert_to_mysql",
    "convert_to_oracle",
    "convert_to_sqlserver",
    "convert_to_access",
]