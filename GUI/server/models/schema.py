# models/schema.py
from pydantic import BaseModel, Field
from typing import List, Optional


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    fk_references: Optional[str] = None   # "table.column"
    nullable: bool = True


class TableInfo(BaseModel):
    name: str
    columns: List[ColumnInfo]


class ForeignKey(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class SchemaInfo(BaseModel):
    dialect: str
    database_name: str
    tables: List[TableInfo]
    foreign_keys: List[ForeignKey]
