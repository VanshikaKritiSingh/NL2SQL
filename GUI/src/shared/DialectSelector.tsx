// src/shared/DialectSelector.tsx
import React from 'react';
import { Database, Zap } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import type { TargetDialect } from '../types/query';

interface DialectCategory {
  category: string;
  options: { id: TargetDialect; label: string; badge?: string }[];
}

const DIALECT_CATEGORIES: DialectCategory[] = [
  {
    category: 'Speculative Auto Mode',
    options: [
      { id: 'auto', label: 'Auto-Detect (CLEF / DSpark Speculative)', badge: 'Recommended' },
    ],
  },
  {
    category: 'Relational / SQL (RDBMS)',
    options: [
      { id: 'postgres', label: 'PostgreSQL (Universal IR)' },
      { id: 'mysql', label: 'MySQL' },
      { id: 'sqlite', label: 'SQLite' },
      { id: 'oracle', label: 'Oracle Database' },
      { id: 'sqlserver', label: 'Microsoft SQL Server' },
      { id: 'mariadb', label: 'MariaDB' },
      { id: 'access', label: 'MS Access' },
    ],
  },
  {
    category: 'Analytical & Data Warehouse (OLAP)',
    options: [
      { id: 'duckdb', label: 'DuckDB (In-Memory OLAP)' },
      { id: 'snowflake', label: 'Snowflake' },
      { id: 'bigquery', label: 'Google BigQuery' },
      { id: 'clickhouse', label: 'ClickHouse' },
    ],
  },
  {
    category: 'Document / NoSQL',
    options: [
      { id: 'mongodb', label: 'MongoDB (MQL Aggregation Pipeline)' },
      { id: 'couchbase', label: 'Couchbase' },
    ],
  },
  {
    category: 'Graph & Network',
    options: [
      { id: 'opencypher', label: 'openCypher (Neo4j / Neptune / Memgraph)' },
    ],
  },
  {
    category: 'Time-Series & Metrics',
    options: [
      { id: 'timescaledb', label: 'TimescaleDB' },
      { id: 'influxql', label: 'InfluxQL (InfluxDB)' },
    ],
  },
];

export const DialectSelector: React.FC = () => {
  const targetDialect = useAppStore((s) => s.targetDialect);
  const setTargetDialect = useAppStore((s) => s.setTargetDialect);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const isAuto = targetDialect === 'auto';

  return (
    <div
      className={`flex items-center gap-1.5 border rounded-[var(--radius-pill)] px-2.5 py-1.5 text-xs transition-colors duration-200 shrink-0 whitespace-nowrap ${
        isAuto
          ? isDark
            ? 'bg-[var(--accent-primary)]/15 border-[var(--accent-primary)]/40 text-[var(--accent-primary)] font-semibold'
            : 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] border-[var(--btn-primary-bg)] font-semibold'
          : isDark
          ? 'bg-[var(--bg-card)] border-[var(--border-hairline)] text-[var(--text-main)]'
          : 'bg-[var(--bg-card)] border-[var(--border-hairline)] text-[var(--text-main)]'
      }`}
    >
      {isAuto ? (
        <Zap className={`w-3.5 h-3.5 shrink-0 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--btn-primary-text)]'}`} aria-hidden="true" />
      ) : (
        <Database className="w-3.5 h-3.5 shrink-0 text-[var(--accent-primary)]" aria-hidden="true" />
      )}
      <label htmlFor="dialect-select" className={`font-medium shrink-0 whitespace-nowrap ${isAuto && !isDark ? 'text-[var(--btn-primary-text)]/80' : 'text-[var(--text-recessive)]'}`}>
        DBMS Target:
      </label>
      <select
        id="dialect-select"
        value={targetDialect}
        onChange={(e) => setTargetDialect(e.target.value as TargetDialect)}
        className={`bg-transparent font-medium focus:outline-none cursor-pointer pr-1 max-w-[190px] truncate shrink-0 ${
          isAuto && !isDark ? 'text-[var(--btn-primary-text)]' : 'text-[var(--text-main)]'
        }`}
      >
        {DIALECT_CATEGORIES.map((cat) => (
          <optgroup
            key={cat.category}
            label={cat.category}
            className={isDark ? 'bg-[var(--bg-panel)] text-[var(--text-primary)] font-semibold' : 'bg-white text-[var(--text-primary)] font-semibold'}
          >
            {cat.options.map((opt) => (
              <option
                key={opt.id}
                value={opt.id}
                className={isDark ? 'bg-[var(--bg-card)] text-[var(--text-primary)] font-normal' : 'bg-white text-[var(--text-primary)] font-normal'}
              >
                {opt.label}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
};
