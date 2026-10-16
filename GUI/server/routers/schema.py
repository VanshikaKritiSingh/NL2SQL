# routers/schema.py
from fastapi import APIRouter
from models.schema import SchemaInfo, TableInfo, ColumnInfo, ForeignKey
from mock_data.schemas import get_mock_ecommerce_schema

router = APIRouter(prefix="/schema", tags=["Schema Explorer"])


@router.get("/{dialect}", response_model=SchemaInfo)
async def get_schema(dialect: str = "mysql"):
    """Returns database schema graph for the ER Diagram visualizer dynamically synced from orchestrator."""
    try:
        from routers.query import orchestrator
        if orchestrator and orchestrator.tables:
            tbl_infos = []
            all_fks = []
            for t_name, t_meta in orchestrator.tables.items():
                col_infos = []
                for c_name, c_meta in t_meta.columns.items():
                    ref_str = f"{c_meta.fk_target_table}.{c_meta.fk_target_column}" if c_meta.is_fk and c_meta.fk_target_table else None
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

            return SchemaInfo(
                dialect=dialect,
                database_name="master_enterprise",
                tables=tbl_infos,
                foreign_keys=all_fks,
                total_tables=len(tbl_infos),
                total_columns=sum(len(t.columns) for t in tbl_infos),
            )
    except Exception:
        pass
    return get_mock_ecommerce_schema(dialect)
