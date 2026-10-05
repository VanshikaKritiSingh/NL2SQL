// src/modules/m14/TableNode.tsx
import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Key, Link } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import type { TableInfo } from '../../types/schema';

interface TableNodeProps {
  data: {
    table: TableInfo;
    impactLevel: 'direct' | 'referenced' | 'none';
    operation?: string | null;
  };
}

export const TableNode = memo(({ data }: TableNodeProps) => {
  const { table, impactLevel, operation } = data;
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  // Highlight styling per spec: Red = Direct Write Target, Yellow = Referenced/FK
  const borderClass = {
    direct: 'border-2 border-rose-500 ring-4 ring-rose-500/20 shadow-xl',
    referenced: 'border-2 border-amber-400 ring-2 ring-amber-400/20 shadow-lg',
    none: isDark ? 'border border-slate-700/80 shadow-md' : 'border border-slate-300 shadow-md',
  }[impactLevel];

  const headerBg = {
    direct: 'bg-rose-950/80 border-b border-rose-800 text-rose-200',
    referenced: 'bg-amber-950/80 border-b border-amber-800 text-amber-200',
    none: isDark
      ? 'bg-slate-800/90 border-b border-slate-700 text-slate-200'
      : 'bg-slate-100 border-b border-slate-200 text-slate-800',
  }[impactLevel];

  return (
    <div
      className={`w-64 rounded-xl overflow-hidden text-xs font-mono transition-all ${
        isDark ? 'bg-slate-900' : 'bg-white'
      } ${borderClass}`}
    >
      {/* Handles for FK Edges */}
      <Handle type="target" position={Position.Left} className="w-2 h-2 bg-indigo-500 border border-slate-700" />
      <Handle type="source" position={Position.Right} className="w-2 h-2 bg-indigo-500 border border-slate-700" />

      {/* Table Header */}
      <div className={`px-3 py-2 flex items-center justify-between font-semibold ${headerBg}`}>
        <div className="flex items-center gap-1.5 truncate">
          <span className="truncate">{table.name}</span>
        </div>
        {operation && (
          <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-rose-500 text-white shadow-xs">
            {operation}
          </span>
        )}
      </div>

      {/* Columns List */}
      <div className={`divide-y p-1 ${isDark ? 'divide-slate-800/60' : 'divide-slate-100'}`}>
        {table.columns.map((col) => (
          <div
            key={col.name}
            className={`px-2 py-1.5 flex items-center justify-between text-[11px] rounded transition-colors ${
              isDark ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center gap-1.5 truncate">
              {col.is_primary_key ? (
                <span title="Primary Key">
                  <Key className="w-3 h-3 text-amber-500 shrink-0" />
                </span>
              ) : col.is_foreign_key ? (
                <span title={`Foreign Key -> ${col.fk_references || ''}`}>
                  <Link className="w-3 h-3 text-indigo-500 shrink-0" />
                </span>
              ) : (
                <span className="w-3" />
              )}
              <span
                className={`truncate ${
                  col.is_primary_key
                    ? isDark
                      ? 'font-bold text-amber-200'
                      : 'font-bold text-amber-700'
                    : isDark
                    ? 'text-slate-300'
                    : 'text-slate-700'
                }`}
              >
                {col.name}
              </span>
            </div>
            <span className="text-[10px] text-slate-400 shrink-0 ml-2">{col.data_type}</span>
          </div>
        ))}
      </div>
    </div>
  );
});
