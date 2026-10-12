// src/shared/ConnectionModal.tsx
import React, { useState, useEffect } from 'react';
import { Database, X, CheckCircle2, AlertCircle, RefreshCw, Unlink, Link2, Server } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { apiFetch } from '../api/client';

interface ConnectionStatus {
  connected: boolean;
  connector_type?: string;
  database?: string;
  host?: string;
  message?: string;
}

interface ConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const CONNECTOR_TYPES = [
  { id: 'sqlite', label: 'SQLite (File or :memory:)', defaultDb: ':memory:', defaultPort: '' },
  { id: 'duckdb', label: 'DuckDB (In-Memory OLAP)', defaultDb: ':memory:', defaultPort: '' },
  { id: 'postgres', label: 'PostgreSQL', defaultDb: 'postgres', defaultPort: '5432' },
  { id: 'mysql', label: 'MySQL / MariaDB', defaultDb: 'mysql', defaultPort: '3306' },
  { id: 'clickhouse', label: 'ClickHouse', defaultDb: 'default', defaultPort: '8123' },
  { id: 'mongodb', label: 'MongoDB', defaultDb: 'admin', defaultPort: '27017' },
  { id: 'neo4j', label: 'Neo4j Graph', defaultDb: 'neo4j', defaultPort: '7687' },
  { id: 'cassandra', label: 'Apache Cassandra', defaultDb: 'system', defaultPort: '9042' },
];

export const ConnectionModal: React.FC<ConnectionModalProps> = ({ isOpen, onClose }) => {
  const userId = useAppStore((s) => s.userId);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const [status, setStatus] = useState<ConnectionStatus>({ connected: false });
  const [connectorType, setConnectorType] = useState('mysql');
  const [database, setDatabase] = useState('test');
  const [host, setHost] = useState('127.0.0.1');
  const [port, setPort] = useState('3306');
  const [username, setUsername] = useState('bhuknu');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [availableDbs, setAvailableDbs] = useState<string[]>([]);
  const [isFetchingDbs, setIsFetchingDbs] = useState(false);
  const [tables, setTables] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Direct SQL execution on selected database
  const [directSql, setDirectSql] = useState('');
  const [isExecutingSql, setIsExecutingSql] = useState(false);
  const [sqlResult, setSqlResult] = useState<any>(null);

  const handleSwitchDatabase = async (newDb: string) => {
    setDatabase(newDb);
    if (!status.connected) return;
    setIsLoading(true);
    setFeedback(null);
    try {
      const res = await apiFetch<any>('/connections/switch-database', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, database: newDb }),
      });
      if (res && res.ok) {
        setFeedback({ type: 'success', message: `Active database switched to '${newDb}'` });
        await fetchStatus();
      }
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Failed to switch database' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleExecuteDirect = async () => {
    if (!directSql.trim()) return;
    setIsExecutingSql(true);
    setSqlResult(null);
    try {
      const res = await apiFetch<any>('/connections/execute', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, query: directSql }),
      });
      setSqlResult(res);
      if (res.ok) {
        const aff = res.is_mutating ? `${res.rows_affected} rows affected` : `${res.row_count} rows returned`;
        setFeedback({ type: 'success', message: `Query executed on '${database}': ${aff} in ${res.execution_time_ms}ms` });
        await fetchSchemaTables();
      } else {
        setFeedback({ type: 'error', message: res.error || 'Direct SQL execution failed' });
      }
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Failed to execute query' });
    } finally {
      setIsExecutingSql(false);
    }
  };

  const fetchSchemaTables = async () => {
    try {
      const schemaData = await apiFetch<any>(`/connections/schema/${encodeURIComponent(userId)}`);
      if (schemaData && schemaData.tables) {
        setTables(Object.keys(schemaData.tables));
      }
    } catch {
      setTables([]);
    }
  };

  const fetchStatus = async () => {
    try {
      const data = await apiFetch<ConnectionStatus>(`/connections/status/${encodeURIComponent(userId)}`);
      setStatus(data);
      if (data.connected) {
        await fetchSchemaTables();
        await fetchDatabases();
      }
    } catch {
      setStatus({ connected: false });
    }
  };

  const fetchDatabases = async () => {
    setIsFetchingDbs(true);
    setFeedback(null);
    try {
      const payload: any = {
        connector_type: connectorType,
        host: host.trim() || undefined,
        port: port ? parseInt(port, 10) : undefined,
        username: username.trim() || undefined,
        password: password || undefined,
      };
      const res = await apiFetch<any>('/connections/databases', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (res && res.databases && Array.isArray(res.databases)) {
        setAvailableDbs(res.databases);
        if (res.databases.length > 0 && !res.databases.includes(database)) {
          const preferred =
            res.databases.find(
              (d: string) =>
                d !== 'information_schema' && d !== 'sys' && d !== 'mysql' && d !== 'performance_schema'
            ) || res.databases[0];
          setDatabase(preferred);
        }
        setFeedback({
          type: 'success',
          message: `Authenticated successfully! Found ${res.databases.length} accessible database(s) for user '${
            username || 'current user'
          }'.`,
        });
      }
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Failed to authenticate and list databases' });
    } finally {
      setIsFetchingDbs(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      setFeedback(null);
      // Auto-fetch databases if using mysql on localhost
      if (connectorType === 'mysql' && availableDbs.length === 0) {
        fetchDatabases();
      }
    }
  }, [isOpen, userId]);

  const handleTypeChange = (type: string) => {
    setConnectorType(type);
    setAvailableDbs([]);
    const found = CONNECTOR_TYPES.find((c) => c.id === type);
    if (found) {
      setDatabase(found.defaultDb);
      setPort(found.defaultPort);
    }
  };

  const handleTest = async () => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const payload: any = {
        connector_type: connectorType,
        database: database.trim(),
        host: host.trim() || undefined,
        port: port ? parseInt(port, 10) : undefined,
        username: username.trim() || undefined,
        password: password || undefined,
      };
      const res = await apiFetch<any>('/connections/test', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (res && res.ok === false) {
        setFeedback({ type: 'error', message: res.error || 'Connection test failed' });
      } else {
        const ver = res?.version ? ` (${res.version})` : '';
        const lat = res?.latency_ms != null ? ` in ${res.latency_ms}ms` : '';
        setFeedback({
          type: 'success',
          message: `Connected successfully to ${res?.dialect || connectorType}${ver}${lat}`,
        });
      }
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Connection test failed' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAttach = async () => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const payload: any = {
        user_id: userId,
        connector_type: connectorType,
        database: database.trim(),
        host: host.trim() || undefined,
        port: port ? parseInt(port, 10) : undefined,
        username: username.trim() || undefined,
        password: password || undefined,
      };
      const res = await apiFetch<any>('/connections/attach', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (res && res.ok === false) {
        setFeedback({ type: 'error', message: res.error || 'Failed to attach database socket' });
      } else {
        setFeedback({ type: 'success', message: res?.message || 'Live database socket attached!' });
        await fetchStatus();
      }
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Failed to attach database socket' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDetach = async () => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const res = await apiFetch<any>(`/connections/${encodeURIComponent(userId)}`, {
        method: 'DELETE',
      });
      setFeedback({ type: 'success', message: res.message || 'Database socket disconnected.' });
      setTables([]);
      await fetchStatus();
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Failed to detach database socket' });
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const modalBg = 'bg-[var(--bg-card)] text-[var(--text-main)] border-[var(--border-main)]';
  const inputBg = 'bg-[var(--bg-input)]';
  const inputBorder = 'border-[var(--border-subtle)]';
  const muted = 'text-[var(--text-muted)]';
  const mutedHover = 'hover:text-[var(--text-main)]';
  const sectionBorder = 'border-[var(--border-subtle)]';
  const successBg = 'bg-[var(--success-bg)] border-[var(--success)] text-[var(--success)]';
  const errorBg = 'bg-[var(--danger-bg)] border-[var(--danger)] text-[var(--danger)]';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div
        className={`w-full max-w-lg border shadow-2xl p-6 transition-all ${modalBg}`}
      >
        {/* Connection Steps Escort Hint Box */}
        <div className="mb-4 p-3 rounded-xl border text-[11px] font-mono leading-snug bg-[var(--bg-card-header)] border-[var(--border-subtle)] text-[var(--text-secondary)] shadow-sm">
          <div className="font-bold text-[var(--accent-primary)] mb-1.5 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> How to Connect to Your Database
          </div>
          <ol className="list-decimal list-inside space-y-1 pl-1">
            <li><strong>1.</strong> Select connector type (PostgreSQL / MySQL / SQLite / DuckDB).</li>
            <li><strong>2.</strong> Enter host (127.0.0.1), port (5432 / 3306 / 9000), database name, and credentials.</li>
            <li><strong>3.</strong> Click <strong>Test Connection</strong> to verify socket handshake.</li>
            <li><strong>4.</strong> Once green (Connected), your NL2SQL queries will run live against this DB.</li>
            <li><strong>5.</strong> Use the direct SQL box for manual commands; click <strong>Attach Socket</strong> to bind to pipeline.</li>
          </ol>
        </div>

        {/* Header */}
        <div className={`flex items-center justify-between pb-3 border-b ${sectionBorder}`}>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 flex items-center justify-center bg-indigo-600/20 text-indigo-400">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight">Live DBMS Socket Connector</h2>
              <p className={`text-[11px] ${muted}`}>
                Session: <code className="font-mono text-indigo-400">{userId}</code>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className={`p-1.5 transition-colors cursor-pointer ${muted} ${mutedHover}`}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Status Indicator */}
        <div
          className={`mt-4 p-3 flex items-center justify-between text-xs font-mono border ${
            status.connected ? 'bg-[var(--success-bg)] border-[var(--success)] text-[var(--success)]' : `${inputBg} ${inputBorder} ${muted}`
          }`}
        >
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 inline-block ${status.connected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
            <span>
              {status.connected
                ? `Connected: ${status.connector_type?.toUpperCase()} (${status.database})`
                : 'No live DB socket attached (Sandbox preview active)'}
            </span>
          </div>
          {status.connected && (
            <button
              onClick={handleDetach}
              disabled={isLoading}
              className="text-rose-400 hover:text-rose-300 flex items-center gap-1 font-semibold cursor-pointer text-[11px]"
            >
              <Unlink className="w-3 h-3" />
              <span>Detach</span>
            </button>
          )}
        </div>

      {/* Form Controls */}
        <div className="mt-4 space-y-3 text-xs">
          <div>
            <label className={`block text-[11px] font-semibold ${muted} mb-1`}>Target Engine:</label>
            <select
              value={connectorType}
              onChange={(e) => handleTypeChange(e.target.value)}
              className={`w-full px-3 py-1.5 border focus:outline-none focus:ring-1 focus:ring-indigo-500 ${inputBg} ${inputBorder} ${muted} ${mutedHover}`}
            >
              {CONNECTOR_TYPES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={`block text-[11px] font-semibold ${muted} mb-1`}>Host:</label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="localhost"
                className={`w-full px-3 py-1.5 border font-mono ${inputBg} ${inputBorder} ${muted}`}
              />
            </div>
            <div>
              <label className={`block text-[11px] font-semibold ${muted} mb-1`}>Port:</label>
              <input
                type="text"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="Optional"
                className={`w-full px-3 py-1.5 border font-mono ${inputBg} ${inputBorder} ${muted}`}
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">
              Database / Path:
            </label>
            {availableDbs.length > 0 ? (
              <div className="flex items-center gap-2">
                <select
                  value={database}
                  onChange={(e) => {
                    if (status.connected) {
                      handleSwitchDatabase(e.target.value);
                    } else {
                      setDatabase(e.target.value);
                    }
                  }}
                  className={`w-full px-3 py-1.5 border focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono ${
                    inputBg} ${inputBorder} ${muted}
                  }`}
                >
                  {availableDbs.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={fetchDatabases}
                  disabled={isFetchingDbs}
                  title="Re-list accessible databases"
                  className={`shrink-0 p-1.5 border cursor-pointer transition-colors ${
                    inputBg} ${inputBorder} ${muted} ${mutedHover}
                  }`}
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isFetchingDbs ? 'animate-spin' : ''}`} />
                </button>
              </div>
            ) : (
              <input
                type="text"
                value={database}
                onChange={(e) => setDatabase(e.target.value)}
                placeholder=":memory: or catalog name"
                className={`w-full px-3 py-1.5 border font-mono ${
                  inputBg} ${inputBorder} ${muted}
                }`}
              />
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={`block text-[11px] font-semibold ${muted} mb-1`}>Username (optional):</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className={`w-full px-3 py-1.5 border font-mono ${inputBg} ${inputBorder} ${muted}`}
              />
            </div>
            <div>
              <label className={`block text-[11px] font-semibold ${muted} mb-1`}>Password (optional):</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`w-full px-3 py-1.5 border font-mono ${inputBg} ${inputBorder} ${muted}`}
              />
            </div>
          </div>
        </div>

        {/* Tables Preview (after attach) */}
        {status.connected && (
          <div className="mt-3">
            <label className={`block text-[11px] font-semibold ${muted} mb-1`}>
              Accessible Tables in [{database}] ({tables.length}):
            </label>
            {tables.length > 0 ? (
              <div
                className={`max-h-36 overflow-y-auto px-3 py-1.5 border font-mono text-[10px] ${
                  inputBg} ${inputBorder} ${muted}
                `}
              >
                {tables.map((t) => (
                  <div key={t} className="py-0.5 text-slate-200">
                    • {t}
                  </div>
                ))}
              </div>
            ) : (
              <div className={`p-2 border font-mono text-[11px] text-slate-400 ${inputBg} ${inputBorder}`}>
                Database '{database}' has no tables yet. Run CREATE TABLE below to create tables.
              </div>
            )}
          </div>
        )}

        {/* Direct SQL Executor (Make changes to selected DB) */}
        {status.connected && (
          <div className="mt-3 pt-3 border-t border-[#40444C]">
            <label className="block text-[11px] font-semibold text-[#8CEBB0] mb-1">
              Direct DB Mutation & Changes [{database}]:
            </label>
            <div className="space-y-1.5">
              <textarea
                rows={2}
                value={directSql}
                onChange={(e) => setDirectSql(e.target.value)}
                placeholder="e.g. CREATE TABLE test_table (id INT PRIMARY KEY, name VARCHAR(50)); or INSERT INTO ...;"
                className={`w-full px-2.5 py-1.5 border font-mono text-xs ${inputBg} ${inputBorder} text-[#E2E4E9] focus:outline-none`}
              />
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-[#A0A3AE]">
                  Direct DDL / DML / Query executor
                </span>
                <button
                  type="button"
                  onClick={handleExecuteDirect}
                  disabled={isExecutingSql || !directSql.trim()}
                  className="px-3 py-1 text-xs font-semibold bg-[#2E7D4E] hover:bg-[#38825A] text-white cursor-pointer border border-[#3E9E66] transition-colors"
                >
                  {isExecutingSql ? 'Executing...' : `Execute on '${database}'`}
                </button>
              </div>
            </div>
          </div>
        )}

          {/* Feedback message */}
        {feedback && (
          <div
            className={`mt-4 p-2.5 border text-xs flex items-center gap-2 ${
              feedback.type === 'success' ? successBg : errorBg
            }`}
          >
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
        )}

        {/* Bottom Actions */}
        <div className="mt-5 flex items-center justify-end gap-2.5 pt-3 border-t border-[var(--border-subtle)]">
          <button
            onClick={handleTest}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs font-semibold border cursor-pointer transition-colors bg-[var(--bg-card)] border-[var(--border-subtle)] hover:bg-[var(--bg-hover)] text-[var(--text-main)]"
          >
            <RefreshCw className={`w-3.5 h-3.5 inline mr-1 ${isLoading ? 'animate-spin' : ''}`} />
            Test Connection
          </button>
          <button
            onClick={handleAttach}
            disabled={isLoading}
            className="px-4 py-1.5 text-xs font-semibold bg-[var(--accent-primary)] hover:opacity-90 text-white cursor-pointer shadow-md transition-colors flex items-center gap-1.5"
          >
            <Link2 className="w-3.5 h-3.5" />
            <span>Attach Socket</span>
          </button>
        </div>
      </div>
    </div>
  );
};
