// src/shared/AuditLogModal.tsx — Visual Git-Tree Style Transaction Logs
import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, RefreshCw, Terminal, AlertTriangle, GitCommit, GitBranch, GitMerge, Lock, Unlock, Play, CheckCircle2, ShieldAlert } from 'lucide-react';
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
    event_id: 'evt-001',
    timestamp: Math.floor(Date.now() / 1000) - 150,
    user_id: 'analyst_1',
    operation: 'SUBMIT',
    stage: 1,
    stage_name: 'Query Intake & Lexer',
    concurrency_tag: 'main',
    details: { query: 'SELECT * FROM users WHERE status = "active"', target_db: 'test' }
  },
  {
    event_id: 'evt-002',
    timestamp: Math.floor(Date.now() / 1000) - 110,
    user_id: 'analyst_1',
    operation: 'LOCK_ACQUIRE',
    stage: 2,
    stage_name: 'LockManager RW Mutex',
    concurrency_tag: 'branch/mutex-users',
    details: { lock_mode: 'SHARED_READ', table: 'users', grant_status: 'GRANTED', wait_time_ms: 0.4 }
  },
  {
    event_id: 'evt-003',
    timestamp: Math.floor(Date.now() / 1000) - 75,
    user_id: 'analyst_1',
    operation: 'EXECUTE',
    stage: 3,
    stage_name: 'AST Dry-Run & Plan Verification',
    concurrency_tag: 'worker-1',
    details: { canonical_sql: 'SELECT id, username, email FROM users WHERE status = "ACTIVE"', elapsed_ms: 12.8 }
  },
  {
    event_id: 'evt-004',
    timestamp: Math.floor(Date.now() / 1000) - 30,
    user_id: 'analyst_1',
    operation: 'APPROVE',
    stage: 4,
    stage_name: 'Schema Safety Gate',
    concurrency_tag: 'main',
    details: { risk_level: 'LOW', human_verdict: 'APPROVED', user: 'analyst_1' }
  },
  {
    event_id: 'evt-005',
    timestamp: Math.floor(Date.now() / 1000) - 10,
    user_id: 'analyst_1',
    operation: 'LOCK_RELEASE',
    stage: 5,
    stage_name: 'Resource Cleanup & Finalize',
    concurrency_tag: 'merge/cleanup',
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

  const getNodeVisual = (op: string) => {
    switch (op.toUpperCase()) {
      case 'SUBMIT':
        return {
          icon: Play,
          ringColor: 'ring-sky-500/30 border-sky-500 bg-sky-500 text-white',
          branchColor: 'text-sky-500',
          badgeClass: 'bg-sky-500/15 text-sky-400 border-sky-500/40',
        };
      case 'LOCK_ACQUIRE':
        return {
          icon: Lock,
          ringColor: 'ring-amber-500/30 border-amber-500 bg-amber-500 text-black',
          branchColor: 'text-amber-500',
          badgeClass: 'bg-amber-500/15 text-amber-400 border-amber-500/40',
        };
      case 'ROUTED':
        return {
          icon: GitBranch,
          ringColor: 'ring-indigo-500/30 border-indigo-500 bg-indigo-500 text-white',
          branchColor: 'text-indigo-500',
          badgeClass: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/40',
        };
      case 'EXECUTE':
        return {
          icon: GitCommit,
          ringColor: 'ring-purple-500/30 border-purple-500 bg-purple-500 text-white',
          branchColor: 'text-purple-500',
          badgeClass: 'bg-purple-500/15 text-purple-400 border-purple-500/40',
        };
      case 'APPROVE':
        return {
          icon: CheckCircle2,
          ringColor: 'ring-emerald-500/30 border-emerald-500 bg-emerald-500 text-white',
          branchColor: 'text-emerald-500',
          badgeClass: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40',
        };
      case 'REJECT':
        return {
          icon: ShieldAlert,
          ringColor: 'ring-rose-500/30 border-rose-500 bg-rose-500 text-white',
          branchColor: 'text-rose-500',
          badgeClass: 'bg-rose-500/15 text-rose-400 border-rose-500/40',
        };
      case 'LOCK_RELEASE':
        return {
          icon: Unlock,
          ringColor: 'ring-teal-500/30 border-teal-500 bg-teal-500 text-white',
          branchColor: 'text-teal-500',
          badgeClass: 'bg-teal-500/15 text-teal-400 border-teal-500/40',
        };
      default:
        return {
          icon: GitMerge,
          ringColor: 'ring-zinc-500/30 border-zinc-500 bg-zinc-500 text-white',
          branchColor: 'text-zinc-500',
          badgeClass: 'bg-zinc-500/15 text-zinc-300 border-zinc-500/40',
        };
    }
  };

  const modalTitleId = 'audit-log-modal-title';

  return createPortal(
    <div className="modal-overlay bg-black/80 backdrop-blur-sm animate-fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={modalTitleId}
        className="w-full max-w-4xl h-[min(88vh,calc(100vh-48px))] max-h-[calc(100vh-48px)] rounded-[var(--radius-panel)] shadow-2xl flex flex-col overflow-hidden transition-colors duration-200 my-auto bg-[var(--bg-panel)] border border-[var(--border-hairline)] text-[var(--text-body)]"
      >
        {/* Header — 2 words title: Transaction Logs */}
        <div
          className="h-14 px-5 border-b flex items-center justify-between shrink-0 bg-[var(--bg-panel-alt)] border-[var(--border-subtle)]"
        >
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-[var(--radius-control)] flex items-center justify-center bg-[var(--accent-primary)]/15 text-[var(--accent-primary)]">
              <GitBranch className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <h2 id={modalTitleId} className="text-sm font-bold tracking-tight text-[var(--text-heading)]">
                Transaction Logs
              </h2>
              <p className="text-[10px] font-mono text-[var(--text-recessive)]">
                Sequential branch tree & lock timeline
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
              <option value="ROUTED">ROUTED</option>
              <option value="EXECUTE">EXECUTE</option>
              <option value="APPROVE">APPROVE</option>
              <option value="REJECT">REJECT</option>
              <option value="LOCK_ACQUIRE">LOCK_ACQUIRE</option>
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
              title="Close Logs"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Content Body with Git Commit Tree Layout */}
        <div className="flex-1 overflow-y-auto p-5 bg-[var(--bg-canvas)]">
          {/* Simulated data warning banner */}
          {isSimulated && (
            <div className="flex items-center gap-2 px-3.5 py-2 mb-4 rounded-[var(--radius-control)] border bg-[var(--warning-bg)] border-[var(--warning)]/30 text-[var(--warning)]">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
              <p className="text-[11px] font-medium">
                Displaying sandbox event simulation — real pipeline events record live transactions automatically.
              </p>
            </div>
          )}

          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-center p-8 border rounded-[var(--radius-panel)] bg-[var(--bg-panel)] border-[var(--border-subtle)] text-[var(--text-recessive)]">
              <Terminal className="w-8 h-8 mb-2 opacity-50" aria-hidden="true" />
              <p className="text-xs font-mono font-semibold">No transactions recorded for filter '{filterOp}'.</p>
              <p className="text-[11px] mt-1">Execute queries to populate the real-time event tree.</p>
            </div>
          ) : (
            <div className="relative pl-6">
              {/* Continuous Git Tree Trunk Line */}
              <div className="absolute left-[15px] top-3 bottom-4 w-0.5 bg-gradient-to-b from-[var(--accent-primary)]/40 via-[var(--border-hairline)] to-transparent" />

              <div className="space-y-4">
                {filtered.map((ev, idx) => {
                  const visual = getNodeVisual(ev.operation);
                  const Icon = visual.icon;
                  const isLast = idx === filtered.length - 1;

                  return (
                    <div key={ev.event_id || idx} className="relative flex items-start gap-4 group">
                      {/* Commit Node Icon */}
                      <div className="relative -ml-[23px] shrink-0 z-10">
                        <div
                          className={`w-6 h-6 rounded-full flex items-center justify-center border shadow-xs ring-4 transition-transform group-hover:scale-110 ${visual.ringColor}`}
                          title={`${ev.operation} (${ev.stage_name || 'Stage'})`}
                        >
                          <Icon className="w-3 h-3 stroke-[2.5]" />
                        </div>
                      </div>

                      {/* Commit Card with Indentation */}
                      <div className="flex-1 p-3.5 rounded-xl border border-[var(--border-hairline)] bg-[var(--bg-panel)] shadow-sm hover:border-[var(--accent-primary)]/40 transition-colors">
                        {/* Top Metadata Row */}
                        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-[var(--border-hairline)]/70">
                          <div className="flex items-center gap-2 flex-wrap">
                            {/* Commit Hash Badge */}
                            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-canvas)] border border-[var(--border-subtle)] text-[var(--text-recessive)] font-semibold">
                              {ev.event_id || `tr-${idx + 1}`}
                            </span>

                            {/* Operation Badge */}
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase border ${visual.badgeClass}`}>
                              {ev.operation}
                            </span>

                            {/* Stage Name */}
                            <span className="text-xs font-semibold text-[var(--text-heading)]">
                              {ev.stage_name || `Stage ${ev.stage ?? 0}`}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-[10px] font-mono text-[var(--text-recessive)]">
                            {/* Branch / Worker Tag */}
                            <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-[var(--bg-ghost)] border border-[var(--border-subtle)]">
                              <GitBranch className="w-2.5 h-2.5" />
                              <span>{ev.concurrency_tag || 'main'}</span>
                            </span>
                            <span>{new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                          </div>
                        </div>

                        {/* Indented Content / SQL / Lock Details */}
                        <div className="mt-2 text-xs font-mono">
                          {ev.details?.canonical_sql || ev.details?.query ? (
                            <div className="p-2.5 rounded-lg bg-black/90 text-emerald-400 border border-black overflow-x-auto select-all">
                              <code>{ev.details.canonical_sql || ev.details.query}</code>
                              {ev.details?.elapsed_ms !== undefined && (
                                <div className="mt-1 text-[10px] text-zinc-400 font-sans flex items-center gap-2">
                                  <span>Elapsed: <strong className="text-emerald-300 font-mono">{ev.details.elapsed_ms}ms</strong></span>
                                  {ev.details?.target_db && (
                                    <span>Target DB: <strong className="text-amber-300 font-mono">{ev.details.target_db}</strong></span>
                                  )}
                                </div>
                              )}
                            </div>
                          ) : ev.operation.includes('LOCK') ? (
                            <div className="flex items-center gap-2 flex-wrap text-[11px] p-2 rounded-lg bg-[var(--bg-ghost)] border border-[var(--border-subtle)] text-[var(--text-body)]">
                              <span>Table: <strong className="text-[var(--text-heading)] font-bold">{ev.details?.table || 'all'}</strong></span>
                              <span>•</span>
                              <span>Mode: <strong className="text-amber-400 font-bold">{ev.details?.lock_mode || 'EXCLUSIVE'}</strong></span>
                              {ev.details?.held_duration_ms && (
                                <>
                                  <span>•</span>
                                  <span>Held: <strong>{ev.details.held_duration_ms}ms</strong></span>
                                </>
                              )}
                              <span>•</span>
                              <span className="text-[var(--success)] font-semibold">{ev.details?.status || 'GRANTED'}</span>
                            </div>
                          ) : (
                            <div className="p-2 rounded-lg bg-[var(--bg-ghost)] border border-[var(--border-subtle)] text-[11px] text-[var(--text-body)] leading-relaxed">
                              {ev.details?.message || JSON.stringify(ev.details || {}, null, 2)}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};
