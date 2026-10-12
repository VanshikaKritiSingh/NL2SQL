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
        className={`border rounded-xl p-4 text-center text-xs ${
          'bg-[var(--bg-card)] border-[var(--border-main)] text-[var(--text-muted)]'
        }`}
      >
        No schema or row-level diff data for this query type.
      </div>
    );
  }

  return (
    <div
      className={`border rounded-xl overflow-hidden shadow-lg flex flex-col h-64 transition-colors ${
        'bg-[var(--bg-card)] border-[var(--border-main)]'
      }`}
    >
      {/* Header */}
      <div
        className={`h-9 px-3 border-b flex items-center justify-between shrink-0 transition-colors ${
          'border-[var(--border-subtle)] bg-[var(--bg-card-header)]'
        }`}
      >
        <div className="flex items-center gap-2">
          {diff_type === 'ddl' ? (
            <GitCompare className="w-4 h-4 text-indigo-500" />
          ) : (
            <Table2 className="w-4 h-4 text-emerald-500" />
          )}
          <span className={`text-xs font-semibold ${'text-[var(--text-main)]'}`}>
            {diff_type === 'ddl' ? 'Schema Migration Diff (Dolt Checkpoint)' : 'Data Row Diff Preview (DML)'}
          </span>
        </div>
        <span
          className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
            'bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border-subtle)]'
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
                'bg-[var(--bg-card-header)] border-[var(--border-subtle)] text-[var(--text-secondary)]'
              }`}
            >
              <tr>
                <th className="px-2 py-1.5">Row ID</th>
                <th className="px-2 py-1.5">Operation</th>
                <th className="px-2 py-1.5">Field</th>
                <th className="px-2 py-1.5">Before Value</th>
                <th className="px-2 py-1.5"></th>
                <th className="px-2 py-1.5">After Value</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${'divide-[var(--border-subtle)] text-[var(--text-main)]'}`}>
              {dml_rows.map((row) => {
                const cols = Object.keys(row.columns);
                return cols.map((colName, idx) => (
                  <tr
                    key={`${row.row_id}-${colName}`}
                    className={`transition-colors ${'hover:bg-[var(--bg-hover)]'}`}
                  >
                    {idx === 0 && (
                      <>
                        <td rowSpan={cols.length} className="px-2 py-1.5 align-top font-bold text-slate-400">
                          #{String(row.row_id)}
                        </td>
                        <td rowSpan={cols.length} className="px-2 py-1.5 align-top">
                          <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-500 border border-amber-500/30">
                            {row.change_type}
                          </span>
                        </td>
                      </>
                    )}
                    <td className={`px-2 py-1.5 font-semibold ${'text-[var(--text-muted)]'}`}>
                      {colName}
                    </td>
                    <td className="px-2 py-1.5 text-rose-500 line-through">
                      {String(row.columns[colName].before)}
                    </td>
                    <td className="px-1 py-1.5 text-slate-400 text-center">
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
