// src/types/schema.ts
export interface ColumnInfo {
  name: string;
  data_type: string;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  fk_references: string | null;
  nullable: boolean;
}

export interface TableInfo {
  name: string;
  columns: ColumnInfo[];
}

export interface ForeignKey {
  from_table: string;
  from_column: string;
  to_table: string;
  to_column: string;
}

export interface SchemaInfo {
  dialect: string;
  database_name: string;
  tables: TableInfo[];
  foreign_keys: ForeignKey[];
}
