// src/api/schemaApi.ts — Schema fetching with live DB support
import { apiFetch } from './client';
import type { SchemaInfo, TableInfo, ColumnInfo, ForeignKey } from '../types/schema';
import { getMockSchema } from '../mock/mockService';

/**
 * Fetches the live database schema from the connected DB socket for the given user.
 * The /api/connections/schema/{user_id} endpoint returns per-table column metadata
 * in a different shape than SchemaInfo, so we convert it here.
 *
 * Falls back to the orchestrator-based /api/schema/{dialect} endpoint,
 * and finally to the frontend mock.
 */
export async function getLiveSchema(userId: string, dialect: string = 'mysql'): Promise<SchemaInfo> {
  // 1. Try fetching live schema from connected DB
  try {
    const raw = await apiFetch<any>(`/connections/schema/${encodeURIComponent(userId)}?force_refresh=true`);
    if (raw && raw.tables && typeof raw.tables === 'object') {
      const converted = convertLiveSchemaToSchemaInfo(raw, dialect);
      if (converted.tables.length > 0) {
        return converted;
      }
    }
  } catch {
    // DB not connected or schema introspection failed — try next
  }

  // 2. Try orchestrator-based schema endpoint
  try {
    const schema = await apiFetch<SchemaInfo>(`/schema/${encodeURIComponent(dialect)}`);
    if (schema && schema.tables && schema.tables.length > 0) {
      return schema;
    }
  } catch {
    // server not available
  }

  // 3. Fallback to frontend mock
  return getMockSchema(dialect);
}

/**
 * Backward-compatible wrapper: fetches schema by dialect (used by older code paths).
 * When userId is available, prefers live schema.
 */
export async function getSchema(dialect: string = 'mysql', userId?: string): Promise<SchemaInfo> {
  if (userId) {
    return getLiveSchema(userId, dialect);
  }
  try {
    return await apiFetch<SchemaInfo>(`/schema/${encodeURIComponent(dialect)}`);
  } catch (error) {
    return getMockSchema(dialect);
  }
}

/**
 * Converts the raw shape from /api/connections/schema/{user_id} into
 * the SchemaInfo shape expected by the ER Diagram components.
 *
 * The raw shape from the connector introspection is:
 * {
 *   database_name: string,
 *   tables: { [tableName]: { columns: { [colName]: {...} }, primary_keys: [...], foreign_keys: [...], ... } },
 *   ...
 * }
 */
function convertLiveSchemaToSchemaInfo(raw: any, dialect: string): SchemaInfo {
  const tables: TableInfo[] = [];
  const foreignKeys: ForeignKey[] = [];
  const dbName = raw.database_name || raw.database || 'unknown';

  const rawTables = raw.tables || {};
  for (const [tableName, tableData] of Object.entries<any>(rawTables)) {
    const columns: ColumnInfo[] = [];
    const pks: string[] = tableData.primary_keys || [];
    const fks: any[] = tableData.foreign_keys || [];

    // Build a set of FK column names for quick lookup
    const fkColumnMap = new Map<string, { refTable: string; refColumn: string }>();
    for (const fk of fks) {
      // FK shape may vary: { column, references_table, references_column } or { from_column, to_table, to_column }
      const fromCol = fk.column || fk.from_column;
      const toTable = fk.references_table || fk.to_table || fk.ref_table;
      const toCol = fk.references_column || fk.to_column || fk.ref_column;
      if (fromCol && toTable && toCol) {
        fkColumnMap.set(fromCol, { refTable: toTable, refColumn: toCol });
        foreignKeys.push({
          from_table: tableName,
          from_column: fromCol,
          to_table: toTable,
          to_column: toCol,
        });
      }
    }

    const rawCols = tableData.columns || {};
    for (const [colName, colData] of Object.entries<any>(rawCols)) {
      const isPk = pks.includes(colName) || colData.is_primary_key || false;
      const fkRef = fkColumnMap.get(colName);
      const isFk = !!fkRef || colData.is_foreign_key || false;
      const fkReferences = fkRef
        ? `${fkRef.refTable}.${fkRef.refColumn}`
        : colData.foreign_key_target || colData.fk_references || null;

      columns.push({
        name: colName,
        data_type: colData.data_type || colData.type || 'VARCHAR',
        is_primary_key: isPk,
        is_foreign_key: isFk,
        fk_references: fkReferences,
        nullable: colData.nullable !== undefined ? colData.nullable : !isPk,
        sample_values: Array.isArray(colData.sample_values) ? colData.sample_values : undefined,
        default_value: colData.default_value !== undefined ? String(colData.default_value) : null,
      });
    }

    const rowCount =
      tableData.row_count_estimate !== undefined
        ? tableData.row_count_estimate
        : tableData.row_count !== undefined
        ? tableData.row_count
        : null;

    tables.push({ name: tableName, columns, row_count: rowCount });
  }

  return {
    dialect,
    database_name: dbName,
    tables,
    foreign_keys: foreignKeys,
  };
}
