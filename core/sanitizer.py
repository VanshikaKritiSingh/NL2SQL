"""M7 — Parameterized Query Sanitizer Module.

Provides AST-based parameterization for SQL queries using sqlglot,
extracting raw literals into typed parameters to prevent SQL injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple, Optional

import sqlglot
from sqlglot import exp


@dataclass(frozen=True, slots=True)
class ParameterizedStatement:
    sql: str
    params: Tuple[Any, ...]
    dialect: str


class SanitizationError(ValueError):
    pass


def detectMultipleStackedSqlStatements(sql: str) -> bool:
    """Detect stacked queries separated by semicolons."""
    return len([s for s in sql.split(";") if s.strip()]) > 1


def split_sql_script(sql: str, dialect: Optional[str] = None) -> List[str]:
    """
    Split a multi-statement SQL script into individual executable statements.
    Uses sqlglot for robust parsing when available; falls back to a
    quote/comment-aware tokenizer for edge cases.
    """
    if not sql or not sql.strip():
        return []
    stripped = sql.strip()
    try:
        stmts = [
            s for s in sqlglot.parse(stripped, read=dialect)
            if s is not None and not isinstance(s, exp.Semicolon)
        ]
        if stmts:
            results = []
            for s in stmts:
                stmt_sql = s.sql(dialect=dialect) if dialect else s.sql()
                stmt_sql = stmt_sql.rstrip(";").strip()
                if stmt_sql:
                    results.append(stmt_sql)
            if results:
                return results
    except Exception:
        pass

    # Fallback: state-machine tokenizer (handles quotes, comments, backticks)
    statements = []
    current = []
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    n = len(stripped)

    while i < n:
        c = stripped[i]
        nxt = stripped[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            current.append(c)
        elif in_block_comment:
            current.append(c)
            if c == "*" and nxt == "/":
                current.append(nxt)
                i += 1
                in_block_comment = False
        elif in_single:
            current.append(c)
            if c == "\x27":
                if nxt == "\x27":
                    current.append(nxt)
                    i += 1
                else:
                    in_single = False
        elif in_double:
            current.append(c)
            if c == "\"":
                if nxt == "\"":
                    current.append(nxt)
                    i += 1
                else:
                    in_double = False
        elif in_backtick:
            current.append(c)
            if c == "`":
                in_backtick = False
        else:
            if c == "-" and nxt == "-":
                in_line_comment = True
                current.append(c)
                current.append(nxt)
                i += 1
            elif c == "/" and nxt == "*":
                in_block_comment = True
                current.append(c)
                current.append(nxt)
                i += 1
            elif c == "\x27":
                in_single = True
                current.append(c)
            elif c == "\"":
                in_double = True
                current.append(c)
            elif c == "`":
                in_backtick = True
                current.append(c)
            elif c == ";":
                stmt = "".join(current).strip()
                # Skip pure comment blocks
                if stmt and not all(line.strip().startswith(("--", "/*")) for line in stmt.splitlines() if line.strip()):
                    statements.append(stmt)
                current = []
            else:
                current.append(c)
        i += 1

    rem = "".join(current).strip()
    if rem and not all(line.strip().startswith(("--", "/*")) for line in rem.splitlines() if line.strip()):
        statements.append(rem)

    return statements


def parseSqlStatementIntoAbstractSyntaxTree(sql: str, dialect: str = "postgres") -> exp.Expression:
    """Parse raw SQL query string into a sqlglot Abstract Syntax Tree representation.

    Raises:
        SanitizationError: if parsing fails or multiple statements are detected.
    """
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if len(statements) > 1:
        raise SanitizationError(f"Multiple statements detected: {statements}")
    try:
        return sqlglot.parse_one(sql, dialect=dialect, read=dialect)
    except Exception as exc:
        raise SanitizationError(f"Failed to parse SQL: {exc}") from exc


def verifyAbstractSyntaxTreeContainsNoRawLiterals(abstractSyntaxTree: exp.Expression, dialect: str = "postgres") -> None:
    """Inspect AST to guarantee that no unparameterized raw literal values remain in the statement."""
    for node in abstractSyntaxTree.walk():
        if (
            isinstance(node, exp.Literal)
            and not isinstance(node, exp.Boolean)
            and not node.find_ancestor(exp.Parameter)
        ):
            raise SanitizationError(
                "Literal value still present after transformation — unsafe input detected"
            )


def sanitizeAndExtractParametersFromSqlAst(sql: str, dialect: str = "postgres") -> ParameterizedStatement:
    """Sanitize raw SQL statement by extracting all literals and booleans into positional/placeholder parameters."""
    parsed = parseSqlStatementIntoAbstractSyntaxTree(sql, dialect=dialect)
    params: List[Any] = []
    param_counter = 1

    def transformAstLiteralNode(node: exp.Expression) -> exp.Expression:
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

    transformed = parsed.transform(transformAstLiteralNode, copy=False)
    result_sql = transformed.sql(dialect=dialect)

    # Sanity check: no unparameterized raw literals left
    check = sqlglot.parse_one(result_sql, dialect=dialect)
    verifyAbstractSyntaxTreeContainsNoRawLiterals(check, dialect=dialect)

    return ParameterizedStatement(
        sql=result_sql,
        params=tuple(params),
        dialect=dialect,
    )


def sanitizeAndParameterizePostgreSqlStatement(sql: str) -> ParameterizedStatement:
    """Convenience helper to sanitize and parameterize a query targeting PostgreSQL."""
    return sanitizeAndExtractParametersFromSqlAst(sql, dialect="postgres")


# Aliases for backward compatibility and alternate conventions
parse_sql = parseSqlStatementIntoAbstractSyntaxTree
sanitize_sql = sanitizeAndExtractParametersFromSqlAst
sanitize_with_postgres = sanitizeAndParameterizePostgreSqlStatement
is_multi_statement = detectMultipleStackedSqlStatements


__all__ = [
    "ParameterizedStatement",
    "SanitizationError",
    "detectMultipleStackedSqlStatements",
    "is_multi_statement",
    "parseSqlStatementIntoAbstractSyntaxTree",
    "verifyAbstractSyntaxTreeContainsNoRawLiterals",
    "sanitizeAndExtractParametersFromSqlAst",
    "sanitizeAndParameterizePostgreSqlStatement",
    "parse_sql",
    "sanitize_sql",
    "sanitize_with_postgres",
    "split_sql_script",
]
