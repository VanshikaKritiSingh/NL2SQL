// src/shared/TopBar.tsx
import React, { useState, useEffect } from 'react';
import { Database, User, ShieldAlert, Sparkles, Sun, Moon, Check, Edit2, PlayCircle, Cpu, Link2, Unlink, Activity } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { useQueryStore } from '../store/useQueryStore';
import { usePipelineStore } from '../store/usePipelineStore';
import { DialectSelector } from './DialectSelector';
import { ConnectionModal } from './ConnectionModal';
import { AuditLogModal } from './AuditLogModal';
import { MOCK_UPDATE_APPROVAL } from '../mock/mockData';
import { apiFetch } from '../api/client';

export const TopBar: React.FC = () => {
  const userId = useAppStore((s) => s.userId);
  const setUserId = useAppStore((s) => s.setUserId);
  const currentView = useAppStore((s) => s.currentView);
  const setCurrentView = useAppStore((s) => s.setCurrentView);
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const wsConnected = usePipelineStore((s) => s.wsConnected);
  const approvalPayload = useQueryStore((s) => s.approvalPayload);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);

  const [isEditingUser, setIsEditingUser] = useState(false);
  const [tempUserName, setTempUserName] = useState(userId);
  const [isConnectOpen, setIsConnectOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [dbStatus, setDbStatus] = useState<{ connected: boolean; database?: string; connector_type?: string } | null>(null);

  const checkDbStatus = async () => {
    try {
      const data = await apiFetch<any>(`/connections/status/${encodeURIComponent(userId)}`);
      setDbStatus({
        connected: Boolean(data.connected || data.attached),
        database: data.database,
        connector_type: data.connector_type,
      });
    } catch {
      setDbStatus({ connected: false });
    }
  };

  useEffect(() => {
    checkDbStatus();
  }, [userId, isConnectOpen]);

  const handleDetachDirect = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiFetch<any>(`/connections/${encodeURIComponent(userId)}`, { method: 'DELETE' });
      setDbStatus({ connected: false });
    } catch {
      // Ignore
    }
  };

  const handleUserSave = () => {
    const trimmed = tempUserName.trim();
    if (trimmed) {
      setUserId(trimmed);
    } else {
      setTempUserName(userId);
    }
    setIsEditingUser(false);
  };

  const handleOpenApprovalGate = () => {
    // Real approval gate is now handled by the ApprovalModal popup triggered from ResultPanel,
    // not a standalone tab navigation. This keeps the top bar clean.
    // If approval payload exists via query response, open modal via external state.
    // For backward compatibility, we just maintain query view focus here.
  };

  const isDark = theme === 'dark';

  return (
    <header
      className="h-14 border-b px-4 flex items-center justify-between shrink-0 transition-colors bg-[var(--bg-header)] border-[var(--border-main)] text-[var(--text-main)] shadow-sm"
    >
      {/* Brand & Subtitle */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-md shadow-indigo-500/20">
          <Database className="w-4 h-4 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm tracking-tight">NL2SQL Studio</span>
          </div>
          <p className={`text-[11px] font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Natural Language SQL Workspace & Schema Safety Gate
          </p>
        </div>
      </div>

      {/* Center Nav: Function Tabs */}
      <div
        className="flex items-center gap-1 p-1 border text-xs bg-[var(--bg-card)] border-[var(--border-subtle)]"
      >
        <button
          onClick={() => setCurrentView('query')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all cursor-pointer ${
            currentView === 'query'
              ? 'bg-[var(--accent-primary)] text-white shadow'
              : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
          }`}
          title="Natural Language Query Intake & SQL Inspector"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Query Intake</span>
        </button>

        <button
          onClick={() => setCurrentView('query')}
          className="flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all cursor-pointer text-[var(--text-muted)] hover:text-[var(--text-main)] bg-[var(--bg-card)]"
          title="Back to Query Intake"
        >
          <Sparkles className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          <span>Query Intake</span>
        </button>
      </div>

      {/* Right Controls: DBMS Dialect, User Profile, Theme Switcher, Engine Status */}
      <div className="flex items-center gap-2.5">
        {/* Dialect Selector */}
        <DialectSelector />

        {/* User Name Input / Profile (Fully Editable) */}
        <div
          className={`flex items-center gap-1.5 border rounded-lg px-2.5 py-1 text-xs transition-all bg-[var(--bg-card)] border-[var(--border-subtle)] focus-within:border-[var(--border-focus)] focus-within:ring-1 focus-within:ring-[var(--accent-glow)]`}
        >
          <User className={`w-3.5 h-3.5 ${isDark ? 'text-slate-400' : 'text-slate-500'}`} />
          <span className={`text-[11px] font-medium ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>User:</span>
          {isEditingUser ? (
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={tempUserName}
                autoFocus
                onChange={(e) => setTempUserName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleUserSave();
                  if (e.key === 'Escape') {
                    setTempUserName(userId);
                    setIsEditingUser(false);
                  }
                }}
                onBlur={handleUserSave}
                className='w-28 bg-transparent font-mono text-xs focus:outline-none select-text text-[var(--accent-primary)]'
                placeholder="Enter user name..."
              />
              <button
                type="button"
                onClick={handleUserSave}
                className="text-[var(--success)] hover:text-[var(--success)] p-0.5 cursor-pointer"
                title="Save user name"
              >
                <Check className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <div
              onClick={() => {
                setTempUserName(userId);
                setIsEditingUser(true);
              }}
              className="flex items-center gap-1 cursor-pointer group"
              title="Click to edit user name"
            >
              <span
                className='font-mono text-xs max-w-[120px] truncate text-[var(--text-main)] group-hover:text-[var(--accent-primary)]'
              >
                {userId}
              </span>
              <Edit2 className="w-2.5 h-2.5 text-slate-500 group-hover:text-indigo-400 opacity-60 group-hover:opacity-100 transition-opacity" />
            </div>
          )}
        </div>

        {/* Connect / Detach Live DB Button */}
        {dbStatus?.connected ? (
          <div className="flex items-center gap-1 border border-[var(--success)] bg-[var(--success-bg)] px-2 py-0.5 text-xs font-mono">
            <span className="w-2 h-2 bg-emerald-400 animate-pulse shrink-0" />
            <button
              onClick={() => setIsConnectOpen(true)}
              className="text-[var(--success)] hover:underline cursor-pointer"
              title="Click to view tables, switch database, or run SQL"
            >
              {dbStatus.connector_type?.toUpperCase() || 'MYSQL'}: <span className="font-bold">{dbStatus.database || 'test'}</span>
            </button>
            <button
              onClick={handleDetachDirect}
              className="ml-1 text-rose-400 hover:text-rose-300 p-0.5 cursor-pointer"
              title="Detach live database socket"
            >
              <Unlink className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => setIsConnectOpen(true)}
            className="flex items-center gap-1.5 px-2.5 py-1 border text-xs font-medium cursor-pointer transition-all bg-[var(--bg-card)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--success)] hover:border-[var(--success)]/50"
            title="Connect a live DBMS socket for real database query execution"
          >
            <Link2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Connect DB</span>
          </button>
        )}

        {/* Audit Log Modal Toggle */}
        <button
          onClick={() => setIsAuditOpen(true)}
          className="flex items-center gap-1.5 px-2.5 py-1 border text-xs font-medium cursor-pointer transition-all bg-[var(--bg-card)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-main)]"
          title="Inspect OS Engine Concurrency & Transaction Audit Log"
        >
          <Activity className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
          <span className="hidden md:inline">Audit Logs</span>
        </button>

        {/* Theme Toggle Button (Light / Dark) */}
        <button
          onClick={toggleTheme}
          className='p-1.5 rounded-lg border transition-all cursor-pointer bg-[var(--bg-card)] border-[var(--border-subtle)] text-[var(--warning)] hover:bg-[var(--bg-hover)] hover:text-[var(--warning)]'
          title='Switch Theme'
          aria-label="Toggle theme"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Engine Status Indicator */}
        <div
          className='flex items-center gap-1.5 px-2 py-1 rounded-md border text-[11px] bg-[var(--bg-card)] border-[var(--border-subtle)]'
          title={wsConnected ? 'WebSocket live stream connected' : 'Client Simulation Engine active'}
        >
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-emerald-500'}`} />
          <span className={`font-mono text-[10px] ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            {wsConnected ? 'LIVE WS' : 'SIMULATION'}
          </span>
        </div>
      </div>

      {/* Live DB Connection Modal */}
      <ConnectionModal isOpen={isConnectOpen} onClose={() => setIsConnectOpen(false)} />

      {/* OS Concurrency & Pipeline Audit Log Modal */}
      <AuditLogModal isOpen={isAuditOpen} onClose={() => setIsAuditOpen(false)} />
    </header>
  );
};
