// src/modules/query_intake/HistorySidebar.tsx — Primer IDE history rail
import React from 'react';
import { History, ChevronLeft, ChevronRight, CheckCircle, AlertCircle, ShieldAlert, Trash2, Database } from 'lucide-react';
import { useQueryStore } from '../../store/useQueryStore';
import { useAppStore } from '../../store/useAppStore';
import { deleteHistoryItemApi, clearHistoryApi } from '../../api/queryApi';
import type { HistoryItem } from '../../types/query';

export const HistorySidebar: React.FC = () => {
  const history = useQueryStore((s) => s.history);
  const deleteHistoryItem = useQueryStore((s) => s.deleteHistoryItem);
  const clearHistory = useQueryStore((s) => s.clearHistory);
  const currentQueryId = useQueryStore((s) => s.currentQueryId);
  const historySidebarOpen = useQueryStore((s) => s.historySidebarOpen);
  const toggleHistorySidebar = useQueryStore((s) => s.toggleHistorySidebar);
  const setLastResponse = useQueryStore((s) => s.setLastResponse);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const setCurrentView = useAppStore((s) => s.setCurrentView);
  const userId = useAppStore((s) => s.userId);

  const handleSelectHistoryItem = (item: HistoryItem) => {
    if (item.is_mutating && item.status === 'approval_required') {
      setApprovalPayload({
        query_id: item.query_id,
        generated_sql: item.generated_sql || '',
        target_dialect: item.target_dialect || 'mysql',
        risk_tier: 'high',
        impacted_tables: [],
        cost_estimate: {
          estimated_rows: 1,
          estimated_cost: 1.0,
          scan_type: 'INDEX_SCAN',
          warnings: ['Mutating query requires explicit confirmation before DBMS execution.'],
        },
        security_check: { deadlock_risk: 'none', lock_level: 'TABLE', privilege_ok: true, flags: [] },
        diff_data: {
          diff_type: 'none',
          ddl_before: null,
          ddl_after: item.generated_sql || null,
          dml_rows: null,
        },
      });
      setCurrentView('approval');
    } else {
      setLastResponse({
        query_id: item.query_id,
        status: (item.status as any) || 'completed',
        generated_sql: item.generated_sql,
        result_data: null,
        approval_payload: null,
        error_message: null,
        cache_hit: false,
        database_profile: item.database_profile || '(No Database Connected)',
        selected_dialect: item.selected_dialect,
        dialect_reason: item.dialect_reason,
        command_blocks: item.command_blocks,
      });
      setCurrentView('query');
    }
  };

  const handleDeleteItem = (e: React.MouseEvent, queryId: string) => {
    e.stopPropagation();
    deleteHistoryItem(queryId);
    deleteHistoryItemApi(userId, queryId);
  };

  const handleClearAll = () => {
    clearHistory();
    clearHistoryApi(userId);
  };

  if (!historySidebarOpen) {
    return (
      <div className="w-9 shrink-0 border-r border-[var(--border-hairline)] bg-[var(--bg-panel)] flex flex-col items-center py-2.5">
        <button
          onClick={toggleHistorySidebar}
          className="p-1.5 rounded-[6px] text-[var(--text-recessive)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-hover)] cursor-pointer transition-colors"
          title="Expand query history"
        >
          <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </button>
        <div className="mt-4 [writing-mode:vertical-rl] rotate-180 text-[11px] font-mono uppercase tracking-[0.08em] text-[var(--text-recessive)]">
          History ({history.length})
        </div>
      </div>
    );
  }

  return (
    <aside className="w-[232px] shrink-0 border-r border-[var(--border-hairline)] bg-[var(--bg-panel)] flex flex-col min-h-0">
      {/* Header — 36px Primer pane header */}
      <div className="h-9 shrink-0 px-3 border-b border-[var(--border-hairline)] bg-[var(--bg-panel)] flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <History className="w-3.5 h-3.5 text-[var(--text-recessive)] shrink-0" aria-hidden="true" />
          <span className="text-[11.5px] font-semibold uppercase tracking-[0.04em] text-[var(--text-recessive)] truncate">
            Query History
          </span>
          <span className="font-mono text-[11px] px-1.5 py-[1px] rounded-[10px] bg-[var(--bg-inset)] border border-[var(--border-hairline)] text-[var(--text-body)]">
            {history.length}
          </span>
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          {history.length > 0 && (
            <button
              onClick={handleClearAll}
              className="p-1 rounded-[6px] text-[var(--text-recessive)] hover:text-[var(--danger)] hover:bg-[var(--bg-hover)] cursor-pointer transition-colors"
              title="Clear all history"
            >
              <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          )}
          <button
            onClick={toggleHistorySidebar}
            className="p-1 rounded-[6px] text-[var(--text-recessive)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-hover)] cursor-pointer transition-colors"
            title="Collapse sidebar"
          >
            <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
        {history.length === 0 ? (
          <div className="p-4 text-center text-[11.5px] text-[var(--text-recessive)] leading-relaxed">
            No queries yet in this session.
            <br />
            Type a question below to begin.
          </div>
        ) : (
          history.map((item) => {
            const isSelected = currentQueryId === item.query_id;
            return (
              <div
                key={item.query_id}
                onClick={() => handleSelectHistoryItem(item)}
                className={`group relative px-2.5 py-2 rounded-[6px] border cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-[var(--bg-canvas)] border-[var(--border-hairline)] text-[var(--text-heading)]'
                    : 'bg-transparent border-transparent text-[var(--text-body)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-heading)]'
                }`}
              >
                <button
                  onClick={(e) => handleDeleteItem(e, item.query_id)}
                  className="absolute top-1.5 right-1.5 p-1 rounded-[4px] opacity-0 group-hover:opacity-100 text-[var(--text-recessive)] hover:text-[var(--danger)] hover:bg-[var(--bg-hover)] cursor-pointer transition-all"
                  title="Delete this query"
                >
                  <Trash2 className="w-3 h-3" aria-hidden="true" />
                </button>

                <div className="flex items-center justify-between mb-1 pr-5 gap-1">
                  <span
                    title={item.dialect_reason || undefined}
                    className={`text-[10px] font-mono uppercase px-1.5 py-[1px] rounded-[4px] cursor-help truncate ${
                      isSelected
                        ? 'bg-[var(--accent-soft)] text-[var(--accent-primary)]'
                        : 'bg-[var(--bg-inset)] text-[var(--text-recessive)]'
                    }`}
                  >
                    {item.target_dialect === 'auto' && item.selected_dialect
                      ? `AUTO:${item.selected_dialect}`
                      : item.target_dialect}
                  </span>
                  <span className="text-[10px] font-mono text-[var(--text-recessive)] shrink-0">{item.timestamp}</span>
                </div>

                <p
                  className={`text-[12px] leading-snug line-clamp-2 mb-1.5 ${
                    isSelected ? 'font-semibold text-[var(--text-heading)]' : 'font-medium'
                  }`}
                >
                  {item.query_text}
                </p>

                <div className="flex items-center justify-between gap-1 text-[10px]">
                  <div className="flex items-center gap-1 min-w-0">
                    {item.status === 'completed' && (
                      <span className="flex items-center gap-1 font-medium text-[var(--success)]">
                        <CheckCircle className="w-2.5 h-2.5 shrink-0" aria-hidden="true" /> Preview
                      </span>
                    )}
                    {item.status === 'approval_required' && (
                      <span className="flex items-center gap-1 font-medium text-[var(--warning)]">
                        <ShieldAlert className="w-2.5 h-2.5 shrink-0" aria-hidden="true" /> Gate
                      </span>
                    )}
                    {item.status === 'error' && (
                      <span className="flex items-center gap-1 font-medium text-[var(--danger)]">
                        <AlertCircle className="w-2.5 h-2.5 shrink-0" aria-hidden="true" /> Blocked
                      </span>
                    )}
                  </div>

                  {item.database_profile && (
                    <span className="flex items-center gap-0.5 font-mono text-[9px] text-[var(--text-recessive)] truncate max-w-[80px]">
                      <Database className="w-2.5 h-2.5 shrink-0" aria-hidden="true" />
                      <span className="truncate">{item.database_profile}</span>
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
