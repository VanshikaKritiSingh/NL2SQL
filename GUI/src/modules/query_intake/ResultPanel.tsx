// src/modules/query_intake/ResultPanel.tsx
import React, { useState, useEffect } from 'react';
import { Table, AlertTriangle, ShieldAlert, Zap, Server, Database, CheckCircle } from 'lucide-react';
import { useQueryStore } from '../../store/useQueryStore';
import { useAppStore } from '../../store/useAppStore';
import { EmptyState } from '../../shared/EmptyState';
import { ApprovalModal } from '../../shared/ApprovalModal';
import { ERDiagramModal } from '../../shared/ERDiagramModal';
import { getSchema } from '../../api/schemaApi';
import type { SchemaInfo } from '../../types/schema';

export const ResultPanel: React.FC = () => {
  const lastResponse = useQueryStore((s) => s.lastResponse);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isERDiagramOpen, setIsERDiagramOpen] = useState(false);
  const [schema, setSchema] = useState<SchemaInfo | null>(null);

  useEffect(() => {
    getSchema(targetDialect).then(setSchema).catch(() => {});
  }, [targetDialect]);

  if (!lastResponse) {
    return (
      <div
        className="flex flex-col h-full overflow-hidden shadow-lg transition-all duration-300 bento-card rounded-none"
      >
        <EmptyState
          icon={<Table className={`w-6 h-6 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`} />}
          title="Sandbox Execution Results"
          description="Read-only query outputs or execution statuses will display here."
        />
      </div>
    );
  }

  // Error State
  if (lastResponse.status === 'error') {
    return (
      <div
        className="flex flex-col h-full overflow-hidden shadow-lg p-6 justify-center items-center text-center transition-all duration-300 bento-card rounded-none"
      >
        <div className="w-12 h-12 rounded-none bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-500 mb-3">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-rose-500 mb-1">Execution Blocked</h3>
        <p className={`text-xs max-w-md font-mono p-3 rounded-none border ${
          isDark
            ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
            : 'text-rose-600 bg-rose-50 border-rose-200'
        }`}>
          {lastResponse.error_message || 'Pipeline validator or safety gate rejected this query.'}
        </p>
      </div>
    );
  }

  // Approval Required Gate Triggered
  if (lastResponse.status === 'approval_required') {
    const payload = lastResponse.approval_payload;
    const riskTier = payload?.risk_tier || 'high';
    const isDDL = payload?.generated_sql?.toUpperCase().includes('CREATE') || payload?.generated_sql?.toUpperCase().includes('ALTER') || payload?.generated_sql?.toUpperCase().includes('DROP');

    return (
      <div
        className="flex flex-col h-full overflow-hidden shadow-lg p-6 justify-center items-center text-center transition-all duration-300 bento-card rounded-none"
      >
        <div className={`w-12 h-12 rounded-none flex items-center justify-center mb-3 ${
          isDark
            ? 'bg-amber-500/10 border border-amber-500/30 text-amber-400'
            : 'bg-amber-50 border border-amber-200 text-amber-600'
        }`}>
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className={`text-base font-semibold mb-1 ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
          Mutating Statement · Approval Required
        </h3>
        <div className="flex items-center gap-2 mb-3">
          <span className={`text-[11px] px-2.5 py-0.5 rounded-none font-mono font-semibold uppercase ${
            isDark
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
              : 'bg-amber-50 text-amber-700 border border-amber-200'
          }`}>
            Risk: {riskTier}
          </span>
          <span className={`text-[11px] px-2.5 py-0.5 rounded-none font-mono ${
            isDark
              ? 'bg-[var(--bg-card-header)] border border-[var(--border-main)] text-[var(--text-muted)]'
              : 'bg-[var(--bg-card-header)] border border-[var(--border-subtle)] text-[var(--text-muted)]'
          }`}>
            Target: {lastResponse.database_profile || 'Connected DBMS'}
          </span>
        </div>
        <p className="text-xs max-w-md mb-5 leading-relaxed text-[var(--text-muted)]">
          The safety router intercepted this database modification. Review schema blast radius, data diffs, and execution cost before confirming changes to the database.
        </p>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsApprovalOpen(true)}
            className={`flex items-center gap-1.5 px-4 py-2.5 rounded-none text-xs font-semibold shadow-lg transition-all cursor-pointer ${
              isDark
                ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/25'
                : 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/20'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Make Changes to Database</span>
          </button>

          <button
            onClick={() => setIsERDiagramOpen(true)}
            className={`flex items-center gap-1.5 px-3.5 py-2.5 rounded-none text-xs font-semibold transition-all cursor-pointer ${
              isDark
                ? 'bg-[var(--bg-card-header)] border border-[var(--border-main)] text-[var(--text-main)] hover:bg-[var(--bg-hover)]'
                : 'bg-white border border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-hover)]'
            }`}
          >
            <Database className={`w-3.5 h-3.5 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`} />
            <span>{isDDL ? 'View Updated ER Diagram' : 'View ER Diagram'}</span>
          </button>
        </div>

        {/* Real Approval Gate Popup Modal */}
        <ApprovalModal
          isOpen={isApprovalOpen}
          onClose={() => setIsApprovalOpen(false)}
          payload={payload}
          onViewERDiagram={() => {
            setIsApprovalOpen(false);
            setIsERDiagramOpen(true);
          }}
        />

        {/* On-Demand ER Diagram Popup Modal */}
        <ERDiagramModal
          isOpen={isERDiagramOpen}
          onClose={() => setIsERDiagramOpen(false)}
          schema={schema}
          impactedTables={payload?.impacted_tables || []}
          title={isDDL ? 'Schema Impact: Table Structure' : 'Database ER Schema Graph'}
        />
      </div>
    );
  }

  // Completed SELECT Table Result
  const resultData = lastResponse.result_data;

  return (
    <div
      className="flex flex-col h-full overflow-hidden shadow-lg transition-all duration-300 bento-card rounded-none"
    >
      {/* Header */}
      <div
        className={`min-h-10 h-auto py-1.5 px-3 border-b flex flex-wrap gap-2 items-center justify-between shrink-0 transition-colors rounded-none ${
          isDark
            ? 'border-[var(--border-main)] bg-[var(--bg-card-header)]'
            : 'border-[var(--border-subtle)] bg-[var(--bg-card-header)]'
        }`}
      >
        <div className="flex flex-wrap items-center gap-2 shrink-0 min-w-0">
          <Server className="w-4 h-4 text-[var(--success)] shrink-0" />
          <span className="text-xs font-semibold text-[var(--text-main)] whitespace-nowrap">
            Execution Output
          </span>
          {lastResponse.cache_hit && (
            <span className={`flex items-center gap-1 text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-none whitespace-nowrap shrink-0 ${
              isDark
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
            }`}>
              <Zap className="w-3 h-3" /> Cache Hit
            </span>
          )}
          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-none whitespace-nowrap shrink-0 ${
            isDark
              ? 'bg-[var(--bg-card-header)] border border-[var(--border-main)] text-[var(--text-muted)]'
              : 'bg-[var(--bg-card-header)] border border-[var(--border-subtle)] text-[var(--text-muted)]'
          }`}>
            {lastResponse.execution_mode === 'live_database' ? 'Live DB Socket' : 'Preview / Dry-Run'}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0 whitespace-nowrap">
          <button
            onClick={() => setIsERDiagramOpen(true)}
            className={`flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-none transition-colors cursor-pointer shrink-0 whitespace-nowrap ${
              isDark
                ? 'bg-[var(--bg-card)] border border-[var(--border-main)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)]'
                : 'bg-white border border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)]'
            }`}
            title="Inspect Schema ER Diagram"
          >
            <Database className={`w-3 h-3 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`} />
            <span>Schema ER</span>
          </button>
          <span className="text-xs font-mono text-[var(--text-muted)] whitespace-nowrap shrink-0">
            {resultData?.row_count || 0} rows
          </span>
        </div>
      </div>

      {/* Table Data */}
      <div className={`flex-1 min-h-0 w-full overflow-x-auto overflow-y-auto rounded-none ${isDark ? 'bg-[var(--bg-card)]' : 'bg-[var(--bg-card)]'}`}>
        {resultData && resultData.rows.length > 0 ? (
          <table className="min-w-full text-left text-xs border-collapse font-mono">
            <thead
              className={`sticky top-0 border-b text-[11px] ${
                isDark
                  ? 'bg-[var(--bg-card-header)] border-[var(--border-main)] text-[var(--text-secondary)]'
                  : 'bg-[var(--bg-card-header)] border-[var(--border-subtle)] text-[var(--text-secondary)]'
              }`}
            >
              <tr>
                {resultData.columns.map((col) => (
                  <th key={col} className="px-3 py-2 font-bold whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className={`divide-y text-[var(--text-main)] ${
              isDark ? 'divide-[var(--border-main)]' : 'divide-[var(--border-subtle)]'
            }`}>
              {resultData.rows.map((row, idx) => (
                <tr
                  key={idx}
                  className={`transition-colors ${isDark ? 'hover:bg-[var(--bg-hover)]' : 'hover:bg-[#EDF0F7]'}`}
                >
                  {resultData.columns.map((col) => (
                    <td key={col} className="px-3 py-2 whitespace-nowrap">
                      {row[col] !== undefined && row[col] !== null ? String(row[col]) : 'NULL'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-[var(--text-muted)]">
            Query produced empty result set or completed with 0 rows.
          </div>
        )}
      </div>

      {/* On-Demand ER Diagram Popup Modal */}
      <ERDiagramModal
        isOpen={isERDiagramOpen}
        onClose={() => setIsERDiagramOpen(false)}
        schema={schema}
        title="Database ER Schema Graph"
      />
    </div>
  );
};
