// src/modules/query_intake/ResultPanel.tsx
import React, { useState, useEffect } from 'react';
import { Table, AlertTriangle, ShieldAlert, Zap, Server, Database, CheckCircle, ExternalLink, GitBranch } from 'lucide-react';
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
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isERDiagramOpen, setIsERDiagramOpen] = useState(false);
  const [schema, setSchema] = useState<SchemaInfo | null>(null);

  useEffect(() => {
    getSchema(targetDialect).then(setSchema).catch(() => {});
  }, [targetDialect]);

  if (!lastResponse) {
    return (
      <div
        className="flex flex-col h-full border rounded-xl overflow-hidden shadow-lg transition-colors bg-[var(--bg-card)] border-[var(--border-main)]"
      >
        <EmptyState
          icon={<Table className="w-6 h-6 text-[var(--accent-primary)]" />}
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
        className="flex flex-col h-full border rounded-xl overflow-hidden shadow-lg p-6 justify-center items-center text-center transition-colors bg-[var(--bg-card)] border-[var(--border-main)]"
      >
        <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-500 mb-3">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-rose-500 mb-1">Execution Blocked</h3>
        <p className="text-xs text-rose-400 max-w-md font-mono bg-rose-500/10 p-3 rounded-lg border border-rose-500/20">
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
        className="flex flex-col h-full border rounded-xl overflow-hidden shadow-lg p-6 justify-center items-center text-center transition-colors bg-[var(--bg-card)] border-[var(--border-main)]"
      >
        <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-500 mb-3">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-amber-500 mb-1">
          Mutating Statement · Approval Required
        </h3>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[11px] px-2 py-0.5 rounded font-mono font-semibold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30">
            Risk: {riskTier}
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded font-mono bg-[var(--bg-card-header)] border border-[var(--border-subtle)] text-[var(--text-muted)]">
            Target: {lastResponse.database_profile || 'Connected DBMS'}
          </span>
        </div>
        <p className="text-xs max-w-md mb-5 leading-relaxed text-[var(--text-muted)]">
          The safety router intercepted this database modification. Review schema blast radius, data diffs, and execution cost before confirming changes to the database.
        </p>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsApprovalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-rose-600/25 transition-all cursor-pointer"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Make Changes to Database</span>
          </button>

          <button
            onClick={() => setIsERDiagramOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 border rounded-lg text-xs font-semibold transition-all cursor-pointer bg-[var(--bg-card-header)] border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-hover)]"
          >
            <Database className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
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
      className="flex flex-col h-full border rounded-xl overflow-hidden shadow-lg transition-colors bg-[var(--bg-card)] border-[var(--border-main)]"
    >
      {/* Header */}
      <div
        className="h-10 px-3 border-b flex items-center justify-between shrink-0 transition-colors border-[var(--border-subtle)] bg-[var(--bg-card-header)]"
      >
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-[var(--success)]" />
          <span className="text-xs font-semibold text-[var(--text-main)]">
            Execution Output
          </span>
          {lastResponse.cache_hit && (
            <span className="flex items-center gap-1 text-[10px] font-semibold uppercase bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 px-1.5 py-0.5 rounded">
              <Zap className="w-3 h-3" /> Cache Hit
            </span>
          )}
          <span className="text-[10px] font-mono bg-[var(--bg-card-header)] px-1.5 py-0.5 rounded border border-[var(--border-subtle)] text-[var(--text-muted)]">
            {lastResponse.execution_mode === 'live_database' ? 'Live DB Socket' : 'Preview / Dry-Run'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsERDiagramOpen(true)}
            className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded border transition-colors cursor-pointer bg-[var(--bg-card)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)]"
            title="Inspect Schema ER Diagram"
          >
            <Database className="w-3 h-3 text-[var(--accent-primary)]" />
            <span>Schema ER</span>
          </button>
          <span className="text-xs font-mono text-[var(--text-muted)]">
            {resultData?.row_count || 0} rows
          </span>
        </div>
      </div>

      {/* Table Data */}
      <div className="flex-1 overflow-auto">
        {resultData && resultData.rows.length > 0 ? (
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead
              className="sticky top-0 border-b text-[11px] bg-[var(--bg-card-header)] border-[var(--border-subtle)] text-[var(--text-secondary)]"
            >
              <tr>
                {resultData.columns.map((col) => (
                  <th key={col} className="px-3 py-2 font-semibold">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)] text-[var(--text-main)]">
              {resultData.rows.map((row, idx) => (
                <tr
                  key={idx}
                  className="transition-colors hover:bg-[var(--bg-hover)]"
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
