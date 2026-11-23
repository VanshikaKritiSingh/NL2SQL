// src/utils/ddlParser.ts — Client-Side DDL AST Extractor
import type { TableInfo, ColumnInfo, ForeignKey } from '../types/schema';

export interface ParsedDDLResult {
  tables: TableInfo[];
  foreignKeys: ForeignKey[];
  tableNames: string[];
}

/**
 * Extracts newly declared table structures and foreign key relationships
 * directly from raw DDL SQL scripts (e.g. CREATE TABLE statements).
 */
export function parseTablesFromDDL(sql?: string | null): ParsedDDLResult {
  if (!sql || !sql.trim()) {
    return { tables: [], foreignKeys: [], tableNames: [] };
  }

  const tables: TableInfo[] = [];
  const foreignKeys: ForeignKey[] = [];
  const tableNames: string[] = [];

  // Match CREATE TABLE [IF NOT EXISTS] <name> (
  const createTableRegex = /CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"'\w]+)\s*\(/gi;
  let match: RegExpExecArray | null;

  while ((match = createTableRegex.exec(sql)) !== null) {
    const rawTableName = match[1].replace(/[`"']/g, '').trim();
    const startIndex = createTableRegex.lastIndex;

    // Balance parentheses to reliably capture the complete table definition body
    let depth = 1;
    let i = startIndex;
    while (i < sql.length && depth > 0) {
      if (sql[i] === '(') depth++;
      else if (sql[i] === ')') depth--;
      i++;
    }

    if (depth !== 0) continue;
    const body = sql.substring(startIndex, i - 1);
    tableNames.push(rawTableName);

    // Split column definitions by commas that are outside parentheses
    const lines = body.split(/,\s*(?![^(]*\))/);
    const columns: ColumnInfo[] = [];

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) continue;
      const upper = line.toUpperCase();

      // Check for inline table constraints: FOREIGN KEY (col) REFERENCES other (col)
      if (upper.startsWith('FOREIGN KEY') || (upper.startsWith('CONSTRAINT') && upper.includes('FOREIGN KEY'))) {
        const fkMatch = line.match(
          /FOREIGN\s+KEY\s*\(([`"\w\s,]+)\)\s*REFERENCES\s+([`"\w]+)\s*\(([`"\w\s,]+)\)/i
        );
        if (fkMatch) {
          const fromCol = fkMatch[1].replace(/[`"']/g, '').trim();
          const toTbl = fkMatch[2].replace(/[`"']/g, '').trim();
          const toCol = fkMatch[3].replace(/[`"']/g, '').trim();
          foreignKeys.push({
            from_table: rawTableName,
            from_column: fromCol,
            to_table: toTbl,
            to_column: toCol,
          });
        }
      } else if (upper.startsWith('PRIMARY KEY')) {
        const pkMatch = line.match(/PRIMARY\s+KEY\s*\(([`"\w\s,]+)\)/i);
        if (pkMatch) {
          const pkCols = pkMatch[1]
            .split(',')
            .map((c) => c.replace(/[`"']/g, '').trim().toLowerCase());
          columns.forEach((col) => {
            if (pkCols.includes(col.name.toLowerCase())) {
              col.is_primary_key = true;
            }
          });
        }
      } else {
        // Normal column declaration: col_name data_type [constraints]
        const colMatch = line.match(/^([`"'\w]+)\s+([A-Za-z0-9_]+(?:\s*\([^)]*\))?)/);
        if (colMatch) {
          const colName = colMatch[1].replace(/[`"']/g, '');
          const colType = colMatch[2].replace(/[,;]/g, '');
          const isPk = upper.includes('PRIMARY KEY');

          columns.push({
            name: colName,
            data_type: colType,
            is_primary_key: isPk,
            is_foreign_key: false,
            fk_references: null,
            nullable: !upper.includes('NOT NULL'),
            sample_values: [],
          });
        }
      }
    }

    // Correlate foreign key columns
    foreignKeys.forEach((fk) => {
      if (fk.from_table.toLowerCase() === rawTableName.toLowerCase()) {
        const col = columns.find((c) => c.name.toLowerCase() === fk.from_column.toLowerCase());
        if (col) {
          col.is_foreign_key = true;
          col.fk_references = `${fk.to_table}.${fk.to_column}`;
        }
      }
    });

    tables.push({
      name: rawTableName,
      columns,
      row_count: 0,
    });
  }

  return { tables, foreignKeys, tableNames };
}
