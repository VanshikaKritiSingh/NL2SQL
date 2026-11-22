// src/shared/AuditLogModal.tsx — Real-Time OS Concurrency & Pipeline Audit Log
import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, Activity, RefreshCw, Terminal, AlertTriangle } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useAppStore } from '../store/useAppStore';

interface AuditEvent {
  event_id: string;
  timestamp: number;
  user_id: string;
  operation: string;
  query_id?: string;
  stage?: number;
  stage_name?: string;
  details?: Record<string, any>;
  concurrency_tag?: string;
}

interface AuditLogModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SEED_AUDIT_EVENTS: AuditEvent[] = [
  {
    event_id: 'evt-os-001',
    timestamp: Math.floor(Date.now() / 1000) - 150,
    user_id: 'bhuknu',
    operation: 'SUBMIT',
    stage: 1,
    stage_name: 'Query Intake & Lexer',
    concurrency_tag: 'WFQ-P0',
    details: { query: 'SELECT * FROM users WHERE status = "active"', target_db: 'test' }
  },
  {
    event_id: 'evt-os-002',
    timestamp: Math.floor(Date.now() / 1000) - 110,
    user_id: 'bhuknu',
    operation: 'LOCK_ACQUIRE',
    stage: 2,
    stage_name: 'LockManager RW Mutex',
    concurrency_tag: 'LockMgr-Shared',
    details: { lock_mode: 'SHARED_READ', table: 'users', grant_status: 'GRANTED', wait_time_ms: 0.4 }
  },
  {
    event_id: 'evt-os-003',
    timestamp: Math.floor(Date.now() / 1000) - 75,
    user_id: 'bhuknu',
    operation: 'EXECUTE',
    stage: 3,
    stage_name: 'AST Dry-Run & Plan Verification',
    concurrency_tag: 'WFQ-Worker-1',
    details: { canonical_sql: 'SELECT id, username, email FROM users WHERE status = "ACTIVE"', elapsed_ms: 12.8 }
  },
  {
    event_id: 'evt-os-004',
    timestamp: Math.floor(Date.now() / 1000) - 30,
    user_id: 'bhuknu',
    operation: 'APPROVE',
    stage: 4,
    stage_name: 'Schema Safety Gate',
    concurrency_tag: 'Gate-Verified',
    details: { risk_level: 'LOW', human_verdict: 'APPROVED', user: 'bhuknu' }
  },
  {
    event_id: 'evt-os-005',
    timestamp: Math.floor(Date.now() / 1000) - 10,
    user_id: 'bhuknu',
    operation: 'LOCK_RELEASE',
    stage: 5,
    stage_name: 'Resource Cleanup & Finalize',
    concurrency_tag: 'LockMgr-Free',
    details: { table: 'users', held_duration_ms: 64.2, status: 'SUCCESS' }
  }
];

export const AuditLogModal: React.FC<AuditLogModalProps> = ({ isOpen, onClose }) => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filterOp, setFilterOp] = useState<string>('all');
  const [isSimulated, setIsSimulated] = useState(false);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const data = await apiFetch<AuditEvent[]>('/audit?limit=100');
      if (Array.isArray(data) && data.length > 0) {
        setEvents(data);
        setIsSimulated(false);
      } else {
        setEvents(SEED_AUDIT_EVENTS);
        setIsSimulated(true);
      }
    } catch {
      setEvents(SEED_AUDIT_EVENTS);
      setIsSimulated(true);
    } finally {
      setIsLoading(false);
    }
  };

  // Escape key handler
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  const filtered = filterOp === 'all'
    ? events
    : events.filter((e) => e.operation.toLowerCase() === filterOp.toLowerCase());

  const getOpBadge = (op: string) => {
    switch (op.toUpperCase()) {
      case 'APPROVE':
        return 'bg-[var(--success-bg)] text-[var(--success)] border-[var(--success)]/40';
      case 'REJECT':
        return 'bg-[var(--danger-bg)] text-[var(--danger)] border-[var(--danger)]/40';
      case 'EXECUTE':
        return 'bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] border-[var(--accent-primary)]/40';
      case 'LOCK_RELEASE':
      case 'LOCK_ACQUIRE':
        return 'bg-[var(--warning-bg)] text-[var(--warning)] border-[var(--warning)]/40';
      default:
        return 'bg-[var(--bg-panel-alt)] text-[var(--text-body)] border-[var(--border-subtle)]';
    }
  };

  const modalTitleId = 'audit-log-modal-title';

  return createPortal(
    <div className="modal-overlay bg-black/80 backdrop-blur-sm animate-fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={modalTitleId}
        className="w-full max-w-5xl h-[min(85vh,calc(100vh-48px))] max-h-[calc(100vh-48px)] rounded-[var(--radius-panel)] shadow-2xl flex flex-col overflow-hidden transition-colors duration-200 my-auto bg-[var(--bg-panel)] border border-[var(--border-hairline)] text-[var(--text-body)]"
      >
        {/* Header */}
        <div
          className="h-14 px-5 border-b flex items-center justify-between shrink-0 bg-[var(--bg-panel-alt)] border-[var(--border-subtle)]"
        >
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-[var(--radius-control)] flex items-center justify-center bg-[var(--accent-primary)]/15 text-[var(--accent-primary)]">
              <Activity className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <h2 id={modalTitleId} className="text-sm font-bold tracking-tight text-[var(--text-heading)]">
                OS Engine Concurrency & Transaction Audit Log
              </h2>
              <p className="text-[10px] font-mono text-[var(--text-recessive)]">
                WFQ Scheduler · WaitForGraph Deadlock Detection · WorkingSet Pager · LockManager
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={filterOp}
              onChange={(e) => setFilterOp(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-[var(--radius-control)] border font-mono cursor-pointer focus:outline-none focus:border-[var(--border-focus)] bg-[var(--bg-canvas)] border-[var(--border-subtle)] text-[var(--text-body)]"
            >
              <option value="all">All Operations</option>
              <option value="SUBMIT">SUBMIT</option>
              <option value="EXECUTE">EXECUTE</option>
              <option value="APPROVE">APPROVE</option>
              <option value="REJECT">REJECT</option>
              <option value="LOCK_RELEASE">LOCK_RELEASE</option>
            </select>

            <button
              onClick={fetchLogs}
              disabled={isLoading}
              className="p-2 rounded-[var(--radius-control)] border transition-colors duration-200 cursor-pointer bg-[var(--bg-panel-alt)] border-[var(--border-subtle)] text-[var(--text-recessive)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-ghost)]"
              title="Refresh Logs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} aria-hidden="true" />
            </button>

            <button
              onClick={onClose}
              className="p-2 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer text-[var(--text-recessive)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-ghost)]"
              title="Close Audit Log"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-auto p-4 bg-[var(--bg-canvas)]">
          {/* Simulated data warning banner */}
          {isSimulated && (
            <div className="flex items-center gap-2 px-3.5 py-2.5 mb-3 rounded-[var(--radius-control)] border bg-[var(--warning-bg)] border-[var(--warning)]/30 text-[var(--warning)]">
              <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <p className="text-xs font-medium">
                Showing simulated audit data — connect to backend for live events
              </p>
            </div>
          )}

          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-8 border rounded-[var(--radius-panel)] bg-[var(--bg-panel)] border-[var(--border-subtle)] text-[var(--text-recessive)]">
              <Terminal className="w-8 h-8 mb-2 opacity-50" aria-hidden="true" />
              <p className="text-xs font-mono font-semibold">No audit events recorded for operation filter '{filterOp}'.</p>
              <p className="text-[11px] mt-1">Submit queries or approval actions to populate the OS audit stream.</p>
            </div>
          ) : (
            <div className="border rounded-[var(--radius-panel)] overflow-hidden border-[var(--border-subtle)] bg-[var(--bg-panel)]">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead className="sticky top-0 border-b text-[11px] bg-[var(--bg-panel-alt)] border-[var(--border-subtle)] text-[var(--text-heading)]">
                  <tr>
                    <th className="px-3.5 py-2.5">Timestamp</th>
                    <th className="px-3.5 py-2.5">Operation</th>
                    <th className="px-3.5 py-2.5">Stage</th>
                    <th className="px-3.5 py-2.5">User / Concurrency Tag</th>
                    <th className="px-3.5 py-2.5">Details / SQL / Locks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-hairline)] text-[var(--text-body)]">
                  {filtered.map((ev) => (
                    <tr
                      key={ev.event_id}
                      className="transition-colors duration-200 hover:bg-[var(--bg-ghost)]"
                    >
                      <td className="px-3.5 py-2.5 whitespace-nowrap text-[11px] text-[var(--text-recessive)]">
                        {new Date(ev.timestamp * 1000).toLocaleTimeString()}
                      </td>
                      <td className="px-3.5 py-2.5 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded-[var(--radius-pill)] text-[10px] font-bold border ${getOpBadge(ev.operation)}`}>
                          {ev.operation}
                        </span>
                      </td>
                      <td className="px-3.5 py-2.5 whitespace-nowrap text-[11px] font-semibold">
                        {ev.stage_name || `Stage ${ev.stage ?? 0}`}
                      </td>
                      <td className="px-3.5 py-2.5 whitespace-nowrap text-[11px] text-[var(--text-body)]">
                        {ev.user_id} {ev.concurrency_tag && <span className="text-[var(--text-recessive)]">({ev.concurrency_tag})</span>}
                      </td>
                      <td className="px-3.5 py-2.5 text-[11px] font-mono break-all max-w-md">
                        {ev.details?.canonical_sql || ev.details?.query || ev.details?.message || JSON.stringify(ev.details || {})}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};
