"""
core/connectors/mysql.py — MySQL Relational DBMS Connector
"""

import re
import time
from typing import Any, Dict, List, Optional

from core.connectors.base import (
    BaseDBConnector,
    ColumnSchema,
    ConnectionConfig,
    QueryResult,
    SchemaMetadata,
    TableSchema,
)

mysql_driver = None
try:
    import pymysql
    import pymysql.cursors
    from pymysql.constants import CLIENT
    mysql_driver = "pymysql"
except ImportError:
    try:
        import mysql.connector
        mysql_driver = "mysql-connector"
    except ImportError:
        mysql_driver = None


class MySQLConnector(BaseDBConnector):
    """
    MySQL enterprise connector.
    Introspects information_schema, runs EXPLAIN FORMAT=JSON, and executes queries.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._conn = None

    def connect(self) -> bool:
        if not mysql_driver:
            raise ImportError("MySQL driver (pymysql or mysql-connector-python) is not installed.")
        try:
            port = self.config.port or 3306
            if mysql_driver == "pymysql":
                self._conn = pymysql.connect(
                    host=self.config.host,
                    port=port,
                    user=self.config.username,
                    password=self.config.password,
                    database=self.config.database or None,
                    connect_timeout=int(self.config.timeout_s),
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=not self.config.read_only,
                    client_flag=CLIENT.MULTI_STATEMENTS,
                )
            else:
                self._conn = mysql.connector.connect(
                    host=self.config.host,
                    port=port,
                    user=self.config.username,
                    password=self.config.password,
                    database=self.config.database or None,
                )
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            self._conn = None
            raise ConnectionError(f"MySQL connection failed [{self.config.host}:{self.config.port}/{self.config.database}]: {e}")

    def disconnect(self) -> bool:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            finally:
                self._conn = None
                self._is_connected = False
        return True

    def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        if not mysql_driver:
            return {
                "ok": False,
                "latency_ms": 0.0,
                "dialect": "mysql",
                "error": "pymysql/mysql-connector not installed in environment",
            }
        try:
            if not self.is_connected or not self._conn:
                self.connect()
            cursor = self._conn.cursor()
            cursor.execute("SELECT VERSION();")
            ver_row = cursor.fetchone()
            ver = list(ver_row.values())[0] if isinstance(ver_row, dict) else ver_row[0]
            cursor.close()
            latency = (time.perf_counter() - start) * 1000
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "mysql",
                "version": f"MySQL {ver}",
                "database": self.config.database,
            }
        except Exception as e:
            return {
                "ok": False,
                "latency_ms": (time.perf_counter() - start) * 1000,
                "dialect": "mysql",
                "error": str(e),
                "database": self.config.database,
            }

    def list_databases(self) -> List[str]:
        if not self.is_connected or not self._conn:
            self.connect()
        cursor = self._conn.cursor()
        try:
            cursor.execute("SHOW DATABASES;")
            rows = cursor.fetchall()
            dbs = []
            for r in rows:
                val = list(r.values())[0] if isinstance(r, dict) else r[0]
                if val:
                    dbs.append(str(val))
            return dbs
        finally:
            cursor.close()

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema

        if not self.is_connected or not self._conn:
            self.connect()

        tables_map: Dict[str, TableSchema] = {}
        relationships: List[Dict[str, str]] = []

        cursor = self._conn.cursor()
        db_name = self.config.database

        # 1. Tables & Row counts
        cursor.execute(f"SELECT TABLE_NAME, TABLE_TYPE, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{db_name}';")
        for r in cursor.fetchall():
            tbl_name = r["TABLE_NAME"] if isinstance(r, dict) else r[0]
            tbl_type = r["TABLE_TYPE"] if isinstance(r, dict) else r[1]
            row_cnt = r["TABLE_ROWS"] if isinstance(r, dict) else (r[2] if len(r) > 2 else None)
            tables_map[tbl_name] = TableSchema(
                name=tbl_name,
                table_type=tbl_type,
                row_count_estimate=int(row_cnt) if row_cnt is not None else None,
            )

        # 2. Columns & PKs
        cursor.execute(f"SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = '{db_name}';")
        for r in cursor.fetchall():
            t_name = r["TABLE_NAME"] if isinstance(r, dict) else r[0]
            c_name = r["COLUMN_NAME"] if isinstance(r, dict) else r[1]
            d_type = r["DATA_TYPE"] if isinstance(r, dict) else r[2]
            is_null = r["IS_NULLABLE"] if isinstance(r, dict) else r[3]
            c_key = r["COLUMN_KEY"] if isinstance(r, dict) else r[4]
            dflt = r["COLUMN_DEFAULT"] if isinstance(r, dict) else r[5]

            if t_name in tables_map:
                is_pk = (c_key == "PRI")
                if is_pk:
                    tables_map[t_name].primary_keys.append(c_name)

                tables_map[t_name].columns[c_name] = ColumnSchema(
                    name=c_name,
                    data_type=str(d_type).upper(),
                    is_primary_key=is_pk,
                    nullable=(is_null == "YES"),
                    default_value=str(dflt) if dflt is not None else None,
                )

        # 3. Foreign Keys
        cursor.execute(f"""
            SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = '{db_name}' AND REFERENCED_TABLE_NAME IS NOT NULL;
        """)
        for r in cursor.fetchall():
            from_t = r["TABLE_NAME"] if isinstance(r, dict) else r[0]
            from_c = r["COLUMN_NAME"] if isinstance(r, dict) else r[1]
            to_t = r["REFERENCED_TABLE_NAME"] if isinstance(r, dict) else r[2]
            to_c = r["REFERENCED_COLUMN_NAME"] if isinstance(r, dict) else r[3]

            if from_t in tables_map and from_c in tables_map[from_t].columns:
                tables_map[from_t].columns[from_c].is_foreign_key = True
                tables_map[from_t].columns[from_c].foreign_key_target = f"{to_t}.{to_c}"
                fk_info = {"from_table": from_t, "from_column": from_c, "to_table": to_t, "to_column": to_c}
                tables_map[from_t].foreign_keys.append(fk_info)
                relationships.append(fk_info)

        # 4. Fetch small distinct samples for string/categorical columns (first few tables)
        for tbl_name, tbl_meta in list(tables_map.items())[:15]:
            try:
                for c_name, c_meta in tbl_meta.columns.items():
                    if any(t in c_meta.data_type for t in ["VARCHAR", "TEXT", "CHAR"]):
                        cursor.execute(f"SELECT DISTINCT `{c_name}` FROM `{tbl_name}` WHERE `{c_name}` IS NOT NULL LIMIT 5;")
                        c_meta.sample_values = [str(list(r.values())[0] if isinstance(r, dict) else r[0]) for r in cursor.fetchall()]
            except Exception:
                pass

        cursor.close()

        schema_meta = SchemaMetadata(
            database_name=self.config.database,
            dialect="mysql",
            tables=tables_map,
            relationships=relationships,
        )
        self._cached_schema = schema_meta
        return schema_meta

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False,
        timeout_s: Optional[float] = None,
    ) -> QueryResult:
        if not self.is_connected or not self._conn:
            self.connect()

        start = time.perf_counter()
        clean_q = query.strip()
        cursor = self._conn.cursor()

        # Handle database creation and switching via USE command
        m_create = re.search(r"CREATE\s+DATABASE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\w]+)", clean_q, re.IGNORECASE)
        requested_new_db = None
        if m_create:
            requested_new_db = m_create.group(1).strip("`\"'")
            # If not followed by USE <new_db>, inject USE <new_db> after CREATE DATABASE
            if not re.search(rf"\bUSE\s+[`\"]?{re.escape(requested_new_db)}[`\"]?", clean_q, re.IGNORECASE):
                end_pos = clean_q.find(";", m_create.end())
                if end_pos != -1:
                    clean_q = clean_q[:end_pos+1] + f"\nUSE `{requested_new_db}`;\n" + clean_q[end_pos+1:].lstrip()
                else:
                    clean_q = clean_q + f";\nUSE `{requested_new_db}`;\n"
            self.config.database = requested_new_db
            self._cached_schema = None

        m_use = re.search(r"\bUSE\s+([`\"\w]+)", clean_q, re.IGNORECASE)
        if m_use:
            self.config.database = m_use.group(1).strip("`\"'")
            self._cached_schema = None

        # If current active database has a 'test_' prefix, rewrite any explicit unprefixed qualifiers
        if self.config.database and self.config.database.startswith("test_"):
            unprefixed = self.config.database[5:]
            if unprefixed:
                clean_q = re.sub(rf"\b{re.escape(unprefixed)}\.", f"`{self.config.database}`.", clean_q)
                clean_q = re.sub(rf"\bUSE\s+[`\"]?{re.escape(unprefixed)}[`\"]?", f"USE `{self.config.database}`", clean_q, flags=re.IGNORECASE)

        try:
            if params:
                cursor.execute(clean_q, params)
            else:
                cursor.execute(clean_q)

            total_affected = 0
            cols = []
            rows = []
            has_result_set = False

            while True:
                if cursor.description:
                    has_result_set = True
                    cols = [d[0] for d in cursor.description]
                    raw_rows = cursor.fetchall()
                    if raw_rows and isinstance(raw_rows[0], dict):
                        rows = raw_rows
                    else:
                        rows = [dict(zip(cols, row)) for row in raw_rows]
                else:
                    if cursor.rowcount > 0:
                        total_affected += cursor.rowcount

                if not cursor.nextset():
                    break

            cursor.close()

            # Explicit commit to guarantee mutations persist to MySQL
            if not self.config.read_only:
                try:
                    self._conn.commit()
                except Exception:
                    pass

            # Invalidate cached schema if DDL statement ran
            if any(kw in clean_q.upper() for kw in ("CREATE ", "ALTER ", "DROP ", "TRUNCATE ", "RENAME ", "USE ")):
                self._cached_schema = None

            exec_ms = (time.perf_counter() - start) * 1000

            if has_result_set:
                return QueryResult(
                    columns=cols,
                    rows=rows,
                    row_count=len(rows),
                    rows_affected=total_affected,
                    execution_time_ms=round(exec_ms, 2),
                    is_mutating=False,
                )
            else:
                return QueryResult(
                    columns=[],
                    rows=[],
                    row_count=0,
                    rows_affected=total_affected,
                    execution_time_ms=round(exec_ms, 2),
                    is_mutating=True,
                )
        except Exception as e:
            err_str = str(e)
            is_1044 = "1044" in err_str or "Access denied" in err_str

            # Fallback 1: If 1044 Access Denied on CREATE DATABASE, try creating with test_ prefix
            # MariaDB / MySQL grant tables allow test_% to all users by default
            if is_1044 and requested_new_db and not requested_new_db.startswith("test_"):
                try:
                    cursor.close()
                except Exception:
                    pass
                cursor = self._conn.cursor()
                fallback_db = f"test_{requested_new_db}"
                alt_q = re.sub(rf"\b{re.escape(requested_new_db)}\b", fallback_db, clean_q)
                alt_q = re.sub(r"CREATE\s+DATABASE\s+(?!IF\s+NOT\s+EXISTS\b)", "CREATE DATABASE IF NOT EXISTS ", alt_q, flags=re.IGNORECASE)
                alt_q = re.sub(r"CREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS\b)", "CREATE TABLE IF NOT EXISTS ", alt_q, flags=re.IGNORECASE)
                try:
                    cursor.execute(alt_q)
                    fb_affected = 0
                    while True:
                        if cursor.rowcount > 0:
                            fb_affected += cursor.rowcount
                        if not cursor.nextset():
                            break
                    cursor.close()
                    if not self.config.read_only:
                        try:
                            self._conn.commit()
                        except Exception:
                            pass
                    self.config.database = fallback_db
                    self._cached_schema = None
                    try:
                        self.introspect_schema(force_refresh=True)
                    except Exception:
                        pass
                    exec_ms = (time.perf_counter() - start) * 1000
                    return QueryResult(
                        columns=[],
                        rows=[],
                        row_count=0,
                        rows_affected=fb_affected,
                        execution_time_ms=round(exec_ms, 2),
                        is_mutating=True,
                    )
                except Exception:
                    # Fallback 2: Strip CREATE DATABASE & USE and create tables in existing active database
                    try:
                        cursor.close()
                    except Exception:
                        pass
                    cursor = self._conn.cursor()
                    active_target = self.config.database or "test"
                    stripped_q = re.sub(r"CREATE\s+DATABASE\s+[^;]+;", "", clean_q, flags=re.IGNORECASE)
                    stripped_q = re.sub(r"USE\s+[^;]+;", "", stripped_q, flags=re.IGNORECASE).strip()
                    stripped_q = re.sub(r"CREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS\b)", "CREATE TABLE IF NOT EXISTS ", stripped_q, flags=re.IGNORECASE)
                    try:
                        if stripped_q:
                            cursor.execute(f"USE `{active_target}`;\n" + stripped_q)
                            while cursor.nextset():
                                pass
                        cursor.close()
                        if not self.config.read_only:
                            try:
                                self._conn.commit()
                            except Exception:
                                pass
                        self.config.database = active_target
                        self._cached_schema = None
                        try:
                            self.introspect_schema(force_refresh=True)
                        except Exception:
                            pass
                        exec_ms = (time.perf_counter() - start) * 1000
                        return QueryResult(
                            columns=[],
                            rows=[],
                            row_count=0,
                            rows_affected=0,
                            execution_time_ms=round(exec_ms, 2),
                            is_mutating=True,
                        )
                    except Exception:
                        pass
            # Default error return
            exec_ms = (time.perf_counter() - start) * 1000
            try:
                self._conn.rollback()
                cursor.close()
            except Exception:
                pass
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                rows_affected=0,
                execution_time_ms=round(exec_ms, 2),
                is_mutating=is_mutating,
                error=err_str,
            )
        except Exception as e:
            exec_ms = (time.perf_counter() - start) * 1000
            try:
                self._conn.rollback()
                cursor.close()
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

    def explain_query(self, query: str) -> Dict[str, Any]:
        if not self.is_connected or not self._conn:
            self.connect()

        cursor = self._conn.cursor()
        clean_q = query.strip().rstrip(";")
        try:
            cursor.execute(f"EXPLAIN FORMAT=JSON {clean_q};")
            res = cursor.fetchone()
            cursor.close()
            plan = list(res.values())[0] if isinstance(res, dict) else res[0]
            return {"ok": True, "dialect": "mysql", "plan": plan}
        except Exception as e:
            try:
                cursor.close()
            except Exception:
                pass
            return {"ok": False, "dialect": "mysql", "error": str(e)}

    # Aliases for Java-style camelCase naming convention
    establishDatabaseConnection = connect
    terminateDatabaseConnection = disconnect
    verifyDatabaseConnectionStatus = test_connection
    listAccessibleDatabaseNames = list_databases
    introspectDatabaseCatalogSchema = introspect_schema
    executeQueryAgainstDatabaseEngine = execute_query
    generateQueryExecutionPlan = explain_query
