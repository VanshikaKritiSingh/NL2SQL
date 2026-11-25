// src/shared/TopBar.tsx — GitHub Primer IDE Top Bar (48px)
import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Database,
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
  Cpu,
  Layers,
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
  const selectedModel = useAppStore((s) => s.selectedModel);
  const setSelectedModel = useAppStore((s) => s.setSelectedModel);

  const [tempUserName, setTempUserName] = useState(userId);
  const [userSaved, setUserSaved] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isConnectOpen, setIsConnectOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [dbStatus, setDbStatus] = useState<{ connected: boolean; database?: string; connector_type?: string } | null>(null);
  const [models, setModels] = useState<string[]>([]);

  const settingsButtonRef = useRef<HTMLButtonElement>(null);
  const [settingsPos, setSettingsPos] = useState({ top: 54, right: 14 });
  const settingsRef = useRef<HTMLDivElement>(null);
  const schema = useSchemaStore((s) => s.schema);
  const schemaVersion = useSchemaStore((s) => s.schemaVersion);
  const updateSchema = useSchemaStore((s) => s.updateSchema);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const databaseProfile = useAppStore((s) => s.databaseProfile);

  useEffect(() => { setTempUserName(userId); }, [userId]);

  // Load available Ollama models from the backend
  useEffect(() => {
    apiFetch<any>('/connections/models')
      .then((d) => {
        const list: string[] = Array.isArray(d?.models) ? d.models
          : Array.isArray(d) ? d : [];
        setModels(list);
      })
      .catch(() => setModels([]));
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isSettingsOpen) setIsSettingsOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSettingsOpen]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        settingsRef.current && !settingsRef.current.contains(e.target as Node) &&
        settingsButtonRef.current && !settingsButtonRef.current.contains(e.target as Node)
      ) setIsSettingsOpen(false);
    };
    if (isSettingsOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isSettingsOpen]);

  useEffect(() => {
    const dialect = dbStatus?.connector_type || (targetDialect === 'auto' ? 'mysql' : targetDialect);
    getLiveSchema(userId, dialect).then(updateSchema).catch(() => {});
  }, [userId, schemaVersion, dbStatus?.connected, dbStatus?.connector_type, targetDialect]);

  useEffect(() => {
    const updatePosition = () => {
      if (settingsButtonRef.current) {
        const rect = settingsButtonRef.current.getBoundingClientRect();
        setSettingsPos({ top: rect.bottom + 6, right: Math.max(14, window.innerWidth - rect.right) });
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
      setDbStatus({ connected, database: data?.database, connector_type: data?.connector_type });
      setIsDbConnected(connected);
      if (connected) {
        if (data.connector_type) setConnectedEngine(data.connector_type);
        if (data.database && databaseProfile !== '__none__') setDatabaseProfile(data.database);
        if (Array.isArray(data.databases) && data.databases.length > 0) setAvailableDatabases(data.databases);
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

  useEffect(() => { checkDbStatus(); }, [userId, isConnectOpen, schemaVersion]);

  const handleDetachDirect = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiFetch<any>(`/connections/${encodeURIComponent(userId)}`, { method: 'DELETE' });
      setDbStatus({ connected: false });
      setIsDbConnected(false);
      setConnectedEngine(null);
      setAvailableDatabases([]);
      setDatabaseProfile('__none__');
    } catch { /* ignore */ }
  };

  const handleUserSave = () => {
    const trimmed = tempUserName.trim();
    if (trimmed) {
      setUserId(trimmed);
      setUserSaved(true);
      setTimeout(() => setUserSaved(false), 2000);
    } else setTempUserName(userId);
  };

  const isDark = theme === 'dark';

  // Primer control classes
  const ctrlBtn =
    'h-[30px] px-[10px] rounded-[6px] border font-medium text-[12.5px] inline-flex items-center gap-[6px] cursor-pointer transition-colors select-none ' +
    'border-[var(--border-hairline)] bg-[var(--bg-canvas)] text-[var(--text-main)] hover:bg-[var(--bg-hover)]';

  const tabCls = (active: boolean) =>
    `relative h-full px-[10px] text-[12.5px] font-medium cursor-pointer bg-transparent border-0 border-b-2 transition-colors flex items-center gap-1.5 ${
      active
        ? 'text-[var(--text-heading)] font-semibold border-b-[var(--accent-primary)]'
        : 'text-[var(--text-recessive)] border-b-transparent hover:text-[var(--text-heading)]'
    }`;

  return (
    <>
      <header className="h-12 shrink-0 flex items-stretch border-b border-[var(--border-hairline)] bg-[var(--bg-panel)] relative z-20">
        {/* ---- Left: brand (no logo icon) + conditional approval tab ---- */}
        <div className="flex items-stretch min-w-0">
          <div className="flex items-center px-3.5 pr-3.5 border-r border-[var(--border-hairline)] shrink-0 font-bold text-[14.5px] tracking-[-0.015em] text-[var(--text-heading)] select-none">
            NL2SQL
          </div>

          {Boolean(approvalPayload) && (
            <nav aria-label="Workspace Views" className="flex items-stretch pl-1">
              <button
                onClick={() => setCurrentView('query')}
                className={tabCls(currentView === 'query')}
                title="Query Intake Studio"
              >
                <Terminal className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Query Studio</span>
              </button>

              <button
                onClick={() => setCurrentView('approval')}
                className={tabCls(currentView === 'approval')}
                title="Review and approve pending database mutations"
              >
                <ShieldAlert className="w-3.5 h-3.5 text-[var(--danger)]" aria-hidden="true" />
                <span className="text-[var(--danger)]">Approval Gate</span>
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--danger)] shrink-0 animate-pulse" aria-hidden="true" />
              </button>
            </nav>
          )}
        </div>

        {/* ---- Middle: DB status pill + model selector ---- */}
        <div className="flex-1 min-w-0 flex items-center gap-2 px-3 overflow-hidden">
          <button
            onClick={() => { setIsSettingsOpen(false); setIsConnectOpen(true); }}
            className={ctrlBtn + ' shrink-0 max-w-[260px]'}
            title={dbStatus?.connected ? 'Live database attached. Click to manage.' : 'No database attached. Click to connect.'}
          >
            <span
              className={`w-[7px] h-[7px] rounded-full shrink-0 ${
                dbStatus?.connected ? 'bg-[var(--success)]' : 'bg-[var(--text-recessive)]'
              }`}
              aria-hidden="true"
            />
            <span className="font-mono text-[12px] truncate">
              {dbStatus?.connected
                ? `${dbStatus.connector_type?.toUpperCase() || 'DB'}:${databaseProfile === '__none__' ? 'scratch' : dbStatus.database || 'test'}`
                : 'No Database'}
            </span>
          </button>

          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            aria-label="Select LLM Model"
            className="h-[30px] pl-[10px] pr-[22px] rounded-[6px] border border-[var(--border-hairline)] bg-[var(--bg-canvas)] text-[var(--text-main)] font-mono text-[12px] cursor-pointer shrink-0 max-w-[240px] focus:outline-2 focus:outline-[var(--accent-primary)] focus:outline-offset-[-1px]"
            title="Local Ollama model used for SQL generation"
          >
            <option value="auto">Model: auto (first available)</option>
            {models.map((m) => (
              <option key={m} value={m}>{`Model: ${m}`}</option>
            ))}
            {models.length === 0 && <option value="qwen2.5-coder:7b">Model: qwen2.5-coder:7b</option>}
          </select>

          {dbStatus?.connected && (
            <button
              onClick={handleDetachDirect}
              className={ctrlBtn + ' shrink-0 !text-[var(--danger)]'}
              title="Detach live database socket"
            >
              <Unlink className="w-3.5 h-3.5" aria-hidden="true" />
              <span className="hidden lg:inline">Detach</span>
            </button>
          )}
        </div>

        {/* ---- Right: diagnostics, theme, settings ---- */}
        <div className="flex items-center gap-2 px-3 shrink-0 border-l border-[var(--border-hairline)]">
          <button
            onClick={() => setIsAuditOpen(true)}
            className={ctrlBtn}
            title="System logs & OS concurrency audit trail"
          >
            <Activity className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="hidden xl:inline">Logs</span>
          </button>

          <button
            onClick={toggleTheme}
            className={ctrlBtn + ' !px-[8px]'}
            title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="w-3.5 h-3.5" aria-hidden="true" /> : <Moon className="w-3.5 h-3.5" aria-hidden="true" />}
          </button>

          <button
            ref={settingsButtonRef}
            onClick={() => setIsSettingsOpen((p) => !p)}
            className={
              ctrlBtn +
              (isSettingsOpen
                ? ' !border-[var(--accent-primary)] !text-[var(--accent-primary)] !bg-[var(--accent-soft)]'
                : '')
            }
            title="Settings: connection, dialect, identity, accent"
            aria-expanded={isSettingsOpen}
            aria-haspopup="dialog"
          >
            <Settings className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="hidden lg:inline">Settings</span>
          </button>

          {/* Settings popover — portaled so it never clips (DA-19) */}
          {isSettingsOpen && typeof document !== 'undefined' && createPortal(
            <div
              ref={settingsRef}
              role="dialog"
              aria-label="Settings and System Options"
              style={{ position: 'fixed', top: `${settingsPos.top}px`, right: `${settingsPos.right}px` }}
              className="w-[360px] max-w-[calc(100vw-28px)] rounded-[8px] border border-[var(--border-hairline)] bg-[var(--bg-canvas)] shadow-[var(--shadow-md)] z-[200] overflow-hidden"
            >
              <div className="px-3.5 py-2.5 bg-[var(--bg-panel)] border-b border-[var(--border-hairline)] flex items-center justify-between">
                <span className="font-semibold text-[13px] text-[var(--text-heading)]">Settings &amp; Options</span>
                <button
                  onClick={() => setIsSettingsOpen(false)}
                  className="h-6 px-2 rounded-[6px] border border-[var(--border-hairline)] bg-[var(--bg-canvas)] text-[11px] text-[var(--text-body)] hover:bg-[var(--bg-hover)] cursor-pointer"
                  aria-label="Close settings"
                >
                  Close
                </button>
              </div>

              <div className="flex flex-col">
                {/* Connection */}
                <section className="px-3.5 py-3 border-b border-[var(--border-subtle)]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[var(--text-recessive)]">
                      Database Connection
                    </span>
                    <span className="font-mono text-[11px] text-[var(--text-recessive)] truncate max-w-[160px]">
                      {dbStatus?.connected
                        ? `${dbStatus.connector_type || 'db'}:${databaseProfile === '__none__' ? 'scratch' : dbStatus.database || 'test'}`
                        : 'disconnected'}
                    </span>
                  </div>
                  <button
                    onClick={() => { setIsSettingsOpen(false); setIsConnectOpen(true); }}
                    className="w-full h-8 rounded-[6px] border border-[var(--accent-primary)] bg-[var(--accent-primary)] text-white text-[12.5px] font-semibold cursor-pointer inline-flex items-center justify-center gap-1.5 hover:brightness-110"
                  >
                    <Link2 className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>{dbStatus?.connected ? 'Manage / Switch Database' : 'Connect Live Database'}</span>
                  </button>
                </section>

                {/* Diagnostics */}
                <section className="px-3.5 py-3 border-b border-[var(--border-subtle)]">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[var(--text-recessive)] block mb-2">
                    System Activity
                  </span>
                  <button
                    onClick={() => { setIsSettingsOpen(false); setIsAuditOpen(true); }}
                    className="w-full p-2.5 rounded-[6px] border border-[var(--border-hairline)] bg-[var(--bg-panel)] hover:bg-[var(--bg-hover)] text-left flex items-center justify-between cursor-pointer transition-colors group"
                  >
                    <div className="flex items-center gap-2.5">
                      <Activity className="w-4 h-4 text-[var(--accent-primary)] shrink-0" aria-hidden="true" />
                      <div className="min-w-0">
                        <span className="font-semibold text-[12px] text-[var(--text-heading)] block">System Logs</span>
                        <span className="text-[11px] text-[var(--text-recessive)] block truncate">
                          Pipeline events &amp; concurrency audit
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-[var(--text-recessive)] shrink-0" aria-hidden="true" />
                  </button>
                </section>

                {/* Preferences */}
                <section className="px-3.5 py-3 border-b border-[var(--border-subtle)] flex flex-col gap-3">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[var(--text-recessive)]">
                    Preferences
                  </span>

                  <div className="flex flex-col gap-1">
                    <label className="text-[11.5px] font-medium text-[var(--text-body)]">Target DBMS Dialect</label>
                    <DialectSelector />
                  </div>

                  <div className="flex flex-col gap-1">
                    <label htmlFor="settings-user-input" className="text-[11.5px] font-medium text-[var(--text-body)]">
                      User Identity
                    </label>
                    <div className="flex items-center gap-1.5 h-8 px-2.5 rounded-[6px] border border-[var(--border-hairline)] bg-[var(--bg-inset)]">
                      <User className="w-3.5 h-3.5 text-[var(--text-recessive)] shrink-0" aria-hidden="true" />
                      <input
                        id="settings-user-input"
                        type="text"
                        value={tempUserName}
                        onChange={(e) => setTempUserName(e.target.value)}
                        onBlur={handleUserSave}
                        onKeyDown={(e) => { if (e.key === 'Enter') handleUserSave(); }}
                        className="bg-transparent font-mono text-[12px] focus:outline-none w-full text-[var(--text-main)]"
                        placeholder="User id..."
                      />
                      <button
                        type="button"
                        onClick={handleUserSave}
                        className="text-[var(--accent-primary)] text-[11px] font-semibold shrink-0 cursor-pointer"
                      >
                        {userSaved ? <Check className="w-3.5 h-3.5 text-[var(--success)]" aria-hidden="true" /> : 'Save'}
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 pt-2 border-t border-[var(--border-subtle)]">
                    <div className="flex items-center justify-between">
                      <span className="text-[11.5px] font-medium text-[var(--text-body)]">Accent Color</span>
                      <span className="text-[10px] font-mono font-bold text-[var(--accent-primary)] uppercase">
                        {ACCENT_PALETTES.find((p) => p.id === accentColor)?.name || 'Blue'}
                      </span>
                    </div>
                    <div className="grid grid-cols-6 gap-1.5">
                      {ACCENT_PALETTES.map((acc) => {
                        const isSelected = acc.id === accentColor;
                        return (
                          <button
                            key={acc.id}
                            type="button"
                            onClick={() => setAccentColor(acc.id)}
                            title={`${acc.name} accent`}
                            className={`flex flex-col items-center justify-center gap-1 p-1.5 rounded-[6px] border cursor-pointer transition-colors ${
                              isSelected
                                ? 'border-[var(--accent-primary)] bg-[var(--accent-soft)]'
                                : 'border-[var(--border-hairline)] hover:bg-[var(--bg-hover)]'
                            }`}
                          >
                            <span
                              className="w-3.5 h-3.5 rounded-full border border-black/20 flex items-center justify-center"
                              style={{ backgroundColor: acc.hex }}
                            >
                              {isSelected && <Check className="w-2 h-2 text-white stroke-[3]" />}
                            </span>
                            <span className="text-[9px] font-mono text-[var(--text-recessive)] truncate max-w-full">
                              {acc.name.slice(0, 4)}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </section>

                {/* Engine status */}
                <div className="px-3.5 py-2.5 flex items-center justify-between text-[11.5px]">
                  <span className="text-[var(--text-recessive)]">Engine Connection</span>
                  <span className="font-mono text-[10px] inline-flex items-center gap-1.5">
                    <span
                      className={`w-[7px] h-[7px] rounded-full ${wsConnected ? 'bg-[var(--success)]' : 'bg-[var(--warning)]'}`}
                      aria-hidden="true"
                    />
                    <span className="text-[var(--text-body)]">{wsConnected ? 'LIVE WEBSOCKET' : 'OFFLINE'}</span>
                  </span>
                </div>
              </div>
            </div>,
            document.body
          )}
        </div>
      </header>

      <ConnectionModal isOpen={isConnectOpen} onClose={() => setIsConnectOpen(false)} />
      <AuditLogModal isOpen={isAuditOpen} onClose={() => setIsAuditOpen(false)} />
    </>
  );
};
