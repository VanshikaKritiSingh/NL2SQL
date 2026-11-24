# routers/schema.py
from typing import Optional
import logging
from fastapi import APIRouter, Query
from models.schema import SchemaInfo, TableInfo, ColumnInfo, ForeignKey
from mock_data.schemas import get_mock_ecommerce_schema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schema", tags=["Schema Explorer"])


def _build_schema_from_connection(conn, dialect: str) -> Optional[SchemaInfo]:
    """Tries to build a SchemaInfo from a live DB connection's introspected schema."""
    try:
        schema_meta = conn.introspect_schema(force_refresh=True)
        db_name = conn.config.database if conn.config else "unknown"
        if not schema_meta or not schema_meta.tables:
            return SchemaInfo(
                dialect=dialect,
                database_name=db_name,
                tables=[],
                foreign_keys=[],
                total_tables=0,
                total_columns=0,
            )

        tbl_infos = []
        all_fks = []
        db_name = conn.config.database if conn.config else "unknown"

        for t_name, t_schema in schema_meta.tables.items():
            col_infos = []
            pks = getattr(t_schema, "primary_keys", [])
            fks_list = getattr(t_schema, "foreign_keys", [])

            # Build FK lookup from table-level foreign_keys list (supports both dict and object)
            fk_col_map = {}
            for fk in fks_list:
                if isinstance(fk, dict):
                    from_col = fk.get("column") or fk.get("from_column")
                    to_table = fk.get("references_table") or fk.get("to_table") or fk.get("ref_table")
                    to_col = fk.get("references_column") or fk.get("to_column") or fk.get("ref_column")
                else:
                    from_col = getattr(fk, "column", None) or getattr(fk, "from_column", None)
                    to_table = getattr(fk, "references_table", None) or getattr(fk, "to_table", None) or getattr(fk, "ref_table", None)
                    to_col = getattr(fk, "references_column", None) or getattr(fk, "to_column", None) or getattr(fk, "ref_column", None)

                if from_col and to_table and to_col:
                    fk_col_map[from_col] = (to_table, to_col)
                    all_fks.append(ForeignKey(
                        from_table=t_name,
                        from_column=from_col,
                        to_table=to_table,
                        to_column=to_col,
                    ))

            cols = getattr(t_schema, "columns", {})
            if isinstance(cols, dict):
                col_items = cols.items()
            else:
                col_items = []

            for c_name, c_schema in col_items:
                if isinstance(c_schema, dict):
                    is_pk = c_name in pks or c_schema.get("is_primary_key", False)
                    fk_target = fk_col_map.get(c_name)
                    is_fk = bool(fk_target) or c_schema.get("is_foreign_key", False)
                    data_type = c_schema.get("data_type") or c_schema.get("type", "VARCHAR")
                    nullable_val = c_schema.get("nullable")
                    sample_vals = c_schema.get("sample_values", []) or []
                    def_val = c_schema.get("default_value")
                    fk_tgt = c_schema.get("foreign_key_target")
                else:
                    is_pk = c_name in pks or getattr(c_schema, "is_primary_key", False)
                    fk_target = fk_col_map.get(c_name)
                    is_fk = bool(fk_target) or getattr(c_schema, "is_foreign_key", False)
                    data_type = getattr(c_schema, "data_type", None) or getattr(c_schema, "type", "VARCHAR")
                    nullable_val = getattr(c_schema, "nullable", None)
                    sample_vals = getattr(c_schema, "sample_values", []) or []
                    def_val = getattr(c_schema, "default_value", None)
                    fk_tgt = getattr(c_schema, "foreign_key_target", None)

                if fk_target:
                    ref_str = f"{fk_target[0]}.{fk_target[1]}"
                elif is_fk and fk_tgt:
                    ref_str = fk_tgt
                else:
                    ref_str = None

                if nullable_val is None:
                    nullable_val = not is_pk

                col_infos.append(ColumnInfo(
                    name=c_name,
                    data_type=data_type,
                    is_primary_key=is_pk,
                    is_foreign_key=is_fk,
                    fk_references=ref_str,
                    nullable=nullable_val,
                    sample_values=sample_vals[:5] if sample_vals else [],
                    default_value=str(def_val) if def_val is not None else None,
                ))

            row_cnt = getattr(t_schema, "row_count_estimate", None)
            tbl_infos.append(TableInfo(name=t_name, columns=col_infos, row_count=row_cnt))

        return SchemaInfo(
            dialect=dialect,
            database_name=db_name,
            tables=tbl_infos,
            foreign_keys=all_fks,
        )
    except Exception:
        db_name = conn.config.database if conn and conn.config and conn.config.database else "scratch"
        return SchemaInfo(
            dialect=dialect,
            database_name=db_name,
            tables=[],
            foreign_keys=[],
            total_tables=0,
            total_columns=0,
        )


def _build_schema_from_orchestrator(dialect: str) -> Optional[SchemaInfo]:
    """Tries to build a SchemaInfo from the query orchestrator's cached schema tables."""
    try:
        from routers.query import orchestrator
        if orchestrator and orchestrator.tables:
            tbl_infos = []
            all_fks = []
            for t_name, t_meta in orchestrator.tables.items():
                col_infos = []
                for c_name, c_meta in t_meta.columns.items():
                    ref_str = (
                        f"{c_meta.fk_target_table}.{c_meta.fk_target_column}"
                        if c_meta.is_fk and c_meta.fk_target_table else None
                    )
                    col_infos.append(ColumnInfo(
                        name=c_name,
                        data_type=c_meta.dtype.split()[0] if c_meta.dtype else "VARCHAR",
                        is_primary_key=c_meta.is_pk,
                        is_foreign_key=c_meta.is_fk,
                        fk_references=ref_str,
                        nullable=not c_meta.is_pk,
                    ))
                    if c_meta.is_fk and c_meta.fk_target_table:
                        all_fks.append(ForeignKey(
                            from_table=t_name,
                            from_column=c_name,
                            to_table=c_meta.fk_target_table,
                            to_column=c_meta.fk_target_column or "id",
                        ))
                tbl_infos.append(TableInfo(name=t_name, columns=col_infos))

            if tbl_infos:
                return SchemaInfo(
                    dialect=dialect,
                    database_name="(In-Memory Cache)",
                    tables=tbl_infos,
                    foreign_keys=all_fks,
                )
    except Exception as exc:
        logger.warning("Suppressed non-fatal error in schema.py: %s", exc, exc_info=True)
    return None


@router.get("/{dialect}", response_model=SchemaInfo)
async def retrieveDatabaseSchemaMetadataForVisualizer(dialect: str = "mysql", user_id: Optional[str] = Query(None)):
    """
    Returns database schema graph for the ER Diagram visualizer.

    Priority:
      1. Live connected DB schema (if user_id provided and DB attached)
      2. Orchestrator cached schema
      3. Mock fallback schema
    """
    # 1. If user_id is provided, check live DB connection
    if user_id:
        try:
            from core.connectors import default_registry
            if default_registry.is_attached(user_id):
                conn = default_registry.get(user_id)
                if conn and conn.is_connected:
                    live_schema = _build_schema_from_connection(conn, dialect)
                    if live_schema is not None:
                        return live_schema
            else:
                # User is explicitly not connected to any database — show 0 tables, no phantom schema
                return SchemaInfo(
                    dialect=dialect,
                    database_name="(No Database Connected)",
                    tables=[],
                    foreign_keys=[],
                    total_tables=0,
                    total_columns=0,
                )
        except Exception as exc:
            logger.warning("Suppressed non-fatal error in schema.py: %s", exc, exc_info=True)

        # If user is provided but not attached or introspection returned nothing, return empty
        return SchemaInfo(
            dialect=dialect,
            database_name="(No Database Connected)",
            tables=[],
            foreign_keys=[],
            total_tables=0,
            total_columns=0,
        )

    # 2. Try orchestrator-based schema (for headless / non-user API calls)
    orch_schema = _build_schema_from_orchestrator(dialect)
    if orch_schema:
        return orch_schema

    # 3. Fallback to mock (only when user_id is None, e.g. standalone test)
    return get_mock_ecommerce_schema(dialect)


get_schema = retrieveDatabaseSchemaMetadataForVisualizer
