"""M9 interfaces and fakes.

SchemaProvider gives read-only metadata about tables/columns.
AuditLogger records validation events; ListAuditLogger is a simple in-memory version.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

# ------------------------------------------------------------------
# SchemaProvider
# ------------------------------------------------------------------

class SchemaProvider(ABC):
    """Read-only view of the database schema.

    M9 receives this as a parameter; it never calls back to a live DB.
    """

    @abstractmethod
    def get_tables(self) -> Tuple[str, ...]:
        """Return all table names in the schema."""

    @abstractmethod
    def get_table(self, name: str) -> Optional[Dict]:
        """Return table metadata dict or None if table missing.

        Expected keys: "columns", "pk", "fks", "indexes", "row_count".
        Each sub-key maps to a dict of column name -> column spec.
        """

    @abstractmethod
    def get_columns(self, table_name: str) -> Tuple[Tuple[str, str], ...]:
        """Return (column_name, column_type) pairs for a table.

        Column spec includes type and any nullability info if needed.
        """

    @abstractmethod
    def get_rows(self, table_name: str) -> int:
        """Estimated or actual row count for a table (for anti-pattern checks)."""


@dataclass(frozen=True, slots=True)
class TableSpec:
    """Internal representation of a single table.

    Built by FakeSchemaProvider from JSON/YAML; used by rules.
    """

    name: str
    columns: Dict[str, str]  # column_name -> column_type
    pk: FrozenSet[str]  # primary key column names
    fks: Dict[str, Tuple[str, str]]  # local_fk_col -> (referenced_table, referenced_col)
    indexes: Dict[str, Tuple[str, ...]]  # index_name -> (col_name, ...)
    row_count: int
    nullable: Dict[str, bool]  # column_name -> is_nullable (True if NULL allowed)


class FakeSchemaProvider(SchemaProvider):
    """In‑memory fake that loads from a JSON/YAML file (or stub data).

    In tests we provide a JSON fixture; in production the real provider
    would read from a DB or config store.
    """

    def __init__(self, schema: Dict):
        self._schema = schema
        self._tables: Dict[str, TableSpec] = {}
        self._build()

    def _build(self):
        for tbl in self._schema.get("tables", []):
            name = tbl["name"]
            cols = tbl.get("columns", {})
            pk = set(tbl.get("pk", []))
            fks = tbl.get("fks", {})
            indexes = tbl.get("indexes", {})
            row_count = int(tbl.get("row_count", 0))
            nullable = {col: bool(tbl.get("nullable", []).get(col, False)) for col in cols}
            self._tables[name] = TableSpec(
                name=name,
                columns=cols,
                pk=frozenset(pk),
                fks=frozenset(fks.items()),
                indexes=frozenset({idx: tuple(cols) for idx, cols in indexes.items()}),
                row_count=row_count,
                nullable=nullable,
            )

    # SchemaProvider API -------------------------------------------------
    def get_tables(self) -> Tuple[str, ...]:
        return tuple(self._tables.keys())

    def get_table(self, name: str) -> Optional[Dict]:
        return {
            "columns": self._tables[name].columns,
            "pk": list(self._tables[name].pk),
            "fks": dict(self._tables[name].fks),
            "indexes": {idx: list(cols) for idx, cols in self._tables[name].indexes.items()},
            "row_count": self._tables[name].row_count,
        }

    def get_columns(self, table_name: str) -> Tuple[Tuple[str, str], ...]:
        return tuple((col, typ) for col, typ in self._tables[table_name].columns.items())

    def get_rows(self, table_name: str) -> int:
        return self._tables[table_name].row_count

    # Convenience helpers ------------------------------------------------
    def _get_table_spec(self, name: str) -> Optional[TableSpec]:
        return self._tables.get(name)


# ------------------------------------------------------------------
# AuditLogger
# ------------------------------------------------------------------

class AuditLogger(ABC):
    """Cross‑cutting logger for M9 validation events."""

    @abstractmethod
    def log_validation(self, sql: str, result: ValidationResult) -> None:
        """Record the validation outcome and any issues."""


@dataclass(frozen=True, slots=True)
class ListAuditLogger(AuditLogger):
    """Simple in‑memory logger used in tests and early development."""

    records: List[Tuple[str, ValidationResult]] = field(default_factory=list)

    def log_validation(self, sql: str, result: ValidationResult) -> None:
        self.records.append((sql, result))


# ------------------------------------------------------------------
# Parse utilities (used by engine.py)
# ------------------------------------------------------------------

from sqlglot import parse_one, exp

def parse_sql(sql: str, dialect: str = "postgres") -> exp.Expression:
    """Parse a single SQL statement with sqlglot.

    Raises:
        ValueError: if parsing fails or multiple statements are detected.
    """
    try:
        # sqlglot parses a single expression/statement; we need to ensure
        # there is exactly one top‑level statement.
        expr = parse_one(sql, dialect=dialect)
        # Quick check: sqlglot may parse multiple statements if we feed it a string
        # containing ';'. We split and verify exactly one statement.
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        if len(statements) != 1:
            raise ValueError(f"Multiple statements detected: {statements}")
        return expr
    except Exception as exc:
        raise ValueError(f"Unable to parse SQL: {exc}") from exc


def is_multi_statement(sql: str) -> bool:
    """Detect stacked queries separated by semicolons or comment tricks."""
    # Basic split on semicolons; more sophisticated detection could look inside comments.
    return len([s for s in sql.split(";") if s.strip()]) > 1


def reject_unparseable(sql: str) -> bool:
    """True if sql cannot be parsed by sqlglot."""
    try:
        parse_sql(sql)
        return False
    except ValueError:
        return True