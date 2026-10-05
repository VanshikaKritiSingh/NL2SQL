// src/shared/DialectSelector.tsx
import React from 'react';
import { Database, Sparkles } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import type { TargetDialect } from '../types/query';

interface DialectCategory {
  category: string;
  options: { id: TargetDialect; label: string; badge?: string }[];
}

const DIALECT_CATEGORIES: DialectCategory[] = [
  {
    category: '⚡ Speculative Auto Mode',
    options: [
      { id: 'auto', label: '⚡ Auto-Detect (CLEF / DSpark Speculative)', badge: 'Recommended' },
    ],
  },
  {
    category: '🗄️ Relational / SQL (RDBMS)',
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
    category: '📊 Analytical & Data Warehouse (OLAP)',
    options: [
      { id: 'duckdb', label: 'DuckDB (In-Memory OLAP)' },
      { id: 'snowflake', label: 'Snowflake' },
      { id: 'bigquery', label: 'Google BigQuery' },
      { id: 'clickhouse', label: 'ClickHouse' },
    ],
  },
  {
    category: '🍃 Document / NoSQL',
    options: [
      { id: 'mongodb', label: 'MongoDB (MQL Aggregation Pipeline)' },
      { id: 'couchbase', label: 'Couchbase' },
    ],
  },
  {
    category: '🕸️ Graph & Network',
    options: [
      { id: 'opencypher', label: 'openCypher (Neo4j / Neptune / Memgraph)' },
    ],
  },
  {
    category: '⏱️ Time-Series & Metrics',
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
      className={`flex items-center gap-1.5 border rounded-lg px-2.5 py-1 text-xs transition-colors shadow-xs ${
        isAuto
          ? isDark
            ? 'bg-indigo-950/40 border-indigo-500/50 text-indigo-200'
            : 'bg-indigo-50 border-indigo-300 text-indigo-900'
          : isDark
          ? 'bg-slate-800/90 border-slate-700/80 text-slate-200'
          : 'bg-slate-100 border-slate-300 text-slate-800'
      }`}
    >
      {isAuto ? (
        <Sparkles className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
      ) : (
        <Database className="w-3.5 h-3.5 text-indigo-500" />
      )}
      <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
        DBMS Target:
      </span>
      <select
        value={targetDialect}
        onChange={(e) => setTargetDialect(e.target.value as TargetDialect)}
        className={`bg-transparent font-medium focus:outline-none cursor-pointer pr-1 max-w-[200px] truncate ${
          isDark ? 'text-slate-100' : 'text-slate-900'
        }`}
      >
        {DIALECT_CATEGORIES.map((cat) => (
          <optgroup
            key={cat.category}
            label={cat.category}
            className={isDark ? 'bg-slate-900 text-slate-400 font-semibold' : 'bg-slate-100 text-slate-600 font-semibold'}
          >
            {cat.options.map((opt) => (
              <option
                key={opt.id}
                value={opt.id}
                className={isDark ? 'bg-slate-950 text-slate-100 font-normal' : 'bg-white text-slate-800 font-normal'}
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
