// src/shared/TopBar.tsx
import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Database,
  Table,
  User,
  Sun,
  Moon,
  Check,
  Link2,
  Unlink,
  Activity,
  Settings,
  X,
  ChevronRight,
  Terminal,
  ShieldAlert,
} from 'lucide-react';
import { useAppStore, ACCENT_PALETTES } from '../store/useAppStore';
import { useQueryStore } from '../store/useQueryStore';
import { usePipelineStore } from '../store/usePipelineStore';
import { DialectSelector } from './DialectSelector';
import { ConnectionModal } from './ConnectionModal';
import { AuditLogModal } from './AuditLogModal';
import { useSchemaStore } from '../store/useSchemaStore';
import { getLiveSchema } from '../api/schemaApi';
import { apiFetch } from '../api/client';

export const TopBar: React.FC = () => {
  const userId = useAppStore((s) => s.userId);
  const setUserId = useAppStore((s) => s.setUserId);
  const currentView = useAppStore((s) => s.currentView);
  const setCurrentView = useAppStore((s) => s.setCurrentView);
  const rightPanelTab = useAppStore((s) => s.rightPanelTab);
  const setRightPanelTab = useAppStore((s) => s.setRightPanelTab);
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const wsConnected = usePipelineStore((s) => s.wsConnected);
  const approvalPayload = useQueryStore((s) => s.approvalPayload);
  const setIsDbConnected = useAppStore((s) => s.setIsDbConnected);
  const setConnectedEngine = useAppStore((s) => s.setConnectedEngine);
  const setDatabaseProfile = useAppStore((s) => s.setDatabaseProfile);
  const setAvailableDatabases = useAppStore((s) => s.setAvailableDatabases);
  const accentColor = useAppStore((s) => s.accentColor);
  const setAccentColor = useAppStore((s) => s.setAccentColor);

  const [tempUserName, setTempUserName] = useState(userId);
  const [userSaved, setUserSaved] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isConnectOpen, setIsConnectOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [dbStatus, setDbStatus] = useState<{ connected: boolean; database?: string; connector_type?: string } | null>(null);

  const settingsButtonRef = useRef<HTMLButtonElement>(null);
  const [settingsPos, setSettingsPos] = useState({ top: 48, right: 16 });
  const settingsRef = useRef<HTMLDivElement>(null);
  const schema = useSchemaStore((s) => s.schema);
  const schemaVersion = useSchemaStore((s) => s.schemaVersion);
  const updateSchema = useSchemaStore((s) => s.updateSchema);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const databaseProfile = useAppStore((s) => s.databaseProfile);

  // Sync temp user name when userId changes in store
  useEffect(() => {
    setTempUserName(userId);
  }, [userId]);

  // Close settings on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isSettingsOpen) {
        setIsSettingsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSettingsOpen]);

  // Close settings on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        settingsRef.current &&
        !settingsRef.current.contains(e.target as Node) &&
        settingsButtonRef.current &&
        !settingsButtonRef.current.contains(e.target as Node)
      ) {
        setIsSettingsOpen(false);
      }
    };
    if (isSettingsOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isSettingsOpen]);

  useEffect(() => {
    const dialect = dbStatus?.connector_type || (targetDialect === 'auto' ? 'mysql' : targetDialect);
    getLiveSchema(userId, dialect).then(updateSchema).catch(() => {});
  }, [userId, schemaVersion, dbStatus?.connected, dbStatus?.connector_type, targetDialect]);

  // Update settings popover coordinates when opening or window resizing (DA-19)
  useEffect(() => {
    const updatePosition = () => {
      if (settingsButtonRef.current) {
        const rect = settingsButtonRef.current.getBoundingClientRect();
        setSettingsPos({
          top: rect.bottom + 6,
          right: Math.max(16, window.innerWidth - rect.right),
        });
      }
    };
    if (isSettingsOpen) {
      updatePosition();
      window.addEventListener('resize', updatePosition);
      window.addEventListener('scroll', updatePosition, true);
    }
    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
    };
  }, [isSettingsOpen]);

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
        if (data.database && databaseProfile !== '__none__') setDatabaseProfile(data.database);
        if (Array.isArray(data.databases) && data.databases.length > 0) {
          setAvailableDatabases(data.databases);
        }
      } else {
        setConnectedEngine(null);
        setAvailableDatabases([]);
        if (databaseProfile !== '__none__') setDatabaseProfile('__none__');
      }
    } catch {
      setDbStatus({ connected: false });
      setIsDbConnected(false);
      setConnectedEngine(null);
      setAvailableDatabases([]);
      if (databaseProfile !== '__none__') setDatabaseProfile('__none__');
    }
  };

  useEffect(() => {
    checkDbStatus();
  }, [userId, isConnectOpen, schemaVersion]);

  const handleDetachDirect = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiFetch<any>(`/connections/${encodeURIComponent(userId)}`, { method: 'DELETE' });
      setDbStatus({ connected: false });
      setIsDbConnected(false);
      setConnectedEngine(null);
      setAvailableDatabases([]);
      setDatabaseProfile('__none__');
    } catch {
      // Ignore
    }
  };

  const handleUserSave = () => {
    const trimmed = tempUserName.trim();
    if (trimmed) {
      setUserId(trimmed);
      setUserSaved(true);
      setTimeout(() => setUserSaved(false), 2000);
    } else {
      setTempUserName(userId);
    }
  };

  const isDark = theme === 'dark';

  return (
    <>
      <header
        className="min-h-12 h-12 border-b px-3 sm:px-5 flex items-center justify-between shrink-0 transition-colors duration-200 relative z-20 gap-3 bg-[var(--bg-header)] backdrop-blur-2xl border-[var(--border-hairline)] text-[var(--text-main)]"
      >
        {/* Left: Brand Icon & Navigation Tabs */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <div
            className="w-8 h-8 rounded-[var(--radius-control)] shrink-0 flex items-center justify-center bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] shadow-sm"
            title="NL2SQL Studio"
          >
            <Database className="w-4 h-4" aria-hidden="true" />
          </div>

          {/* Navigation Tabs — Query Studio with Segmented Results/ER Ghost Slider, and Approval Gate */}
          <nav
            aria-label="Primary Navigation"
            className={`flex items-center gap-1 p-1 rounded-[var(--radius-pill)] text-xs shrink-0 whitespace-nowrap border ${
              isDark ? 'bg-[var(--bg-canvas)] border-[var(--border-hairline)]' : 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)]'
            }`}
          >
            {/* Query Studio Navigation Button */}
            <button
              onClick={() => setCurrentView('query')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-pill)] font-medium transition-colors duration-200 cursor-pointer shrink-0 whitespace-nowrap ${
                currentView === 'query'
                  ? 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] shadow-sm'
                  : 'text-[var(--text-recessive)] hover:text-[var(--text-heading)]'
              }`}
              title="Query Intake Studio"
            >
              <Terminal className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Query Studio</span>
            </button>

            {/* Ghost Slider Selector: Results vs ER Schema */}
            <div className="relative inline-flex items-center p-0.5 rounded-[var(--radius-pill)] bg-[var(--bg-card)] border border-[var(--border-subtle)] shadow-inner">
              <button
                onClick={() => {
                  if (currentView !== 'query') setCurrentView('query');
                  setRightPanelTab('results');
                }}
                className={`relative z-10 flex items-center gap-1 px-2.5 py-1 rounded-[var(--radius-pill)] text-[11px] font-semibold transition-all duration-200 cursor-pointer ${
                  rightPanelTab === 'results' && currentView === 'query'
                    ? 'text-[var(--text-heading)]'
                    : 'text-[var(--text-recessive)] hover:text-[var(--text-heading)]'
                }`}
                title="View Execution Results Output"
              >
                <Table className="w-3 h-3" />
                <span>Results</span>
              </button>

              <button
                onClick={() => {
                  if (currentView !== 'query') setCurrentView('query');
                  setRightPanelTab('er_diagram');
                }}
                className={`relative z-10 flex items-center gap-1 px-2.5 py-1 rounded-[var(--radius-pill)] text-[11px] font-semibold transition-all duration-200 cursor-pointer ${
                  rightPanelTab === 'er_diagram' && currentView === 'query'
                    ? 'text-[var(--text-heading)]'
                    : 'text-[var(--text-recessive)] hover:text-[var(--text-heading)]'
                }`}
                title="View Interactive ER Schema Graph"
              >
                <Database className="w-3 h-3" />
                <span>ER Schema</span>
                {schema && schema.tables.length > 0 && (
                  <span className="text-[9px] px-1 py-0.2 rounded-full bg-[var(--border-hairline)] text-[var(--text-body)] font-mono">
                    {schema.tables.length}
                  </span>
                )}
              </button>

              {/* Ghost Slider Indicator */}
              {currentView === 'query' && (
                <div
                  className={`absolute top-0.5 bottom-0.5 rounded-[var(--radius-pill)] bg-[var(--bg-panel-alt)] border border-[var(--border-hairline)] shadow-xs transition-all duration-300 pointer-events-none ${
                    rightPanelTab === 'results' ? 'left-0.5 w-[calc(50%-2px)]' : 'left-[50%] w-[calc(50%-2px)]'
                  }`}
                />
              )}
            </div>

            {/* Approval Gate Tab (Visible if approval view or pending payload) */}
            {(currentView === 'approval' || Boolean(approvalPayload)) && (
              <button
                onClick={() => setCurrentView('approval')}
                className={`flex items-center gap-1.5 px-3 sm:px-4 py-1.5 rounded-[var(--radius-pill)] font-medium transition-colors duration-200 cursor-pointer shrink-0 whitespace-nowrap ${
                  currentView === 'approval'
                    ? 'bg-rose-600 text-white shadow-sm'
                    : 'text-[var(--text-recessive)] hover:text-rose-400 hover:bg-rose-500/10'
                }`}
                title="Review and approve pending database mutations"
              >
                <ShieldAlert className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Approval Gate</span>
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              </button>
            )}
          </nav>
        </div>

        {/* Right: Active DB pill, Theme Toggle & Unified Settings Option */}
        <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 whitespace-nowrap relative">
          {/* Quick Active DB Status Chip (visible only when a live database is attached) */}
          {dbStatus?.connected && (
            <button
              onClick={() => {
                setIsSettingsOpen(false);
                setIsConnectOpen(true);
              }}
              className="hidden sm:flex items-center gap-1.5 rounded-[var(--radius-pill)] px-2.5 py-1 text-xs font-mono shrink-0 whitespace-nowrap border border-[var(--success)]/30 bg-[var(--success-bg)] text-[var(--success)] hover:opacity-90 cursor-pointer transition-opacity"
              title="Live Database Connected. Click to configure or switch database."
            >
              <span className="w-2 h-2 rounded-full bg-[var(--success)] shrink-0" aria-hidden="true" />
              <span>
                {dbStatus.connector_type?.toUpperCase() || 'MYSQL'}: <strong className="font-semibold">{databaseProfile === '__none__' ? 'SCRATCH' : (dbStatus.database || 'test')}</strong>
              </span>
            </button>
          )}

          {/* Quick Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-[var(--radius-pill)] transition-colors duration-200 cursor-pointer shrink-0 bg-[var(--bg-card)] border border-[var(--border-hairline)] text-[var(--text-recessive)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-heading)]"
            title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="w-4 h-4" aria-hidden="true" /> : <Moon className="w-4 h-4" aria-hidden="true" />}
          </button>

          {/* Unified Settings Option Button */}
          <button
            ref={settingsButtonRef}
            onClick={() => setIsSettingsOpen((prev) => !prev)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-pill)] text-xs font-medium cursor-pointer transition-colors duration-200 shrink-0 whitespace-nowrap border ${
              isSettingsOpen
                ? 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] border-[var(--btn-primary-bg)] shadow-sm'
                : 'bg-[var(--bg-card)] border-[var(--border-hairline)] text-[var(--text-main)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-heading)]'
            }`}
            title="Settings: Connect DB, System Logs, Dialect & Accent"
            aria-expanded={isSettingsOpen}
            aria-haspopup="dialog"
          >
            <Settings className={`w-3.5 h-3.5 transition-transform duration-200 ${isSettingsOpen ? 'rotate-45' : ''}`} aria-hidden="true" />
            <span>Settings</span>
          </button>

          {/* Unified Settings Popover / Dropdown Menu rendered via Portal to prevent clipping (DA-19) */}
          {isSettingsOpen && typeof document !== 'undefined' && createPortal(
            <div
              ref={settingsRef}
              role="dialog"
              aria-label="Settings and System Options"
              style={{
                position: 'fixed',
                top: `${settingsPos.top}px`,
                right: `${settingsPos.right}px`,
              }}
              className="w-[340px] sm:w-[400px] rounded-[var(--radius-panel)] border border-[var(--border-hairline)] bg-[var(--bg-card)] shadow-2xl z-[200] overflow-hidden flex flex-col text-xs transition-colors duration-200 animate-in fade-in zoom-in-95"
            >
              {/* Settings Header */}
              <div className="px-4 py-3 border-b border-[var(--border-hairline)] flex items-center justify-between bg-[var(--bg-panel-alt)]/50">
                <div className="flex items-center gap-2">
                  <Settings className="w-4 h-4 text-[var(--accent-primary)]" aria-hidden="true" />
                  <h3 className="font-semibold text-sm text-[var(--text-heading)]">Settings & Options</h3>
                </div>
                <button
                  onClick={() => setIsSettingsOpen(false)}
                  className="p-1 rounded-[var(--radius-pill)] text-[var(--text-recessive)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-hover)] cursor-pointer"
                  aria-label="Close settings"
                >
                  <X className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>

              {/* Settings Body */}
              <div className="p-4 flex flex-col gap-4 max-h-[80vh] overflow-y-auto">
                {/* 1. Database Connection */}
                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] font-semibold tracking-wider uppercase text-[var(--text-recessive)]">
                    Database Connection
                  </span>
                  <div className="p-3 rounded-[var(--radius-control)] border border-[var(--border-hairline)] bg-[var(--bg-canvas)] flex flex-col gap-2.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${dbStatus?.connected ? 'bg-[var(--success)]' : 'bg-[var(--text-recessive)]'} shrink-0`} aria-hidden="true" />
                        <span className="font-medium text-[var(--text-heading)] truncate max-w-[200px]">
                          {dbStatus?.connected
                            ? `${dbStatus.connector_type?.toUpperCase() || 'DB'}: ${databaseProfile === '__none__' ? 'SCRATCH' : (dbStatus.database || 'test')}`
                            : 'No Database Connected'}
                        </span>
                      </div>
                      {dbStatus?.connected && (
                        <button
                          onClick={handleDetachDirect}
                          className="text-[11px] text-[var(--danger)] hover:underline flex items-center gap-1 cursor-pointer"
                          title="Detach live database"
                        >
                          <Unlink className="w-3 h-3" aria-hidden="true" />
                          <span>Detach</span>
                        </button>
                      )}
                    </div>
                    <button
                      onClick={() => {
                        setIsSettingsOpen(false);
                        setIsConnectOpen(true);
                      }}
                      className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-[var(--radius-pill)] bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] font-medium text-xs hover:opacity-90 transition-opacity cursor-pointer shadow-sm"
                    >
                      <Link2 className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>{dbStatus?.connected ? 'Manage Connection / Switch DB' : 'Connect Live Database'}</span>
                    </button>
                  </div>
                </div>

                {/* 2. System Diagnostics & Activity Logs */}
                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] font-semibold tracking-wider uppercase text-[var(--text-recessive)]">
                    System Activity
                  </span>
                  <button
                    onClick={() => {
                      setIsSettingsOpen(false);
                      setIsAuditOpen(true);
                    }}
                    className="p-3 rounded-[var(--radius-control)] border border-[var(--border-hairline)] bg-[var(--bg-canvas)] hover:border-[var(--accent-primary)]/40 hover:bg-[var(--bg-hover)] text-left flex items-center justify-between transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-[var(--radius-control)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]">
                        <Activity className="w-4 h-4" aria-hidden="true" />
                      </div>
                      <div>
                        <span className="font-semibold text-xs text-[var(--text-heading)] group-hover:text-[var(--accent-primary)] block">
                          System Logs
                        </span>
                        <span className="text-[11px] text-[var(--text-recessive)] block">
                          Pipeline events & git-style branch execution trace
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-[var(--text-recessive)] group-hover:text-[var(--accent-primary)] transition-colors" aria-hidden="true" />
                  </button>
                </div>

                {/* 3. Query Preferences & Dialect */}
                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] font-semibold tracking-wider uppercase text-[var(--text-recessive)]">
                    Preferences & Dialect
                  </span>
                  <div className="p-3 rounded-[var(--radius-control)] border border-[var(--border-hairline)] bg-[var(--bg-canvas)] flex flex-col gap-3">
                    {/* Target Dialect */}
                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] font-medium text-[var(--text-recessive)]">Target DBMS Dialect</label>
                      <DialectSelector />
                    </div>

                    {/* User Identity */}
                    <div className="flex flex-col gap-1">
                      <label htmlFor="settings-user-input" className="text-[11px] font-medium text-[var(--text-recessive)]">User Identity</label>
                      <div className="flex items-center gap-1.5 border border-[var(--border-hairline)] rounded-[var(--radius-pill)] px-3 py-1.5 bg-[var(--bg-card)]">
                        <User className="w-3.5 h-3.5 text-[var(--text-recessive)] shrink-0" aria-hidden="true" />
                        <input
                          id="settings-user-input"
                          type="text"
                          value={tempUserName}
                          onChange={(e) => setTempUserName(e.target.value)}
                          onBlur={handleUserSave}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleUserSave();
                          }}
                          className="bg-transparent font-mono text-xs focus:outline-none w-full text-[var(--text-heading)]"
                          placeholder="Enter user name..."
                        />
                        <button
                          type="button"
                          onClick={handleUserSave}
                          className="text-[var(--accent-primary)] text-[11px] font-medium hover:underline cursor-pointer shrink-0"
                        >
                          {userSaved ? <Check className="w-3.5 h-3.5 text-[var(--success)]" aria-hidden="true" /> : 'Save'}
                        </button>
                      </div>
                    </div>

                    {/* Accent Color Selection (Replaced Redundant Theme Toggle) */}
                    <div className="flex flex-col gap-2 pt-2 border-t border-[var(--border-hairline)]">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-medium text-[var(--text-recessive)]">Accent Color</span>
                        <span className="text-[10px] font-mono font-bold text-[var(--accent-primary)] uppercase">
                          {ACCENT_PALETTES.find((p) => p.id === accentColor)?.name || 'Violet'}
                        </span>
                      </div>
                      <div className="grid grid-cols-6 gap-2 pt-1">
                        {ACCENT_PALETTES.map((acc) => {
                          const isSelected = acc.id === accentColor;
                          return (
                            <button
                              key={acc.id}
                              type="button"
                              onClick={() => setAccentColor(acc.id)}
                              title={`${acc.name} Accent`}
                              className={`group relative flex flex-col items-center justify-center p-1.5 rounded-[var(--radius-control)] border transition-all cursor-pointer ${
                                isSelected
                                  ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/15 scale-105 shadow-sm'
                                  : 'border-[var(--border-hairline)] hover:border-[var(--text-recessive)] bg-[var(--bg-card)]'
                              }`}
                            >
                              <span
                                className="w-4 h-4 rounded-full border border-black/20 dark:border-white/20 shadow-xs flex items-center justify-center transition-transform group-hover:scale-110"
                                style={{ backgroundColor: acc.hex }}
                              >
                                {isSelected && (
                                  <Check className="w-2.5 h-2.5 text-white stroke-[3]" />
                                )}
                              </span>
                              <span className="text-[9px] font-mono mt-1 text-[var(--text-recessive)] group-hover:text-[var(--text-heading)] truncate max-w-full">
                                {acc.name.slice(0, 4)}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>

                {/* 4. Engine & Status */}
                <div className="flex items-center justify-between px-1 text-[11px] text-[var(--text-recessive)]">
                  <span>Engine Connection</span>
                  <div className="flex items-center gap-1.5 font-mono text-[10px]">
                    <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-[var(--success)]' : 'bg-[var(--success)]'} shrink-0`} aria-hidden="true" />
                    <span>{wsConnected ? 'LIVE WEBSOCKET' : 'CLIENT SIMULATION'}</span>
                  </div>
                </div>
              </div>
            </div>,
            document.body
          )}
        </div>
      </header>

      {/* Live DB Connection Modal */}
      <ConnectionModal isOpen={isConnectOpen} onClose={() => setIsConnectOpen(false)} />

      {/* OS Concurrency & Pipeline Audit Log Modal */}
      <AuditLogModal isOpen={isAuditOpen} onClose={() => setIsAuditOpen(false)} />
    </>
  );
};
