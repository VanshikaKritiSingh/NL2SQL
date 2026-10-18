"""
core/connectors/sqlite.py — High-Performance SQLite Connector (Stdlib Embedded)
"""

import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

from core.connectors.base import (
    BaseDBConnector,
    ColumnSchema,
    ConnectionConfig,
    ConnectorType,
    QueryResult,
    SchemaMetadata,
    TableSchema,
)


class SQLiteConnector(BaseDBConnector):
    """
    Standard-library embedded SQLite connector.
    Supports in-memory (`:memory:`) or persistent disk databases.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._conn: Optional[sqlite3.Connection] = None

    def establishDatabaseConnection(self) -> bool:
        try:
            db_path = self.config.database
            if db_path != ":memory:":
                if not os.path.isabs(db_path):
                    db_path = os.path.abspath(db_path)
                create_if_missing = self.config.extra_params.get("create_if_missing", False)
                if not os.path.exists(db_path) and not create_if_missing:
                    raise FileNotFoundError(f"SQLite database file not found: {db_path}")

            self._conn = sqlite3.connect(
                db_path,
                timeout=self.config.timeout_s,
                check_same_thread=False,
            )
            # Enable FK enforcement and WAL mode for concurrency
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.row_factory = sqlite3.Row
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            self._conn = None
            raise ConnectionError(f"Failed to connect to SQLite [{self.config.database}]: {e}")

    def terminateDatabaseConnection(self) -> bool:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            finally:
                self._conn = None
                self._is_connected = False
        return True

    def verifyDatabaseConnectionStatus(self) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            if not self.is_connected or not self._conn:
                self.establishDatabaseConnection()
            cursor = self._conn.cursor()
            cursor.execute("SELECT sqlite_version();")
            ver = cursor.fetchone()[0]
            # Run quick_check to verify database header and pages integrity
            cursor.execute("PRAGMA quick_check(1);")
            check_res = cursor.fetchone()
            if check_res and check_res[0] != "ok":
                raise ValueError(f"SQLite integrity check failed: {check_res[0]}")
            latency = (time.perf_counter() - start) * 1000
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "sqlite",
                "version": f"SQLite {ver}",
                "database": self.config.database,
            }
        except Exception as e:
            return {
                "ok": False,
                "latency_ms": (time.perf_counter() - start) * 1000,
                "dialect": "sqlite",
                "error": str(e),
                "database": self.config.database,
            }

    def introspectDatabaseCatalogSchema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema

        if not self.is_connected or not self._conn:
            self.establishDatabaseConnection()

        tables_map: Dict[str, TableSchema] = {}
        relationships: List[Dict[str, str]] = []

        cursor = self._conn.cursor()
        # Fetch all user tables and views
        cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%';")
        db_objects = cursor.fetchall()

        for obj in db_objects:
            tbl_name = obj[0]
            tbl_type = "VIEW" if obj[1] == "view" else "TABLE"
            tbl_schema = TableSchema(name=tbl_name, table_type=tbl_type)

            # Columns via PRAGMA table_info
            col_cursor = self._conn.cursor()
            col_cursor.execute(f"PRAGMA table_info('{tbl_name}');")
            # columns: cid, name, type, notnull, dflt_value, pk
            for col in col_cursor.fetchall():
                c_name = col[1]
                c_type = col[2] or "TEXT"
                c_notnull = bool(col[3])
                c_dflt = str(col[4]) if col[4] is not None else None
                c_pk = bool(col[5])

                if c_pk:
                    tbl_schema.primary_keys.append(c_name)

                tbl_schema.columns[c_name] = ColumnSchema(
                    name=c_name,
                    data_type=c_type.upper(),
                    is_primary_key=c_pk,
                    nullable=not c_notnull,
                    default_value=c_dflt,
                )

            # Foreign Keys via PRAGMA foreign_key_list
            fk_cursor = self._conn.cursor()
            try:
                fk_cursor.execute(f"PRAGMA foreign_key_list('{tbl_name}');")
                # columns: id, seq, table, from, to, on_update, on_delete, match
                for fk in fk_cursor.fetchall():
                    target_table = fk[2]
                    from_col = fk[3]
                    to_col = fk[4]
                    if from_col in tbl_schema.columns:
                        tbl_schema.columns[from_col].is_foreign_key = True
                        tbl_schema.columns[from_col].foreign_key_target = f"{target_table}.{to_col}"

                    fk_info = {
                        "from_table": tbl_name,
                        "from_column": from_col,
                        "to_table": target_table,
                        "to_column": to_col,
                    }
                    tbl_schema.foreign_keys.append(fk_info)
                    relationships.append(fk_info)
            except Exception:
                pass

            # Sample values & row count estimate
            try:
                cnt_cursor = self._conn.cursor()
                cnt_cursor.execute(f"SELECT COUNT(*) FROM \"{tbl_name}\";")
                tbl_schema.row_count_estimate = cnt_cursor.fetchone()[0]

                # Fetch small distinct samples for string/categorical columns
                for c_name, c_meta in tbl_schema.columns.items():
                    if any(t in c_meta.data_type for t in ["VARCHAR", "TEXT", "CHAR"]):
                        sample_cur = self._conn.cursor()
                        sample_cur.execute(f"SELECT DISTINCT \"{c_name}\" FROM \"{tbl_name}\" WHERE \"{c_name}\" IS NOT NULL LIMIT 5;")
                        c_meta.sample_values = [str(r[0]) for r in sample_cur.fetchall()]
            except Exception:
                pass

            tables_map[tbl_name] = tbl_schema

        schema_meta = SchemaMetadata(
            database_name=self.config.database,
            dialect="sqlite",
            tables=tables_map,
            relationships=relationships,
        )
        self._cached_schema = schema_meta
        return schema_meta

    def executeQueryAgainstDatabaseEngine(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False,
        timeout_s: Optional[float] = None,
    ) -> QueryResult:
        if not self.is_connected or not self._conn:
            self.establishDatabaseConnection()

        start = time.perf_counter()
        clean_q = query.strip().rstrip(";")
        cursor = self._conn.cursor()

        try:
            if params:
                cursor.execute(clean_q, params)
            else:
                cursor.execute(clean_q)

            exec_ms = (time.perf_counter() - start) * 1000

            # If SELECT / PRAGMA / EXPLAIN with descriptions
            if cursor.description:
                cols = [d[0] for d in cursor.description]
                raw_rows = cursor.fetchall()
                rows = [dict(zip(cols, row)) for row in raw_rows]
                return QueryResult(
                    columns=cols,
                    rows=rows,
                    row_count=len(rows),
                    rows_affected=0,
                    execution_time_ms=round(exec_ms, 2),
                    is_mutating=False,
                )
            else:
                # DML / DDL statement
                affected = cursor.rowcount
                if is_mutating or not self.config.read_only:
                    self._conn.commit()
                return QueryResult(
                    columns=[],
                    rows=[],
                    row_count=0,
                    rows_affected=affected if affected >= 0 else 0,
                    execution_time_ms=round(exec_ms, 2),
                    is_mutating=True,
                )
        except Exception as e:
            exec_ms = (time.perf_counter() - start) * 1000
            if self._conn:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                rows_affected=0,
                execution_time_ms=round(exec_ms, 2),
                is_mutating=is_mutating,
                error=str(e),
            )

    def generateQueryExecutionPlan(self, query: str) -> Dict[str, Any]:
        if not self.is_connected or not self._conn:
            self.establishDatabaseConnection()

        cursor = self._conn.cursor()
        clean_q = query.strip().rstrip(";")
        try:
            cursor.execute(f"EXPLAIN QUERY PLAN {clean_q};")
            # Columns: id, parent, notused, detail
            plan_rows = cursor.fetchall()
            steps = []
            has_scan = False
            has_index = False
            for row in plan_rows:
                detail = str(row[3])
                steps.append({"id": row[0], "parent": row[1], "detail": detail})
                if "SCAN" in detail:
                    has_scan = True
                if "USING INDEX" in detail or "USING COVERING INDEX" in detail:
                    has_index = True

            return {
                "ok": True,
                "dialect": "sqlite",
                "plan_steps": steps,
                "has_full_scan": has_scan,
                "uses_index": has_index,
            }
        except Exception as e:
            return {"ok": False, "dialect": "sqlite", "error": str(e)}

    # Aliases for backward compatibility
    connect = establishDatabaseConnection
    disconnect = terminateDatabaseConnection
    test_connection = verifyDatabaseConnectionStatus
    introspect_schema = introspectDatabaseCatalogSchema
    execute_query = executeQueryAgainstDatabaseEngine
    explain_query = generateQueryExecutionPlan
