// src/shared/TopBar.tsx
import React, { useState, useEffect } from 'react';
import { Database, User, Sun, Moon, Check, Edit2, Link2, Unlink, Activity } from 'lucide-react';
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
  const setIsDbConnected = useAppStore((s) => s.setIsDbConnected);
  const setConnectedEngine = useAppStore((s) => s.setConnectedEngine);
  const setDatabaseProfile = useAppStore((s) => s.setDatabaseProfile);
  const setAvailableDatabases = useAppStore((s) => s.setAvailableDatabases);

  const [isEditingUser, setIsEditingUser] = useState(false);
  const [tempUserName, setTempUserName] = useState(userId);
  const [isConnectOpen, setIsConnectOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [dbStatus, setDbStatus] = useState<{ connected: boolean; database?: string; connector_type?: string } | null>(null);

  const checkDbStatus = async () => {
    try {
      const data = await apiFetch<any>(`/connections/status/${encodeURIComponent(userId)}`);
      const connected = Boolean(data && (data.connected || data.attached));
      setDbStatus({
        connected,
        database: data?.database,
        connector_type: data?.connector_type,
      });
      setIsDbConnected(connected);
      if (connected) {
        if (data.connector_type) setConnectedEngine(data.connector_type);
        if (data.database) setDatabaseProfile(data.database);
        if (Array.isArray(data.databases) && data.databases.length > 0) {
          setAvailableDatabases(data.databases);
        }
      } else {
        setConnectedEngine(null);
      }
    } catch {
      setDbStatus({ connected: false });
      setIsDbConnected(false);
      setConnectedEngine(null);
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
      setIsDbConnected(false);
      setConnectedEngine(null);
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

  const isDark = theme === 'dark';

  return (
    <>
      <header
        className={`min-h-14 h-14 border-b px-3 sm:px-5 flex items-center justify-between shrink-0 transition-all duration-300 relative z-20 overflow-x-auto overflow-y-hidden gap-3 ${
          isDark
            ? 'bg-[var(--bg-header)]/80 backdrop-blur-xl border-[var(--border-main)]'
            : 'bg-white border-[var(--border-main)]'
        } text-[var(--text-main)]`}
      >
      {/* Brand & Subtitle */}
      <div className="flex items-center gap-2.5 sm:gap-3 shrink-0 min-w-0">
        <div className={`w-8 h-8 rounded-none shrink-0 flex items-center justify-center shadow-md ${
          isDark
            ? 'bg-gradient-to-tr from-[#8E94F2] to-[#B48EBA] shadow-[#8E94F2]/20'
            : 'bg-[#111111] shadow-black/10'
        }`}>
          <Database className="w-4 h-4 text-white" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm tracking-tight whitespace-nowrap">NL2SQL Studio</span>
          </div>
          <p className="text-[11px] font-medium text-[var(--text-muted)] whitespace-nowrap overflow-hidden text-ellipsis hidden sm:block max-w-[240px] md:max-w-none">
            Natural Language SQL Workspace & Schema Safety Gate
          </p>
        </div>
      </div>

      {/* Center Nav: Function Tab */}
      <div className={`flex items-center gap-1 p-1 rounded-none text-xs shrink-0 whitespace-nowrap ${
        isDark ? 'bg-[var(--bg-card)]' : 'bg-[var(--bg-card)]'
      }`}>
        <button
          onClick={() => setCurrentView('query')}
          className={`flex items-center gap-1.5 px-3 sm:px-4 py-1.5 rounded-none font-medium transition-all cursor-pointer shrink-0 whitespace-nowrap ${
            currentView === 'query'
              ? isDark
                ? 'bg-[var(--accent-primary)] text-white shadow-md ambient-glow-btn'
                : 'bg-[#111111] text-white shadow-md'
              : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
          }`}
          title="Natural Language Query Intake & SQL Inspector"
        >
          <span>Query Intake</span>
        </button>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 whitespace-nowrap">
        {/* Dialect Selector */}
        <DialectSelector />

        {/* User Name Input / Profile */}
        <div className={`flex items-center gap-1.5 rounded-none px-2.5 py-1.5 text-xs transition-all shrink-0 whitespace-nowrap ${
          isDark
            ? 'bg-[var(--bg-card)] border border-[var(--border-main)]'
            : 'bg-[var(--bg-card)] border border-[var(--border-subtle)]'
        } focus-within:border-[var(--border-focus)] focus-within:ring-1 focus-within:ring-[var(--accent-glow)]`}>
          <User className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
          <span className="text-[11px] font-medium text-[var(--text-muted)] shrink-0 whitespace-nowrap">User:</span>
          {isEditingUser ? (
            <div className="flex items-center gap-1 shrink-0">
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
                className="w-28 bg-transparent font-mono text-xs focus:outline-none select-text text-[var(--accent-primary)] rounded-none"
                placeholder="Enter user name..."
              />
              <button
                type="button"
                onClick={handleUserSave}
                className="text-[var(--success)] hover:text-[var(--success)] p-0.5 cursor-pointer rounded-none"
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
              className="flex items-center gap-1 cursor-pointer group shrink-0"
              title="Click to edit user name"
            >
              <span className="font-mono text-xs max-w-[120px] truncate text-[var(--text-main)] group-hover:text-[var(--accent-primary)]">
                {userId}
              </span>
              <Edit2 className="w-2.5 h-2.5 text-[var(--text-muted)] group-hover:text-[var(--accent-primary)] opacity-60 group-hover:opacity-100 transition-opacity" />
            </div>
          )}
        </div>

        {/* Connect / Detach Live DB Button */}
        {dbStatus?.connected ? (
          <div className={`flex items-center gap-1 rounded-none px-2.5 py-1 text-xs font-mono shrink-0 whitespace-nowrap ${
            isDark
              ? 'border border-[var(--success)]/30 bg-[var(--success-bg)]'
              : 'border border-[var(--success)]/30 bg-[var(--success-bg)]'
          }`}>
            <span className="w-2 h-2 rounded-none bg-emerald-400 animate-pulse shrink-0" />
            <button
              onClick={() => setIsConnectOpen(true)}
              className="text-[var(--success)] hover:underline cursor-pointer shrink-0 whitespace-nowrap"
              title="Click to view tables, switch database, or run SQL"
            >
              {dbStatus.connector_type?.toUpperCase() || 'MYSQL'}: <span className="font-bold">{dbStatus.database || 'test'}</span>
            </button>
            <button
              onClick={handleDetachDirect}
              className="ml-1 text-rose-400 hover:text-rose-300 p-0.5 cursor-pointer rounded-none shrink-0"
              title="Detach live database socket"
            >
              <Unlink className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => setIsConnectOpen(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-none text-xs font-medium cursor-pointer transition-all shrink-0 whitespace-nowrap ${
              isDark
                ? 'bg-[var(--bg-card)] border border-[var(--border-main)] text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--success)] hover:border-[var(--success)]/50'
                : 'bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--success)] hover:border-[var(--success)]'
            }`}
            title="Connect a live DBMS socket for real database query execution"
          >
            <Link2 className="w-3.5 h-3.5 shrink-0" />
            <span className="hidden sm:inline whitespace-nowrap">Connect DB</span>
          </button>
        )}

        {/* Audit Log Modal Toggle */}
        <button
          onClick={() => setIsAuditOpen(true)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-none text-xs font-medium cursor-pointer transition-all shrink-0 whitespace-nowrap ${
            isDark
              ? 'bg-[var(--bg-card)] border border-[var(--border-main)] text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-main)]'
              : 'bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-main)]'
          }`}
          title="Inspect OS Engine Concurrency & Transaction Audit Log"
        >
          <Activity className={`w-3.5 h-3.5 shrink-0 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`} />
          <span className="hidden md:inline whitespace-nowrap">Audit Logs</span>
        </button>

        {/* Theme Toggle — two options: Light (Sun) / Dark (Moon) */}
        <button
          onClick={toggleTheme}
          className={`p-2 rounded-none transition-all cursor-pointer shrink-0 ${
            isDark
              ? 'bg-[var(--bg-card)] border border-[var(--border-main)] text-[var(--warning)] hover:bg-[var(--bg-hover)]'
              : 'bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--warning)] hover:bg-[var(--bg-hover)]'
          }`}
          title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          aria-label="Toggle theme"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Engine Status Indicator */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-none text-[11px] shrink-0 whitespace-nowrap ${
            isDark
              ? 'bg-[var(--bg-card)] border border-[var(--border-main)]'
              : 'bg-[var(--bg-card)] border border-[var(--border-subtle)]'
          }`}
          title={wsConnected ? 'WebSocket live stream connected' : 'Client Simulation Engine active'}
        >
          <span className={`w-2 h-2 rounded-none ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-emerald-500'} shrink-0`} />
          <span className="font-mono text-[10px] text-[var(--text-muted)] whitespace-nowrap">
            {wsConnected ? 'LIVE WS' : 'SIMULATION'}
          </span>
        </div>
      </div>
    </header>

      {/* Live DB Connection Modal */}
      <ConnectionModal isOpen={isConnectOpen} onClose={() => setIsConnectOpen(false)} />

      {/* OS Concurrency & Pipeline Audit Log Modal */}
      <AuditLogModal isOpen={isAuditOpen} onClose={() => setIsAuditOpen(false)} />
    </>
  );
};
