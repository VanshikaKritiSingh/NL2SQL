// src/shared/ConnectionModal.tsx
import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Database, X, CheckCircle2, AlertCircle, RefreshCw, Unlink, Link2, Server, Download, Package, Info, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { apiFetch } from '../api/client';

interface ConnectionStatus {
  connected: boolean;
  connector_type?: string;
  database?: string;
  host?: string;
  message?: string;
  databases?: string[];
  tables?: string[];
}

interface ConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface DepStatus {
  package: string;
  installed: boolean;
  version?: string | null;
}

const CONNECTOR_TYPES = [
  { id: 'sqlite', label: 'SQLite (File or :memory:)', defaultDb: ':memory:', defaultPort: '', needsCreds: false },
  { id: 'duckdb', label: 'DuckDB (In-Memory OLAP)', defaultDb: ':memory:', defaultPort: '', needsCreds: false },
  { id: 'postgres', label: 'PostgreSQL', defaultDb: 'postgres', defaultPort: '5432', needsCreds: true },
  { id: 'mysql', label: 'MySQL / MariaDB', defaultDb: 'mysql', defaultPort: '3306', needsCreds: true },
  { id: 'clickhouse', label: 'ClickHouse', defaultDb: 'default', defaultPort: '8123', needsCreds: true },
  { id: 'mongodb', label: 'MongoDB', defaultDb: 'admin', defaultPort: '27017', needsCreds: true },
  { id: 'neo4j', label: 'Neo4j Graph', defaultDb: 'neo4j', defaultPort: '7687', needsCreds: true },
  { id: 'cassandra', label: 'Apache Cassandra', defaultDb: 'system', defaultPort: '9042', needsCreds: true },
];

// Instructions on how to find port number and server for each engine
const PORT_INSTRUCTIONS: Record<string, { port: string; howToFind: string; serverHint: string }> = {
  sqlite: {
    port: 'N/A (embedded)',
    howToFind: 'SQLite is an embedded file-based database — no server or port is needed. Just provide the file path or use `:memory:` for in-memory.',
    serverHint: 'No server required. Use `:memory:` or a file path like `C:\\data\\mydb.sqlite`.',
  },
  duckdb: {
    port: 'N/A (embedded)',
    howToFind: 'DuckDB is an in-process OLAP engine — no server or port is needed. Use `:memory:` for in-memory analytics or a `.duckdb` file path.',
    serverHint: 'No server required. Use `:memory:` or a file path like `./analytics.duckdb`.',
  },
  postgres: {
    port: '5432 (default)',
    howToFind: 'Run `SHOW port;` inside psql, or check `postgresql.conf` for the `port` setting. On Windows, check Services → postgresql-x64-XX → Properties → Path for `--port`. On Linux: `ss -tlnp | grep postgres`.',
    serverHint: 'Use `127.0.0.1` for local installs, or the IP/hostname of your PostgreSQL server. Cloud: use the endpoint from AWS RDS / Azure / GCP console.',
  },
  mysql: {
    port: '3306 (default)',
    howToFind: 'Run `SHOW VARIABLES LIKE \'port\';` in MySQL CLI. Or check `my.ini` / `my.cnf` for the `port` setting. On Windows: open Services → MySQL/MariaDB → check startup parameters. On Linux: `ss -tlnp | grep mysql`.',
    serverHint: 'Use `127.0.0.1` for local MySQL/MariaDB installs (XAMPP, WAMP, standalone). Remote: use the server IP or cloud endpoint.',
  },
  clickhouse: {
    port: '8123 (HTTP) / 9000 (Native)',
    howToFind: 'Check `config.xml` for `<http_port>` (default 8123) or `<tcp_port>` (default 9000). Run `SELECT value FROM system.settings WHERE name = \'http_port\'` in ClickHouse client.',
    serverHint: 'Use `127.0.0.1` for local installs. This connector uses the HTTP API (port 8123 by default).',
  },
  mongodb: {
    port: '27017 (default)',
    howToFind: 'Check `mongod.conf` for `net.port`. Run `db.serverStatus().connections` in mongosh. On Windows: check Services → MongoDB Server → startup params. On Linux: `ss -tlnp | grep mongod`.',
    serverHint: 'Use `127.0.0.1` for local MongoDB. For Atlas: use the connection string hostname from your cluster dashboard.',
  },
  neo4j: {
    port: '7687 (Bolt protocol)',
    howToFind: 'Check `neo4j.conf` for `server.bolt.listen_address` (port 7687). The Neo4j Browser runs on port 7474 (HTTP) but the Bolt driver uses 7687.',
    serverHint: 'Use `127.0.0.1` for local Neo4j Desktop/Community. For Aura: use the `neo4j+s://` connection URI from your Aura console.',
  },
  cassandra: {
    port: '9042 (CQL native transport)',
    howToFind: 'Check `cassandra.yaml` for `native_transport_port` (default 9042). Run `nodetool status` to see nodes. On Linux: `ss -tlnp | grep 9042`.',
    serverHint: 'Use `127.0.0.1` for local Cassandra. For multi-node clusters, provide any seed node IP.',
  },
};

export const ConnectionModal: React.FC<ConnectionModalProps> = ({ isOpen, onClose }) => {
  const userId = useAppStore((s) => s.userId);
  const theme = useAppStore((s) => s.theme);
  const setIsDbConnected = useAppStore((s) => s.setIsDbConnected);
  const setConnectedEngine = useAppStore((s) => s.setConnectedEngine);
  const setDatabaseProfile = useAppStore((s) => s.setDatabaseProfile);
  const setAvailableDatabases = useAppStore((s) => s.setAvailableDatabases);
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
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

  // Direct SQL execution on selected database
  const [directSql, setDirectSql] = useState('');
  const [isExecutingSql, setIsExecutingSql] = useState(false);
  const [sqlResult, setSqlResult] = useState<any>(null);

  // Install Dependencies state
  const [isInstallingDeps, setIsInstallingDeps] = useState(false);
  const [depStatus, setDepStatus] = useState<{ allInstalled: boolean; packages: DepStatus[]; message?: string } | null>(null);
  const [isCheckingDeps, setIsCheckingDeps] = useState(false);

  // Port/Server instructions collapsible
  const [showInstructions, setShowInstructions] = useState(false);

  const currentInfo = PORT_INSTRUCTIONS[connectorType] || PORT_INSTRUCTIONS['mysql'];
  const currentConnectorMeta = CONNECTOR_TYPES.find((c) => c.id === connectorType);

  // ── Check Dependencies on connector change ──
  const checkDeps = async (ct?: string) => {
    const targetType = ct || connectorType;
    setIsCheckingDeps(true);
    try {
      const res = await apiFetch<any>(`/connections/check-deps/${encodeURIComponent(targetType)}`);
      setDepStatus({
        allInstalled: res.all_installed,
        packages: res.packages || [],
        message: res.message,
      });
    } catch {
      setDepStatus(null);
    } finally {
      setIsCheckingDeps(false);
    }
  };

  // ── Install Dependencies ──
  const handleInstallDeps = async () => {
    setIsInstallingDeps(true);
    setFeedback(null);
    try {
      const res = await apiFetch<any>('/connections/install-deps', {
        method: 'POST',
        body: JSON.stringify({ connector_type: connectorType }),
      });
      if (res.ok) {
        setFeedback({
          type: 'success',
          message: res.message || `Dependencies installed for ${connectorType}`,
        });
        // Re-check deps
        await checkDeps();
      } else {
        setFeedback({
          type: 'error',
          message: res.message || 'Dependency installation failed.',
        });
      }
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Failed to install dependencies' });
    } finally {
      setIsInstallingDeps(false);
    }
  };

  const handleSwitchDatabase = async (newDb: string) => {
    setDatabase(newDb);
    setDatabaseProfile(newDb);
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
        setIsDbConnected(true);
        if (data.connector_type) setConnectedEngine(data.connector_type);
        if (data.database) {
          setDatabase(data.database);
          setDatabaseProfile(data.database);
        }
        if (Array.isArray(data.databases) && data.databases.length > 0) {
          setAvailableDbs(data.databases);
          setAvailableDatabases(data.databases);
        }
        await fetchSchemaTables();
        await fetchDatabases();
      } else {
        setIsDbConnected(false);
        setConnectedEngine(null);
      }
    } catch {
      setStatus({ connected: false });
      setIsDbConnected(false);
      setConnectedEngine(null);
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
      checkDeps();
      // Auto-fetch databases if using mysql on localhost
      if (connectorType === 'mysql' && availableDbs.length === 0) {
        fetchDatabases();
      }
    }
  }, [isOpen, userId]);

  const handleTypeChange = (type: string) => {
    setConnectorType(type);
    setAvailableDbs([]);
    setDepStatus(null);
    const found = CONNECTOR_TYPES.find((c) => c.id === type);
    if (found) {
      setDatabase(found.defaultDb);
      setPort(found.defaultPort);
    }
    checkDeps(type);
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

  // ── One-Click Setup: Install Deps → Test → Attach ──
  const handleOneClickSetup = async () => {
    setIsLoading(true);
    setFeedback({ type: 'info', message: 'Step 1/3: Installing dependencies...' });

    try {
      // Step 1: Install dependencies
      const depRes = await apiFetch<any>('/connections/install-deps', {
        method: 'POST',
        body: JSON.stringify({ connector_type: connectorType }),
      });
      if (!depRes.ok && !depRes.already_installed) {
        setFeedback({ type: 'error', message: `Dependency install failed: ${depRes.message}` });
        setIsLoading(false);
        return;
      }
      await checkDeps();

      // Step 2: Test connection
      setFeedback({ type: 'info', message: 'Step 2/3: Testing connection...' });
      const testPayload: any = {
        connector_type: connectorType,
        database: database.trim(),
        host: host.trim() || undefined,
        port: port ? parseInt(port, 10) : undefined,
        username: username.trim() || undefined,
        password: password || undefined,
      };
      const testRes = await apiFetch<any>('/connections/test', {
        method: 'POST',
        body: JSON.stringify(testPayload),
      });
      if (testRes && testRes.ok === false) {
        setFeedback({ type: 'error', message: `Connection test failed: ${testRes.error || 'Unknown error'}` });
        setIsLoading(false);
        return;
      }

      // Step 3: Attach socket
      setFeedback({ type: 'info', message: 'Step 3/3: Attaching live database socket...' });
      const attachPayload: any = {
        user_id: userId,
        connector_type: connectorType,
        database: database.trim(),
        host: host.trim() || undefined,
        port: port ? parseInt(port, 10) : undefined,
        username: username.trim() || undefined,
        password: password || undefined,
      };
      const attachRes = await apiFetch<any>('/connections/attach', {
        method: 'POST',
        body: JSON.stringify(attachPayload),
      });
      if (attachRes && attachRes.ok === false) {
        setFeedback({ type: 'error', message: `Socket attach failed: ${attachRes.error || 'Unknown error'}` });
        setIsLoading(false);
        return;
      }

      setFeedback({
        type: 'success',
        message: `✓ All done! Dependencies installed, connection verified, and socket attached to ${connectorType.toUpperCase()} [${database}].`,
      });
      await fetchStatus();
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'One-click setup failed' });
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const modalBg = isDark
    ? 'bg-[#181824] text-white border-white/20 shadow-black/80'
    : 'bg-white text-slate-900 border-slate-300 shadow-2xl';
  const inputBg = isDark ? 'bg-[#12121A]' : 'bg-[#F4F6F9]';
  const inputBorder = isDark ? 'border-white/15' : 'border-slate-300';
  const muted = isDark ? 'text-slate-400' : 'text-slate-500';
  const mutedHover = isDark ? 'hover:text-white' : 'hover:text-slate-900';
  const labelClass = isDark ? 'text-slate-300' : 'text-slate-600';
  const sectionBorder = isDark ? 'border-white/12' : 'border-slate-200';
  const successBg = isDark ? 'bg-emerald-950/50 border-emerald-500/50 text-emerald-300' : 'bg-emerald-50 border-emerald-300 text-emerald-800';
  const errorBg = isDark ? 'bg-rose-950/50 border-rose-500/50 text-rose-300' : 'bg-rose-50 border-rose-300 text-rose-800';
  const infoBg = isDark ? 'bg-indigo-950/50 border-indigo-500/50 text-indigo-300' : 'bg-indigo-50 border-indigo-300 text-indigo-800';

  return createPortal(
    <div className="modal-overlay bg-black/80 backdrop-blur-sm animate-fade-in">
      <div
        className={`w-full max-w-2xl border rounded-none shadow-2xl p-6 transition-all overflow-y-auto max-h-[calc(100vh-48px)] my-auto ${modalBg}`}
      >
        {/* Connection Steps Escort Hint Box */}
        <div className={`mb-4 p-3.5 rounded-none border text-[11px] font-mono leading-snug shadow-sm ${
          isDark
            ? 'bg-[#1E1E2C] border-white/12 text-slate-300'
            : 'bg-[#F1F3F8] border-slate-300 text-slate-700'
        }`}>
          <div className="font-bold text-[var(--accent-primary)] mb-1.5 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> How to Connect to Your Database
          </div>
          <ol className="list-decimal list-inside space-y-1 pl-1">
            <li><strong>1.</strong> Select connector type (PostgreSQL / MySQL / SQLite / DuckDB / etc.).</li>
            <li><strong>2.</strong> Click <strong>Install Dependencies</strong> to auto-install the required Python driver.</li>
            <li><strong>3.</strong> Enter host, port, database name, username, and password.</li>
            <li><strong>4.</strong> Click <strong>Test Connection</strong> to verify socket handshake, then <strong>Attach Socket</strong> to bind.</li>
            <li><strong>5.</strong> Or use <strong>⚡ One-Click Setup</strong> to do all steps automatically!</li>
          </ol>
        </div>

        {/* Header */}
        <div className={`flex items-center justify-between pb-3 border-b ${sectionBorder}`}>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 flex items-center justify-center bg-indigo-600/20 text-indigo-400">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight">Myspire — Live DBMS Socket Connector</h2>
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
          {/* Target Engine Selector */}
          <div>
            <label className={`block text-[11px] font-semibold ${muted} mb-1`}>Target Engine:</label>
            <select
              value={connectorType}
              onChange={(e) => handleTypeChange(e.target.value)}
              className={`w-full px-3 py-2 border rounded-none focus:outline-none focus:ring-1 focus:ring-[#8E94F2] focus:border-[#8E94F2] font-mono text-xs ${inputBg} ${inputBorder} ${isDark ? 'text-white' : 'text-slate-900'}`}
            >
              {CONNECTOR_TYPES.map((c) => (
                <option key={c.id} value={c.id} className={isDark ? 'bg-[#181824] text-white' : 'bg-white text-slate-900'}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* ── Install Dependencies Section ── */}
          <div className={`p-3.5 border rounded-none ${isDark ? 'bg-[#1E1E2C] border-white/12' : 'bg-[#F8FAFC] border-slate-300'}`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Package className="w-3.5 h-3.5 text-indigo-400" />
                <span className="text-[11px] font-semibold text-[var(--text-secondary)]">
                  Python Driver Dependencies
                </span>
              </div>
              <div className="flex items-center gap-2">
                {isCheckingDeps && <Loader2 className="w-3 h-3 animate-spin text-indigo-400" />}
                {depStatus && (
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-none ${
                    depStatus.allInstalled
                      ? isDark
                        ? 'bg-emerald-950/60 border border-emerald-500/40 text-emerald-300'
                        : 'bg-emerald-50 border border-emerald-300 text-emerald-700'
                      : isDark
                        ? 'bg-amber-950/60 border border-amber-500/40 text-amber-300'
                        : 'bg-amber-50 border border-amber-300 text-amber-700'
                  }`}>
                    {depStatus.allInstalled ? '✓ Ready' : '⚠ Missing'}
                  </span>
                )}
              </div>
            </div>

            {/* Package status list */}
            {depStatus && depStatus.packages.length > 0 && (
              <div className="mb-2 space-y-1">
                {depStatus.packages.map((p) => (
                  <div
                    key={p.package}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-none text-[10px] font-mono border ${
                      p.installed
                        ? isDark
                          ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                          : 'bg-emerald-50 border-emerald-200 text-emerald-700'
                        : isDark
                          ? 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                          : 'bg-rose-50 border-rose-200 text-rose-700'
                    }`}
                  >
                    <span>📦 {p.package}</span>
                    <span>{p.installed ? `v${p.version || '?'}` : 'Not installed'}</span>
                  </div>
                ))}
              </div>
            )}

            {depStatus && !depStatus.allInstalled && depStatus.packages.length > 0 && (
              <span className={`block text-[10px] mb-2 ${muted}`}>
                {depStatus.message}
              </span>
            )}

            {depStatus && depStatus.packages.length === 0 && (
              <span className={`block text-[10px] mb-2 text-[var(--success)]`}>
                {depStatus.message || `${connectorType} uses built-in libraries — no external packages needed.`}
              </span>
            )}

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleInstallDeps}
                disabled={isInstallingDeps || (depStatus?.allInstalled === true)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold border cursor-pointer transition-all ${
                  depStatus?.allInstalled
                    ? 'bg-[var(--success-bg)] border-[var(--success)] text-[var(--success)] opacity-70 cursor-default'
                    : 'bg-indigo-600/20 border-indigo-500/50 text-indigo-300 hover:bg-indigo-600/30'
                }`}
              >
                {isInstallingDeps ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Download className="w-3.5 h-3.5" />
                )}
                {isInstallingDeps
                  ? 'Installing...'
                  : depStatus?.allInstalled
                    ? 'All Installed ✓'
                    : 'Install Dependencies'}
              </button>
              <button
                type="button"
                onClick={() => checkDeps()}
                disabled={isCheckingDeps}
                className={`p-1.5 border cursor-pointer transition-colors ${inputBg} ${inputBorder} ${muted} ${mutedHover}`}
                title="Re-check dependency status"
              >
                <RefreshCw className={`w-3 h-3 ${isCheckingDeps ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* ── How to Find Port & Server — Collapsible Instructions ── */}
          <div className={`border rounded-none overflow-hidden ${inputBorder}`}>
            <button
              type="button"
              onClick={() => setShowInstructions(!showInstructions)}
              className={`w-full flex items-center justify-between px-3 py-2 text-[11px] font-semibold cursor-pointer transition-colors ${
                isDark ? 'bg-[var(--bg-card-header)] hover:bg-[var(--bg-subtle)]' : 'bg-[var(--bg-card-header)] hover:bg-[var(--bg-subtle)]'
              } text-[var(--text-secondary)]`}
            >
              <div className="flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-indigo-400" />
                <span>How to Find Your Port Number & Server Address</span>
              </div>
              {showInstructions ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
            {showInstructions && (
              <div className={`px-3 py-2.5 text-[10px] font-mono leading-relaxed ${inputBg} text-[var(--text-secondary)] space-y-2`}>
                <div>
                  <span className="font-bold text-[var(--accent-primary)]">Default Port:</span>{' '}
                  <span className="text-[var(--text-main)]">{currentInfo.port}</span>
                </div>
                <div>
                  <span className="font-bold text-[var(--accent-primary)]">How to find your port:</span>
                  <p className="mt-0.5 text-[var(--text-muted)] whitespace-pre-wrap">{currentInfo.howToFind}</p>
                </div>
                <div>
                  <span className="font-bold text-[var(--accent-primary)]">Server / Host:</span>
                  <p className="mt-0.5 text-[var(--text-muted)] whitespace-pre-wrap">{currentInfo.serverHint}</p>
                </div>
                <div className={`mt-2 p-2 rounded-none border text-[9px] ${
                  isDark ? 'bg-slate-900/50 border-slate-700/50 text-slate-400' : 'bg-amber-50 border-amber-200 text-amber-800'
                }`}>
                  💡 <strong>Quick Reference — Default Ports:</strong>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 mt-1">
                    <span>MySQL / MariaDB: <strong>3306</strong></span>
                    <span>PostgreSQL: <strong>5432</strong></span>
                    <span>ClickHouse (HTTP): <strong>8123</strong></span>
                    <span>MongoDB: <strong>27017</strong></span>
                    <span>Neo4j (Bolt): <strong>7687</strong></span>
                    <span>Cassandra (CQL): <strong>9042</strong></span>
                    <span>Redis: <strong>6379</strong></span>
                    <span>SQLite / DuckDB: <strong>N/A</strong></span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Host & Port */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={`block text-[11px] font-semibold ${labelClass} mb-1`}>Server / Host:</label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="127.0.0.1 or hostname"
                className={`w-full px-3 py-2 border rounded-none font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[#8E94F2] focus:border-[#8E94F2] ${
                  isDark
                    ? 'bg-[#12121A] border-white/15 text-white placeholder-slate-500'
                    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
                }`}
              />
            </div>
            <div>
              <label className={`block text-[11px] font-semibold ${labelClass} mb-1`}>Port:</label>
              <input
                type="text"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder={currentInfo.port.split(' ')[0] || 'Optional'}
                className={`w-full px-3 py-2 border rounded-none font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[#8E94F2] focus:border-[#8E94F2] ${
                  isDark
                    ? 'bg-[#12121A] border-white/15 text-white placeholder-slate-500'
                    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
                }`}
              />
            </div>
          </div>

          {/* Database / Path */}
          <div>
            <label className={`block text-[11px] font-semibold ${labelClass} mb-1`}>
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
                  className={`w-full px-3 py-2 border rounded-none focus:outline-none focus:ring-1 focus:ring-[#8E94F2] focus:border-[#8E94F2] font-mono text-xs ${
                    isDark
                      ? 'bg-[#12121A] border-white/15 text-white'
                      : 'bg-white border-slate-300 text-slate-900'
                  }`}
                >
                  {availableDbs.map((d) => (
                    <option key={d} value={d} className={isDark ? 'bg-[#181824] text-white' : 'bg-white text-slate-900'}>
                      {d}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={fetchDatabases}
                  disabled={isFetchingDbs}
                  title="Re-list accessible databases"
                  className={`shrink-0 p-2 border rounded-none cursor-pointer transition-colors ${
                    isDark
                      ? 'bg-[#1E1E2C] border-white/15 text-slate-300 hover:text-white hover:bg-white/10'
                      : 'bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200'
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
                className={`w-full px-3 py-2 border rounded-none font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[#8E94F2] focus:border-[#8E94F2] ${
                  isDark
                    ? 'bg-[#12121A] border-white/15 text-white placeholder-slate-500'
                    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
                }`}
              />
            )}
          </div>

          {/* Username & Password */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={`block text-[11px] font-semibold ${labelClass} mb-1`}>Username:</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={currentConnectorMeta?.needsCreds ? 'Required' : 'Optional'}
                className={`w-full px-3 py-2 border rounded-none font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[#8E94F2] focus:border-[#8E94F2] ${
                  isDark
                    ? 'bg-[#12121A] border-white/15 text-white placeholder-slate-500'
                    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
                }`}
              />
            </div>
            <div>
              <label className={`block text-[11px] font-semibold ${labelClass} mb-1`}>Password:</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={currentConnectorMeta?.needsCreds ? 'Required' : 'Optional'}
                className={`w-full px-3 py-2 border rounded-none font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[#8E94F2] focus:border-[#8E94F2] ${
                  isDark
                    ? 'bg-[#12121A] border-white/15 text-white placeholder-slate-500'
                    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
                }`}
              />
            </div>
          </div>
        </div>

        {/* Tables Preview (after attach) */}
        {status.connected && (
          <div className="mt-3">
            <label className={`block text-[11px] font-semibold ${labelClass} mb-1`}>
              Accessible Tables in [{database}] ({tables.length}):
            </label>
            {tables.length > 0 ? (
              <div
                className={`max-h-36 overflow-y-auto px-3 py-2 border rounded-none font-mono text-[10px] ${
                  isDark
                    ? 'bg-[#12121A] border-white/15 text-slate-200'
                    : 'bg-white border-slate-300 text-slate-800'
                }`}
              >
                {tables.map((t) => (
                  <div key={t} className={`py-0.5 ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>
                    • {t}
                  </div>
                ))}
              </div>
            ) : (
              <div className={`p-2.5 border rounded-none font-mono text-[11px] ${
                isDark
                  ? 'bg-[#12121A] border-white/15 text-slate-400'
                  : 'bg-white border-slate-300 text-slate-500'
              }`}>
                Database '{database}' has no tables yet. Run CREATE TABLE below to create tables.
              </div>
            )}
          </div>
        )}

        {/* Direct SQL Executor (Make changes to selected DB) */}
        {status.connected && (
          <div className={`mt-3 pt-3 border-t ${sectionBorder}`}>
            <label className="block text-[11px] font-semibold text-emerald-400 mb-1">
              Direct DB Mutation & Changes [{database}]:
            </label>
            <div className="space-y-1.5">
              <textarea
                rows={2}
                value={directSql}
                onChange={(e) => setDirectSql(e.target.value)}
                placeholder="e.g. CREATE TABLE test_table (id INT PRIMARY KEY, name VARCHAR(50)); or INSERT INTO ...;"
                className={`w-full px-2.5 py-1.5 border rounded-none font-mono text-xs focus:outline-none focus:border-[#8E94F2] focus:ring-1 focus:ring-[#8E94F2] ${
                  isDark
                    ? 'bg-[#12121A] border-white/15 text-white placeholder-slate-500'
                    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
                }`}
              />
              <div className="flex items-center justify-between">
                <span className={`text-[10px] font-mono ${muted}`}>
                  Direct DDL / DML / Query executor
                </span>
                <button
                  type="button"
                  onClick={handleExecuteDirect}
                  disabled={isExecutingSql || !directSql.trim()}
                  className="px-3 py-1 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer border border-emerald-500 transition-colors rounded-none"
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
              feedback.type === 'success' ? successBg : feedback.type === 'info' ? infoBg : errorBg
            }`}
          >
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : feedback.type === 'info' ? (
              <Loader2 className="w-4 h-4 shrink-0 animate-spin" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
        )}

        {/* Bottom Actions */}
        <div className="mt-5 flex items-center justify-between gap-2.5 pt-3 border-t border-[var(--border-subtle)]">
          {/* One-Click Setup button (left side) */}
          <button
            onClick={handleOneClickSetup}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-bold border cursor-pointer transition-all bg-gradient-to-r from-indigo-600/30 to-violet-600/30 border-indigo-500/50 text-indigo-200 hover:from-indigo-600/50 hover:to-violet-600/50 shadow-md"
            title="Auto-install dependencies, test connection, and attach socket in one click"
          >
            <Download className="w-3.5 h-3.5" />
            <span>⚡ One-Click Setup</span>
          </button>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleTest}
              disabled={isLoading}
              className={`px-3 py-1.5 text-xs font-semibold border cursor-pointer transition-colors ${
                isDark
                  ? 'bg-[#1E1E2C] border-white/15 text-white hover:bg-white/10'
                  : 'bg-slate-100 border-slate-300 text-slate-800 hover:bg-slate-200'
              }`}
            >
              <RefreshCw className={`w-3.5 h-3.5 inline mr-1 ${isLoading ? 'animate-spin' : ''}`} />
              Test Connection
            </button>
            <button
              onClick={handleAttach}
              disabled={isLoading}
              className="px-4 py-1.5 text-xs font-semibold bg-[#8E94F2] hover:bg-[#7D84EE] text-slate-950 font-bold cursor-pointer shadow-md transition-colors flex items-center gap-1.5"
            >
              <Link2 className="w-3.5 h-3.5" />
              <span>Attach Socket</span>
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};
