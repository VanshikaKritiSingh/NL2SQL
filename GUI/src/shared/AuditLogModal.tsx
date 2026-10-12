// src/shared/AuditLogModal.tsx — Real-Time OS Concurrency & Pipeline Audit Log
import React, { useState, useEffect } from 'react';
import { X, Activity, RefreshCw, Shield, Lock, CheckCircle2, AlertTriangle, Terminal } from 'lucide-react';
import { apiFetch } from '../api/client';

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

export const AuditLogModal: React.FC<AuditLogModalProps> = ({ isOpen, onClose }) => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filterOp, setFilterOp] = useState<string>('all');

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const data = await apiFetch<AuditEvent[]>('/audit?limit=100');
      setEvents(data);
    } catch {
      // Ignore or empty
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filtered = filterOp === 'all'
    ? events
    : events.filter((e) => e.operation.toLowerCase() === filterOp.toLowerCase());

  const getOpBadge = (op: string) => {
    switch (op.toUpperCase()) {
      case 'APPROVE':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'REJECT':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      case 'EXECUTE':
        return 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30';
      case 'LOCK_RELEASE':
      case 'LOCK_ACQUIRE':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      default:
        return 'bg-[var(--bg-subtle)] text-[var(--text-muted)] border-[var(--border-subtle)]';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-5xl h-[85vh] border rounded-2xl shadow-2xl flex flex-col overflow-hidden bg-[var(--bg-card)] border-[var(--border-main)]">
        {/* Header */}
        <div className="h-13 px-4 border-b flex items-center justify-between shrink-0 bg-[var(--bg-card-header)] border-[var(--border-subtle)]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-[var(--accent-glow)] text-[var(--accent-primary)]">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight text-[var(--text-main)]">
                OS Engine Concurrency & Transaction Audit Log
              </h2>
              <p className="text-[10px] text-[var(--text-muted)] font-mono">
                WFQ Scheduler · WaitForGraph Deadlock Detection · WorkingSet Pager · LockManager
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={filterOp}
              onChange={(e) => setFilterOp(e.target.value)}
              className="text-xs px-2 py-1 rounded-lg border font-mono cursor-pointer bg-[var(--bg-input)] border-[var(--border-subtle)] text-[var(--text-main)]"
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
              className="p-1.5 rounded-lg border transition-colors cursor-pointer bg-[var(--bg-card)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)]"
              title="Refresh Logs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg transition-colors cursor-pointer text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)]"
              title="Close Audit Log"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-auto p-4 bg-[var(--bg-app)]">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-6 text-[var(--text-muted)]">
              <Terminal className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-xs font-mono">No audit events recorded yet.</p>
              <p className="text-[11px] mt-1">Submit queries or approval actions to populate the OS audit stream.</p>
            </div>
          ) : (
            <table className="w-full text-left text-xs border-collapse font-mono">
              <thead className="sticky top-0 border-b text-[11px] bg-[var(--bg-card-header)] border-[var(--border-subtle)] text-[var(--text-secondary)]">
                <tr>
                  <th className="px-3 py-2">Timestamp</th>
                  <th className="px-3 py-2">Operation</th>
                  <th className="px-3 py-2">Stage</th>
                  <th className="px-3 py-2">User / Concurrency Tag</th>
                  <th className="px-3 py-2">Details / SQL / Locks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)] text-[var(--text-main)]">
                {filtered.map((ev) => (
                  <tr key={ev.event_id} className="transition-colors hover:bg-[var(--bg-hover)]">
                    <td className="px-3 py-2 whitespace-nowrap text-[11px] text-[var(--text-muted)]">
                      {new Date(ev.timestamp * 1000).toLocaleTimeString()}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${getOpBadge(ev.operation)}`}>
                        {ev.operation}
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-[11px]">
                      {ev.stage_name || `Stage ${ev.stage ?? 0}`}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-[11px] text-[var(--text-secondary)]">
                      {ev.user_id} {ev.concurrency_tag && <span className="text-[var(--text-muted)]">({ev.concurrency_tag})</span>}
                    </td>
                    <td className="px-3 py-2 text-[11px] font-mono break-all max-w-md">
                      {ev.details?.canonical_sql || ev.details?.query || ev.details?.message || JSON.stringify(ev.details || {})}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
