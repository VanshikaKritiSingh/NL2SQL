// src/modules/query_intake/ResultPanel.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { Table, AlertTriangle, ShieldAlert, Zap, Server, Database, CheckCircle, RefreshCw } from 'lucide-react';
import { useQueryStore } from '../../store/useQueryStore';
import { useAppStore } from '../../store/useAppStore';
import { useSchemaStore } from '../../store/useSchemaStore';
import { EmptyState } from '../../shared/EmptyState';
import { ApprovalModal } from '../../shared/ApprovalModal';
import { ERDiagramModal } from '../../shared/ERDiagramModal';
import { getLiveSchema } from '../../api/schemaApi';
import type { SchemaInfo } from '../../types/schema';

export const ResultPanel: React.FC = () => {
  const lastResponse = useQueryStore((s) => s.lastResponse);
  const userId = useAppStore((s) => s.userId);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const isDbConnected = useAppStore((s) => s.isDbConnected);
  const connectedEngine = useAppStore((s) => s.connectedEngine);
  const setRightPanelTab = useAppStore((s) => s.setRightPanelTab);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isERDiagramOpen, setIsERDiagramOpen] = useState(false);

  // Centralized schema state
  const schema = useSchemaStore((s) => s.schema);
  const schemaVersion = useSchemaStore((s) => s.schemaVersion);
  const isFetchingSchema = useSchemaStore((s) => s.isFetching);
  const updateSchema = useSchemaStore((s) => s.updateSchema);
  const setFetching = useSchemaStore((s) => s.setFetching);
  const setFetchError = useSchemaStore((s) => s.setFetchError);
  const databaseProfile = useAppStore((s) => s.databaseProfile);

  // Fetch schema whenever dialect, userId, connection status, schemaVersion, or database profile changes
  const fetchSchema = useCallback(async () => {
    setFetching(true);
    setFetchError(null);
    try {
      const dialect = connectedEngine || (targetDialect === 'auto' ? 'mysql' : targetDialect);
      const fetched = await getLiveSchema(userId, dialect);
      updateSchema(fetched);
    } catch (err: any) {
      setFetchError(err.message || 'Failed to fetch schema');
    } finally {
      setFetching(false);
    }
  }, [userId, targetDialect, connectedEngine, databaseProfile, updateSchema, setFetching, setFetchError]);

  // Refetch schema on mount, when schemaVersion bumps, when connection status changes, or when active database changes
  useEffect(() => {
    fetchSchema();
  }, [fetchSchema, schemaVersion, isDbConnected, databaseProfile]);

  // Auto-bump schema version when a new response arrives (especially for mutating operations)
  useEffect(() => {
    if (lastResponse) {
      const status = lastResponse.status;
      // After a completed query or after approval, the DB may have changed
      if (status === 'completed' || status === 'approval_required') {
        // Small delay to let the DB settle after writes
        const timer = setTimeout(() => fetchSchema(), 300);
        return () => clearTimeout(timer);
      }
    }
  }, [lastResponse?.query_id]);

  if (!lastResponse) {
    return (
      <div
        className="flex flex-col h-full overflow-hidden shadow-lg transition-colors duration-200 bento-card rounded-[var(--radius-panel)]"
      >
        <EmptyState
          icon={<Table aria-hidden="true" className={`w-6 h-6 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`} />}
          title="Sandbox Execution Results"
          description="Read-only query outputs or execution statuses will display here."
        />
      </div>
    );
  }

  // Refusal State (Non-SQL query or Schema Mismatch Guard)
  if (lastResponse.status === 'refusal') {
    const isSchemaMismatch = lastResponse.generated_sql?.includes('SCHEMA_MISMATCH');
    return (
      <div
        className="flex flex-col h-full overflow-hidden shadow-lg p-6 justify-center items-center text-center transition-colors duration-200 bento-card rounded-[var(--radius-panel)]"
      >
        <div className={`w-12 h-12 rounded-[var(--radius-panel)] flex items-center justify-center mb-3 ${
          isSchemaMismatch
            ? 'bg-[var(--warning-bg)] border border-[var(--warning)]/30 text-[var(--warning)]'
            : 'bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/30 text-[var(--accent-primary)]'
        }`}>
          {isSchemaMismatch ? <Database aria-hidden="true" className="w-6 h-6" /> : <Server aria-hidden="true" className="w-6 h-6" />}
        </div>
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-[10px] font-mono px-2 py-0.5 rounded-[var(--radius-pill)] uppercase tracking-wider font-semibold border ${
            isSchemaMismatch
              ? 'bg-[var(--warning-bg)] border border-[var(--warning)]/30 text-[var(--warning)]'
              : 'bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/30 text-[var(--accent-primary)]'
          }`}>
            {isSchemaMismatch ? 'Schema Grounding Notice' : 'Non-Database Query Notice'}
          </span>
        </div>
        <h3 className={`text-base font-semibold mb-2 ${
          isSchemaMismatch ? 'text-[var(--warning)]' : 'text-[var(--accent-primary)]'
        }`}>
          {isSchemaMismatch ? 'Entity Not Found in Active Schema' : 'Conversational Input Detected'}
        </h3>
        <p className={`text-xs max-w-lg p-3 rounded-[var(--radius-control)] border text-left leading-relaxed mb-4 ${
          isDark
            ? isSchemaMismatch
              ? 'text-[var(--warning)]/90 bg-[var(--warning-bg)] border-[var(--warning)]/20'
              : 'text-[var(--text-main)] bg-[var(--accent-primary)]/10 border-[var(--accent-primary)]/20'
            : isSchemaMismatch
              ? 'text-[var(--warning)] bg-[var(--warning-bg)] border-[var(--warning)]/20'
              : 'text-[var(--text-body)] bg-[var(--accent-primary)]/5 border-[var(--accent-primary)]/20'
        }`}>
          {lastResponse.error_message}
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setRightPanelTab('er_diagram')}
            className={`px-3 py-1.5 text-xs font-medium border rounded-[var(--radius-pill)] flex items-center gap-1.5 transition-colors duration-200 cursor-pointer ${
              isDark
                ? 'bg-[var(--bg-panel)] border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-hover)]'
                : 'bg-white border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-hover)]'
            }`}
          >
            <Database aria-hidden="true" className="w-3.5 h-3.5" />
            Explore Connected Schema (ER Diagram)
          </button>
        </div>
        <ERDiagramModal
          isOpen={isERDiagramOpen}
          onClose={() => setIsERDiagramOpen(false)}
          schema={schema}
          impactedTables={[]}
        />
      </div>
    );
  }

  // Error State
  if (lastResponse.status === 'error') {
    return (
      <div
        className="flex flex-col h-full overflow-hidden shadow-lg p-6 justify-center items-center text-center transition-colors duration-200 bento-card rounded-[var(--radius-panel)]"
      >
        <div className="w-12 h-12 rounded-[var(--radius-panel)] bg-[var(--danger-bg)] border border-[var(--danger)]/30 flex items-center justify-center text-[var(--danger)] mb-3">
          <AlertTriangle aria-hidden="true" className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-[var(--danger)] mb-1">Execution Blocked</h3>
        <p className={`text-xs max-w-md font-mono p-3 rounded-[var(--radius-control)] border ${
          isDark
            ? 'text-[var(--danger)] bg-[var(--danger-bg)] border-[var(--danger)]/20'
            : 'text-[var(--danger)] bg-[var(--danger-bg)] border-[var(--danger)]/20'
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
        className="flex flex-col h-full overflow-hidden shadow-lg p-6 justify-center items-center text-center transition-colors duration-200 bento-card rounded-[var(--radius-panel)]"
      >
        <div className={`w-12 h-12 rounded-[var(--radius-panel)] flex items-center justify-center mb-3 ${
          isDark
            ? 'bg-[var(--warning-bg)] border border-[var(--warning)]/30 text-[var(--warning)]'
            : 'bg-[var(--warning-bg)] border border-[var(--warning)]/30 text-[var(--warning)]'
        }`}>
          <ShieldAlert aria-hidden="true" className="w-6 h-6" />
        </div>
        <h3 className={`text-base font-semibold mb-1 ${isDark ? 'text-[var(--warning)]' : 'text-[var(--warning)]'}`}>
          Mutating Statement · Approval Required
        </h3>
        <div className="flex items-center gap-2 mb-3">
          <span className={`text-[11px] px-2.5 py-0.5 rounded-[var(--radius-pill)] font-mono font-semibold uppercase ${
            isDark
              ? 'bg-[var(--warning-bg)] text-[var(--warning)] border border-[var(--warning)]/30'
              : 'bg-[var(--warning-bg)] text-[var(--warning)] border border-[var(--warning)]/20'
          }`}>
            Risk: {riskTier}
          </span>
          <span className={`text-[11px] px-2.5 py-0.5 rounded-[var(--radius-pill)] font-mono ${
            isDark
              ? 'bg-[var(--bg-card-header)] border border-[var(--border-main)] text-[var(--text-muted)]'
              : 'bg-[var(--bg-card-header)] border border-[var(--border-subtle)] text-[var(--text-muted)]'
          }`}>
            Target: {databaseProfile && databaseProfile !== '__none__' ? databaseProfile : (lastResponse.database_profile || 'Connected DBMS')}
          </span>
        </div>
        <p className="text-xs max-w-md mb-5 leading-relaxed text-[var(--text-muted)]">
          The safety router intercepted this database modification. Review schema blast radius, data diffs, and execution cost before confirming changes to the database.
        </p>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsApprovalOpen(true)}
            className={`flex items-center gap-1.5 px-4 py-2.5 rounded-[var(--radius-pill)] text-xs font-semibold shadow-lg transition-colors duration-200 cursor-pointer ${
              isDark
                ? 'bg-[var(--danger)] hover:opacity-90 text-white'
                : 'bg-[var(--danger)] hover:opacity-90 text-white'
            }`}
          >
            <ShieldAlert aria-hidden="true" className="w-3.5 h-3.5" />
            <span>Make Changes to Database</span>
          </button>

          <button
            onClick={() => setIsERDiagramOpen(true)}
            className={`flex items-center gap-1.5 px-3.5 py-2.5 rounded-[var(--radius-pill)] text-xs font-semibold transition-colors duration-200 cursor-pointer ${
              isDark
                ? 'bg-[var(--bg-card-header)] border border-[var(--border-main)] text-[var(--text-main)] hover:bg-[var(--bg-hover)]'
                : 'bg-white border border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-hover)]'
            }`}
          >
            <Database aria-hidden="true" className={`w-3.5 h-3.5 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`} />
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

        {/* On-Demand ER Diagram Popup Modal (Scoped to query's impacted/generated tables) */}
        <ERDiagramModal
          isOpen={isERDiagramOpen}
          onClose={() => setIsERDiagramOpen(false)}
          schema={schema}
          impactedTables={payload?.impacted_tables || []}
          generatedSql={payload?.generated_sql || lastResponse.generated_sql}
          defaultScope="query"
          title={isDDL ? 'Schema Impact: Generated Tables' : 'Query Impacted ER Schema'}
        />
      </div>
    );
  }

  // Completed SELECT Table Result
  const resultData = lastResponse.result_data;

  return (
    <div
      className="flex flex-col h-full overflow-hidden shadow-lg transition-colors duration-200 bento-card rounded-[var(--radius-panel)]"
    >
      {/* Header */}
      <div
        className={`min-h-10 h-auto py-1.5 px-3 border-b flex flex-wrap gap-2 items-center justify-between shrink-0 transition-colors duration-200 ${
          isDark
            ? 'border-[var(--border-hairline)] bg-[var(--bg-card-header)]'
            : 'border-[var(--border-hairline)] bg-[var(--bg-card-header)]'
        }`}
      >
        <div className="flex flex-wrap items-center gap-2 shrink-0 min-w-0">
          <Server aria-hidden="true" className="w-4 h-4 text-[var(--success)] shrink-0" />
          <span className="text-xs font-semibold text-[var(--text-heading)] whitespace-nowrap">
            Execution Output
          </span>
          {lastResponse.cache_hit && (
            <span className="flex items-center gap-1 text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-[var(--radius-pill)] whitespace-nowrap shrink-0 bg-[var(--success-bg)] text-[var(--success)] border border-[var(--success)]/30">
              <Zap aria-hidden="true" className="w-3 h-3" /> Cache Hit
            </span>
          )}
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-[var(--radius-pill)] whitespace-nowrap shrink-0 bg-[var(--bg-card-header)] border border-[var(--border-hairline)] text-[var(--text-muted)]">
            {lastResponse.execution_mode === 'live_database' ? 'Live DB Socket' : 'Preview / Dry-Run'}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0 whitespace-nowrap">
          <button
            onClick={() => fetchSchema()}
            disabled={isFetchingSchema}
            className="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-[var(--radius-pill)] transition-colors duration-200 cursor-pointer shrink-0 whitespace-nowrap bg-[var(--bg-card)] border border-[var(--border-hairline)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)]"
            title="Refresh schema from database"
          >
            <RefreshCw aria-hidden="true" className={`w-3 h-3 ${isFetchingSchema ? 'animate-spin' : ''} text-[var(--accent-primary)]`} />
            <span>Refresh</span>
          </button>
          <span className="text-xs font-mono text-[var(--text-muted)] whitespace-nowrap shrink-0 font-variant-numeric tabular-nums">
            {resultData?.row_count || 0} rows
          </span>
        </div>
      </div>

      {/* Table Data */}
      <div className="flex-1 min-h-0 w-full overflow-x-auto overflow-y-auto bg-[var(--bg-card)]">
        {resultData && resultData.rows.length > 0 ? (
          <table className="min-w-full text-left text-xs border-collapse font-mono">
            <thead
              className="sticky top-0 border-b text-[11px] bg-[var(--bg-card-header)] border-[var(--border-hairline)] text-[var(--text-secondary)]"
            >
              <tr>
                {resultData.columns.map((col) => (
                  <th key={col} className="px-3 py-2 font-bold whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-hairline)] text-[var(--text-main)]">
              {resultData.rows.map((row, idx) => (
                <tr
                  key={idx}
                  className="transition-colors duration-150 hover:bg-[var(--bg-hover)]"
                >
                  {resultData.columns.map((col) => {
                    const val = row[col];
                    const isNull = val === undefined || val === null;
                    const isNum = typeof val === 'number' || (!isNull && !isNaN(Number(val)) && typeof val !== 'boolean');
                    return (
                      <td key={col} className={`px-3 py-2 whitespace-nowrap ${isNum ? 'text-right tabular-nums' : ''}`}>
                        {isNull ? (
                          <span className="null-badge italic text-[var(--text-recessive)] text-[10px] px-1.5 py-0.5 rounded-[var(--radius-pill)] bg-[var(--bg-ghost)]">NULL</span>
                        ) : (
                          String(val)
                        )}
                      </td>
                    );
                  })}
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
        impactedTables={lastResponse.approval_payload?.impacted_tables || []}
        generatedSql={lastResponse.generated_sql}
        defaultScope={lastResponse.generated_sql ? 'query' : 'all'}
        title={
          schema && schema.tables.length > 0
            ? `Query ER Scope: ${schema.database_name}`
            : 'Database ER Schema Graph'
        }
      />
    </div>
  );
};
