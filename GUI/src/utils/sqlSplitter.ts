// src/utils/sqlSplitter.ts — Command Block Splitter with Prompt-Mapped Reasons
import type { BackendCommandBlock } from '../types/query';

export interface SqlCommandBlock {
  id: string;
  index: number;
  rawText: string;
  commandText: string;
  commentText?: string;
  commandType: string;
  isMutating: boolean;
  reason: string;
}

/**
 * Categorizes a SQL statement string into a human-friendly command type label (DDL, DML, SELECT, TCL).
 */
export function classifySqlCommandType(sql: string): { type: string; isMutating: boolean } {
  const clean = sql.trim().replace(/^(--.*?\n|\/\*.*?\*\/)+/s, '').trim();
  const upper = clean.toUpperCase();

  if (upper.startsWith('SELECT') || upper.startsWith('WITH')) {
    return { type: 'SELECT', isMutating: false };
  }
  if (upper.startsWith('CREATE TABLE')) {
    return { type: 'DDL: CREATE TABLE', isMutating: true };
  }
  if (upper.startsWith('CREATE INDEX') || upper.startsWith('CREATE UNIQUE INDEX')) {
    return { type: 'DDL: CREATE INDEX', isMutating: true };
  }
  if (upper.startsWith('CREATE VIEW') || upper.startsWith('CREATE OR REPLACE VIEW')) {
    return { type: 'DDL: CREATE VIEW', isMutating: true };
  }
  if (upper.startsWith('CREATE') || upper.startsWith('CREATE DATABASE')) {
    return { type: 'DDL: CREATE', isMutating: true };
  }
  if (upper.startsWith('ALTER TABLE') || upper.startsWith('ALTER')) {
    return { type: 'DDL: ALTER TABLE', isMutating: true };
  }
  if (upper.startsWith('DROP TABLE') || upper.startsWith('DROP')) {
    return { type: 'DDL: DROP', isMutating: true };
  }
  if (upper.startsWith('TRUNCATE')) {
    return { type: 'DDL: TRUNCATE', isMutating: true };
  }
  if (upper.startsWith('INSERT INTO') || upper.startsWith('INSERT')) {
    return { type: 'DML: INSERT', isMutating: true };
  }
  if (upper.startsWith('UPDATE')) {
    return { type: 'DML: UPDATE', isMutating: true };
  }
  if (upper.startsWith('DELETE FROM') || upper.startsWith('DELETE')) {
    return { type: 'DML: DELETE', isMutating: true };
  }
  if (upper.startsWith('REPLACE INTO')) {
    return { type: 'DML: REPLACE', isMutating: true };
  }
  if (upper.startsWith('BEGIN') || upper.startsWith('START TRANSACTION')) {
    return { type: 'TCL: BEGIN', isMutating: false };
  }
  if (upper.startsWith('COMMIT')) {
    return { type: 'TCL: COMMIT', isMutating: true };
  }
  if (upper.startsWith('ROLLBACK')) {
    return { type: 'TCL: ROLLBACK', isMutating: false };
  }
  if (upper.startsWith('EXPLAIN') || upper.startsWith('DESCRIBE') || upper.startsWith('PRAGMA') || upper.startsWith('SHOW')) {
    return { type: 'METADATA', isMutating: false };
  }
  if (upper.startsWith('USE')) {
    return { type: 'CONTEXT: USE', isMutating: false };
  }

  return { type: 'COMMAND', isMutating: false };
}

/**
 * Generates a concise fallback reason mapping the command to user intent if LLM reason is omitted.
 */
export function getDefaultCommandReason(sql: string): string {
  const clean = sql.trim().toUpperCase();
  const mCreate = sql.match(/CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"'\w]+)/i);
  if (mCreate) return `Creates table ${mCreate[1]} with specified columns and constraints.`;
  const mAlterAuto = sql.match(/ALTER\s+TABLE\s+([`"'\w]+)\s+AUTO_INCREMENT\s*=\s*(\d+)/i);
  if (mAlterAuto) return `Sets the starting AUTO_INCREMENT counter for ${mAlterAuto[1]} to ${mAlterAuto[2]}.`;
  const mAlter = sql.match(/ALTER\s+TABLE\s+([`"'\w]+)/i);
  if (mAlter) return `Modifies the structure of table ${mAlter[1]}.`;
  const mUpdate = sql.match(/UPDATE\s+([`"'\w]+)/i);
  if (mUpdate) return `Updates targeted records in ${mUpdate[1]} based on criteria.`;
  const mDelete = sql.match(/DELETE\s+FROM\s+([`"'\w]+)/i);
  if (mDelete) return `Deletes targeted records from ${mDelete[1]}.`;
  const mInsert = sql.match(/INSERT\s+INTO\s+([`"'\w]+)/i);
  if (mInsert) return `Inserts new records into ${mInsert[1]}.`;
  const mSelect = sql.match(/FROM\s+([`"'\w]+)/i);
  if (mSelect) return `Queries and retrieves data projections from ${mSelect[1]}.`;
  return `Executes command to satisfy natural language request requirements.`;
}

/**
 * Splits a full SQL script or consumes backend-provided command blocks into sequential,
 * individual Jupyter-style cell blocks with prompt-mapped reasons.
 */
export function splitSqlIntoCommandBlocks(
  fullSql: string,
  backendBlocks?: BackendCommandBlock[]
): SqlCommandBlock[] {
  // If backend LLM returned structured command blocks with pre-generated reasons, use them directly
  if (backendBlocks && backendBlocks.length > 0) {
    return backendBlocks.map((b, idx) => {
      const classification = classifySqlCommandType(b.command);
      return {
        id: `cell-cmd-${idx + 1}`,
        index: idx + 1,
        rawText: b.command,
        commandText: b.command.trim(),
        commandType: b.type ? b.type.toUpperCase() : classification.type,
        isMutating: classification.isMutating,
        reason: b.reason || getDefaultCommandReason(b.command),
      };
    });
  }

  if (!fullSql || !fullSql.trim()) return [];

  const blocks: SqlCommandBlock[] = [];
  let current = '';
  let inSingleQuote = false;
  let inDoubleQuote = false;
  let inDollarQuote = false;
  let dollarTag = '';
  let inLineComment = false;
  let inBlockComment = false;

  const len = fullSql.length;
  let i = 0;

  while (i < len) {
    const char = fullSql[i];
    const next = i + 1 < len ? fullSql[i + 1] : '';

    if (inLineComment) {
      current += char;
      if (char === '\n') {
        inLineComment = false;
      }
      i++;
      continue;
    }

    if (inBlockComment) {
      current += char;
      if (char === '*' && next === '/') {
        current += next;
        inBlockComment = false;
        i += 2;
        continue;
      }
      i++;
      continue;
    }

    if (inSingleQuote) {
      current += char;
      if (char === "'") {
        if (next === "'") {
          current += next;
          i += 2;
          continue;
        }
        inSingleQuote = false;
      }
      i++;
      continue;
    }

    if (inDoubleQuote) {
      current += char;
      if (char === '"') {
        if (next === '"') {
          current += next;
          i += 2;
          continue;
        }
        inDoubleQuote = false;
      }
      i++;
      continue;
    }

    if (inDollarQuote) {
      current += char;
      if (char === '$') {
        const remaining = fullSql.slice(i);
        if (remaining.startsWith(dollarTag)) {
          current += dollarTag.slice(1);
          i += dollarTag.length;
          inDollarQuote = false;
          continue;
        }
      }
      i++;
      continue;
    }

    // Check for comment starts
    if (char === '-' && next === '-') {
      inLineComment = true;
      current += '--';
      i += 2;
      continue;
    }
    if (char === '/' && next === '*') {
      inBlockComment = true;
      current += '/*';
      i += 2;
      continue;
    }

    // Check for string quote starts
    if (char === "'") {
      inSingleQuote = true;
      current += char;
      i++;
      continue;
    }
    if (char === '"') {
      inDoubleQuote = true;
      current += char;
      i++;
      continue;
    }

    // Check for Postgres dollar quote tag
    if (char === '$') {
      const match = fullSql.slice(i).match(/^(\$[a-zA-Z0-9_]*\$)/);
      if (match) {
        dollarTag = match[1];
        inDollarQuote = true;
        current += dollarTag;
        i += dollarTag.length;
        continue;
      }
    }

    // Semicolon statement boundary
    if (char === ';') {
      current += ';';
      const trimmed = current.trim();
      if (trimmed.length > 0) {
        const classification = classifySqlCommandType(trimmed);
        blocks.push({
          id: `cell-cmd-${blocks.length + 1}`,
          index: blocks.length + 1,
          rawText: current,
          commandText: trimmed,
          commandType: classification.type,
          isMutating: classification.isMutating,
          reason: getDefaultCommandReason(trimmed),
        });
      }
      current = '';
      i++;
      continue;
    }

    current += char;
    i++;
  }

  // Trailing statement without semicolon
  const trailing = current.trim();
  if (trailing.length > 0) {
    const classification = classifySqlCommandType(trailing);
    blocks.push({
      id: `cell-cmd-${blocks.length + 1}`,
      index: blocks.length + 1,
      rawText: current,
      commandText: trailing,
      commandType: classification.type,
      isMutating: classification.isMutating,
      reason: getDefaultCommandReason(trailing),
    });
  }

  return blocks;
}
