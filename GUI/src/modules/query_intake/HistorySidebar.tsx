// src/modules/query_intake/HistorySidebar.tsx
import React from 'react';
import { History, ChevronLeft, ChevronRight, CheckCircle, AlertCircle, ShieldAlert, Trash2, Database } from 'lucide-react';
import { useQueryStore } from '../../store/useQueryStore';
import { useAppStore } from '../../store/useAppStore';
import { deleteHistoryItemApi, clearHistoryApi } from '../../api/queryApi';
import { MOCK_UPDATE_APPROVAL } from '../../mock/mockData';
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
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const handleSelectHistoryItem = (item: HistoryItem) => {
    if (item.is_mutating) {
      setApprovalPayload(MOCK_UPDATE_APPROVAL);
      setCurrentView('approval');
    } else {
      setLastResponse({
        query_id: item.query_id,
        status: item.status,
        generated_sql: item.generated_sql,
        result_data: {
          columns: ['order_id', 'full_name', 'order_date', 'total_amount', 'status'],
          rows: [
            { order_id: 1042, full_name: 'Aarav Patel', order_date: '2025-02-14 10:30:00', total_amount: '$149.99', status: 'COMPLETED' },
            { order_id: 1043, full_name: 'Diya Sharma', order_date: '2025-02-16 15:45:00', total_amount: '$320.50', status: 'COMPLETED' },
            { order_id: 1044, full_name: 'Rohan Verma', order_date: '2025-02-20 18:20:00', total_amount: '$89.00', status: 'PENDING' },
          ],
          row_count: 3,
        },
        approval_payload: null,
        error_message: null,
        cache_hit: false,
        database_profile: item.database_profile || '(No Database Connected)',
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
      <div
        className={`w-10 border-r flex flex-col items-center py-3 shrink-0 transition-colors duration-300 ${
          isDark
            ? 'border-[var(--border-main)] bg-[var(--bg-header)]'
            : 'border-[var(--border-subtle)] bg-[var(--bg-card)]'
        }`}
      >
        <button
          onClick={toggleHistorySidebar}
          className="p-1.5 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer hover:bg-[var(--bg-hover)] text-[var(--text-muted)] hover:text-[var(--text-main)]"
          title="Expand Query History"
        >
          <ChevronRight aria-hidden="true" className="w-4 h-4" />
        </button>
        <div className="mt-4 [writing-mode:vertical-rl] rotate-180 text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)]">
          History ({history.length})
        </div>
      </div>
    );
  }

  return (
    <aside
      className={`w-64 border-r flex flex-col shrink-0 transition-colors duration-300 ${
        isDark
          ? 'border-[var(--border-main)] bg-[var(--bg-header)]'
          : 'border-[var(--border-subtle)] bg-[var(--bg-card)]'
      }`}
    >
      {/* Header */}
      <div
        className={`h-11 px-3 border-b flex items-center justify-between transition-colors ${
          isDark
            ? 'border-[var(--border-main)] bg-[var(--bg-card-header)]'
            : 'border-[var(--border-subtle)] bg-[var(--bg-card-header)]'
        }`}
      >
        <div className="flex items-center gap-2 text-xs font-semibold">
          <History aria-hidden="true" className={`w-3.5 h-3.5 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`} />
          <span className="text-[var(--text-main)]">Query History</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-[var(--radius-pill)] font-mono bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border-subtle)]">
            {history.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {history.length > 0 && (
            <button
              onClick={handleClearAll}
              className="p-1 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer hover:bg-[var(--bg-hover)] text-[var(--text-muted)] hover:text-[var(--danger)]"
              title="Clear all history"
            >
              <Trash2 aria-hidden="true" className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={toggleHistorySidebar}
            className="p-1 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer hover:bg-[var(--bg-hover)] text-[var(--text-muted)] hover:text-[var(--text-main)]"
            title="Collapse Sidebar"
          >
            <ChevronLeft aria-hidden="true" className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* History Items List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {history.length === 0 ? (
          <div className="p-4 text-center text-xs text-[var(--text-muted)]">
            No queries in current session. Type a natural language question to start.
          </div>
        ) : (
          history.map((item) => {
            const isSelected = currentQueryId === item.query_id;
            return (
              <div
                key={item.query_id}
                onClick={() => handleSelectHistoryItem(item)}
                className={`p-2.5 rounded-[var(--radius-panel)] border transition-colors duration-200 cursor-pointer group relative ${
                  isSelected
                    ? isDark
                      ? 'bg-[var(--accent-primary)] border-[var(--accent-primary)] text-white shadow-md'
                      : 'bg-[var(--accent-primary)] border-[var(--accent-primary)] text-white shadow-md'
                    : isDark
                    ? 'bg-[var(--bg-panel)] hover:bg-[var(--bg-hover)] border-[var(--border-panel)] hover:border-[var(--accent-primary)]/30'
                    : 'bg-[var(--bg-panel)] hover:bg-[var(--bg-hover)] border-[var(--border-subtle)] hover:border-[var(--border-main)]'
                }`}
              >
                {/* Delete button on hover */}
                <button
                  onClick={(e) => handleDeleteItem(e, item.query_id)}
                  className={`absolute top-2 right-2 p-1 rounded-[var(--radius-control)] opacity-0 group-hover:opacity-100 transition-colors duration-200 cursor-pointer ${
                    isSelected
                      ? 'hover:bg-white/20 text-white/70 hover:text-white'
                      : isDark
                      ? 'hover:bg-[var(--danger-bg)] text-[var(--text-muted)] hover:text-[var(--danger)]'
                      : 'hover:bg-[var(--danger-bg)] text-[var(--text-muted)] hover:text-[var(--danger)]'
                  }`}
                  title="Delete this query"
                >
                  <Trash2 aria-hidden="true" className="w-3 h-3" />
                </button>

                <div className="flex items-center justify-between mb-1 pr-4">
                  <span
                    title={item.dialect_reason || undefined}
                    className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-[var(--radius-pill)] cursor-help ${
                      isSelected
                        ? 'bg-white/20 text-white border border-white/20'
                        : item.target_dialect === 'auto'
                        ? isDark
                          ? 'bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30 font-semibold'
                          : 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] border border-[var(--btn-primary-bg)] font-semibold'
                        : isDark
                        ? 'bg-[var(--bg-subtle)] text-[var(--text-muted)]'
                        : 'bg-[var(--bg-card-header)] text-[var(--text-muted)]'
                    }`}
                  >
                    {item.target_dialect === 'auto' && item.selected_dialect
                      ? `AUTO: ${item.selected_dialect}`
                      : item.target_dialect}
                  </span>
                  <span className={`text-[10px] font-mono ${isSelected ? 'text-white/70' : 'text-[var(--text-muted)]'}`}>
                    {item.timestamp}
                  </span>
                </div>

                <p className={`text-xs line-clamp-2 font-bold mb-1.5 ${
                  isSelected ? 'text-white' : 'text-[var(--text-main)]'
                }`}>
                  {item.query_text}
                </p>

                <div className="flex items-center justify-between text-[10px]">
                  <div className="flex items-center gap-1">
                    {item.status === 'completed' && (
                      <span className={`flex items-center gap-1 font-medium ${isSelected ? 'text-[var(--success)]/80' : 'text-[var(--success)]'}`}>
                        <CheckCircle aria-hidden="true" className="w-3 h-3" /> Preview
                      </span>
                    )}
                    {item.status === 'approval_required' && (
                      <span className={`flex items-center gap-1 font-medium ${isSelected ? 'text-[var(--warning)]/80' : 'text-[var(--warning)]'}`}>
                        <ShieldAlert aria-hidden="true" className="w-3 h-3" /> Gate Review
                      </span>
                    )}
                    {item.status === 'error' && (
                      <span className={`flex items-center gap-1 font-medium ${isSelected ? 'text-[var(--danger)]/80' : 'text-[var(--danger)]'}`}>
                        <AlertCircle aria-hidden="true" className="w-3 h-3" /> Blocked
                      </span>
                    )}
                  </div>

                  {item.database_profile && (
                    <span className={`flex items-center gap-0.5 text-[9px] font-mono truncate max-w-[90px] ${
                      isSelected ? 'text-white/70' : isDark ? 'text-[var(--accent-primary)]/80' : 'text-[var(--text-muted)]'
                    }`}>
                      <Database aria-hidden="true" className="w-2.5 h-2.5 shrink-0" />
                      <span className="truncate">{item.database_profile.replace('_', ' ')}</span>
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
