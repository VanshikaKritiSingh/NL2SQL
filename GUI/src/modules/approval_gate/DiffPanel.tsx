// src/modules/m14/DiffPanel.tsx
import React from 'react';
import { DiffEditor } from '@monaco-editor/react';
import { GitCompare, Table2, ArrowRight } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import type { DiffData } from '../../types/approval';

interface DiffPanelProps {
  diffData: DiffData;
}

export const DiffPanel: React.FC<DiffPanelProps> = ({ diffData }) => {
  const { diff_type, ddl_before, ddl_after, dml_rows } = diffData;
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  if (diff_type === 'none') {
    return (
      <div
        className="bento-card p-4 text-center text-xs text-[var(--text-muted)] rounded-none"
        style={{
          backgroundColor: isDark ? 'var(--bg-card)' : 'var(--bg-card)',
          border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid var(--border-subtle)',
        }}
      >
        No schema or row-level diff data for this query type.
      </div>
    );
  }

  return (
    <div
      className="bento-card overflow-hidden shadow-lg flex flex-col h-64 transition-all duration-300 rounded-none"
      style={{
        backgroundColor: isDark ? 'var(--bg-card)' : 'var(--bg-card)',
        border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid var(--border-subtle)',
      }}
    >
      {/* Header */}
      <div
        className={`h-9 px-3 border-b flex items-center justify-between shrink-0 transition-colors rounded-none ${
          isDark
            ? 'border-[var(--border-main)] bg-[var(--bg-card-header)]'
            : 'border-[var(--border-subtle)] bg-[var(--bg-card-header)]'
        }`}
      >
        <div className="flex items-center gap-2">
          {diff_type === 'ddl' ? (
            <GitCompare className={`w-4 h-4 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[#111111]'}`} />
          ) : (
            <Table2 className="w-4 h-4 text-emerald-500" />
          )}
          <span className="text-xs font-semibold text-[var(--text-main)]">
            {diff_type === 'ddl' ? 'Schema Migration Diff (Dolt Checkpoint)' : 'Data Row Diff Preview (DML)'}
          </span>
        </div>
        <span
          className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-none ${
            isDark
              ? 'bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border-main)]'
              : 'bg-white text-[var(--text-muted)] border border-[var(--border-subtle)]'
          }`}
        >
          {diff_type.toUpperCase()} Mode
        </span>
      </div>

      {/* DDL Diff Editor Mode */}
      {diff_type === 'ddl' && (
        <div className="flex-1 relative">
          <DiffEditor
            height="100%"
            language="sql"
            theme={isDark ? 'vs-dark' : 'light'}
            original={ddl_before || ''}
            modified={ddl_after || ''}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 11.5,
              fontFamily: "'JetBrains Mono', monospace",
              lineNumbers: 'on',
              renderSideBySide: true,
              scrollBeyondLastLine: false,
              wordWrap: 'on',
            }}
          />
        </div>
      )}

      {/* DML Tabular Row Diff Mode */}
      {diff_type === 'dml' && dml_rows && (
        <div className="flex-1 overflow-auto p-2">
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead
              className={`sticky top-0 border-b text-[11px] ${
                isDark
                  ? 'bg-[var(--bg-card-header)] border-[var(--border-main)] text-[var(--text-secondary)]'
                  : 'bg-[var(--bg-card-header)] border-[var(--border-subtle)] text-[var(--text-secondary)]'
              }`}
            >
              <tr>
                <th className="px-2 py-1.5 font-bold">Row ID</th>
                <th className="px-2 py-1.5 font-bold">Operation</th>
                <th className="px-2 py-1.5 font-bold">Field</th>
                <th className="px-2 py-1.5 font-bold">Before Value</th>
                <th className="px-2 py-1.5"></th>
                <th className="px-2 py-1.5 font-bold">After Value</th>
              </tr>
            </thead>
            <tbody className={`divide-y text-[var(--text-main)] ${
              isDark ? 'divide-[var(--border-main)]' : 'divide-[var(--border-subtle)]'
            }`}>
              {dml_rows.map((row) => {
                const cols = Object.keys(row.columns);
                return cols.map((colName, idx) => (
                  <tr
                    key={`${row.row_id}-${colName}`}
                    className={`transition-colors ${
                      isDark ? 'hover:bg-[var(--bg-hover)]' : 'hover:bg-[#EDF0F7]'
                    }`}
                  >
                    {idx === 0 && (
                      <>
                        <td rowSpan={cols.length} className="px-2 py-1.5 align-top font-bold text-[var(--text-muted)]">
                          #{String(row.row_id)}
                        </td>
                        <td rowSpan={cols.length} className="px-2 py-1.5 align-top">
                          <span className={`text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded-none ${
                            isDark
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}>
                            {row.change_type}
                          </span>
                        </td>
                      </>
                    )}
                    <td className="px-2 py-1.5 font-semibold text-[var(--text-secondary)]">
                      {colName}
                    </td>
                    <td className="px-2 py-1.5 text-rose-500 line-through">
                      {String(row.columns[colName].before)}
                    </td>
                    <td className="px-1 py-1.5 text-[var(--text-muted)] text-center">
                      <ArrowRight className="w-3 h-3 inline" />
                    </td>
                    <td className="px-2 py-1.5 text-emerald-500 font-bold">
                      {String(row.columns[colName].after)}
                    </td>
                  </tr>
                ));
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
