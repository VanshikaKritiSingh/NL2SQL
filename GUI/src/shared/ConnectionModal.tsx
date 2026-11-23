// src/shared/ConnectionModal.tsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Database, X, CheckCircle2, AlertCircle, RefreshCw, Unlink, Link2, Server, Download, Package, Info, ChevronDown, ChevronUp, Loader2, Search, Copy, Check, Sparkles, Terminal } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { useSchemaStore } from '../store/useSchemaStore';
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
  { id: 'sqlite', label: 'SQLite (Embedded SQL)', defaultDb: ':memory:', defaultPort: '', needsCreds: false },
  { id: 'postgres', label: 'PostgreSQL (Relational RDBMS)', defaultDb: 'postgres', defaultPort: '5432', needsCreds: true },
  { id: 'mysql', label: 'MySQL / MariaDB (Relational RDBMS)', defaultDb: 'mysql', defaultPort: '3306', needsCreds: true },
  { id: 'duckdb', label: 'DuckDB (In-Memory / File / OLAP Port)', defaultDb: ':memory:', defaultPort: '', needsCreds: true },
  { id: 'clickhouse', label: 'ClickHouse (Columnar OLAP)', defaultDb: 'default', defaultPort: '8123', needsCreds: true },
  { id: 'mongodb', label: 'MongoDB (Document NoSQL)', defaultDb: 'admin', defaultPort: '27017', needsCreds: true },
  { id: 'neo4j', label: 'Neo4j (Graph Database)', defaultDb: 'neo4j', defaultPort: '7687', needsCreds: true },
  { id: 'redis', label: 'Redis (Key-Value Store)', defaultDb: '0', defaultPort: '6379', needsCreds: true },
  { id: 'cassandra', label: 'Apache Cassandra (Wide-Column)', defaultDb: 'system', defaultPort: '9042', needsCreds: true },
  { id: 'custom', label: 'Personal / Custom DBMS (Extensible)', defaultDb: 'main', defaultPort: '5432', needsCreds: true },
];

// Instructions on how to find port number and server for each engine
const PORT_INSTRUCTIONS: Record<string, { port: string; howToFind: string; serverHint: string }> = {
  sqlite: {
    port: 'N/A (embedded)',
    howToFind: 'SQLite is an embedded file-based database — no server or port is needed. Just provide the file path or use `:memory:` for in-memory.',
    serverHint: 'No server required. Use `:memory:` or a file path like `C:\\data\\mydb.sqlite`.',
  },
  duckdb: {
    port: 'Optional (embedded or custom server port)',
    howToFind: 'DuckDB is an in-process OLAP engine — by default no server or port is needed (use `:memory:` or `./analytics.duckdb`). If running behind a DuckDB server daemon or proxy, specify your server port.',
    serverHint: 'Leave Host empty for local in-memory/file mode, or enter `127.0.0.1` / your host if connecting to a network DuckDB endpoint.',
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
  redis: {
    port: '6379 (default)',
    howToFind: 'Check `redis.conf` for `port` (default 6379). Run `redis-cli ping` or `INFO server`. On Linux: `ss -tlnp | grep 6379`.',
    serverHint: 'Use `127.0.0.1` for local Redis. Database number is typically `0` (0-15).',
  },
  cassandra: {
    port: '9042 (CQL native transport)',
    howToFind: 'Check `cassandra.yaml` for `native_transport_port` (default 9042). Run `nodetool status` to see nodes. On Linux: `ss -tlnp | grep 9042`.',
    serverHint: 'Use `127.0.0.1` for local Cassandra. For multi-node clusters, provide any seed node IP.',
  },
  custom: {
    port: 'Custom (e.g. 5432, 3306, 26257, 4000, 27017, 8123)',
    howToFind: 'Check the listening port of your custom database or cloud instance. Most custom/enterprise databases listen on standard wire ports (CockroachDB: 26257, TiDB: 4000, Timescale/Redshift: 5432, MariaDB: 3306).',
    serverHint: 'Provide your custom host IP (e.g. 127.0.0.1) or cloud endpoint URL.',
  },
};

interface DetectiveStep {
  label: string;
  cmd: string;
  hint: string;
}

interface DetectiveTip {
  title: string;
  catchphrase: string;
  steps: DetectiveStep[];
  quickDefaults: {
    host?: string;
    port?: string;
    database?: string;
    username?: string;
    password?: string;
  };
}

const DETECTIVE_TIPS: Record<string, DetectiveTip> = {
  mysql: {
    title: 'MariaDB / MySQL Detective (Linux & Localhost)',
    catchphrase: "Psst! Don't know your database info? Here is how to uncover your Linux MariaDB secrets!",
    steps: [
      {
        label: 'Step 1: Check if MariaDB/MySQL is active',
        cmd: 'sudo systemctl status mariadb || sudo systemctl status mysql',
        hint: 'If stopped, run `sudo systemctl start mariadb` to launch it.',
      },
      {
        label: 'Step 2: Find the active port (Usually 3306)',
        cmd: 'ss -tlnp | grep 3306',
        hint: 'Localhost IP is 127.0.0.1 and standard port is 3306.',
      },
      {
        label: 'Step 3: What is my username? (Linux auth)',
        cmd: 'whoami',
        hint: 'On Linux, MariaDB often permits your current OS username or `root` with no password via unix_socket.',
      },
      {
        label: 'Step 4: Discover all existing databases',
        cmd: 'sudo mariadb -e "SHOW DATABASES;"',
        hint: 'Pick any database from the output (or use `test`), then type it in Database Name.',
      },
      {
        label: 'Step 5: Need a dedicated user with password?',
        cmd: "sudo mariadb -e \"CREATE USER IF NOT EXISTS 'admin'@'127.0.0.1' IDENTIFIED BY 'secret123'; GRANT ALL PRIVILEGES ON *.* TO 'admin'@'127.0.0.1'; FLUSH PRIVILEGES;\"",
        hint: 'Runs in 1 second! Then enter username: admin, password: secret123.',
      },
    ],
    quickDefaults: {
      host: '127.0.0.1',
      port: '3306',
      database: 'test',
      username: 'root',
      password: '',
    },
  },
  postgres: {
    title: 'PostgreSQL Detective',
    catchphrase: 'Aha! Looking for PostgreSQL? Let us inspect your local cluster!',
    steps: [
      {
        label: 'Step 1: Verify PostgreSQL daemon',
        cmd: 'sudo systemctl status postgresql',
        hint: 'Start it with `sudo systemctl start postgresql` if inactive.',
      },
      {
        label: 'Step 2: Check port (Usually 5432)',
        cmd: 'ss -tlnp | grep 5432',
        hint: 'Postgres listens on port 5432 on 127.0.0.1 by default.',
      },
      {
        label: 'Step 3: List databases and superusers',
        cmd: "sudo -u postgres psql -c '\\l'",
        hint: 'Default user is `postgres` and default database is `postgres`.',
      },
      {
        label: 'Step 4: Set a password if needed',
        cmd: "sudo -u postgres psql -c \"ALTER USER postgres WITH PASSWORD 'postgres';\"",
        hint: 'Enables password-based login for user `postgres`.',
      },
    ],
    quickDefaults: {
      host: '127.0.0.1',
      port: '5432',
      database: 'postgres',
      username: 'postgres',
      password: '',
    },
  },
  sqlite: {
    title: 'SQLite Zero-Config Wonder',
    catchphrase: 'No server, no ports, no credentials! 100% effortless!',
    steps: [
      {
        label: 'Instant In-Memory Mode',
        cmd: ':memory:',
        hint: 'Type `:memory:` in Database Name. Zero setup, runs in pure RAM with blazing speed!',
      },
      {
        label: 'Disk File Mode',
        cmd: './my_database.db',
        hint: 'Or enter any local file path on your computer. SQLite will create it automatically!',
      },
    ],
    quickDefaults: {
      host: '',
      port: '',
      database: ':memory:',
      username: '',
      password: '',
    },
  },
  duckdb: {
    title: 'DuckDB In-Process OLAP',
    catchphrase: 'Fast analytical SQL with zero background services!',
    steps: [
      {
        label: 'In-Memory Analytics',
        cmd: ':memory:',
        hint: 'Runs in process without any background daemon. Just click Attach!',
      },
      {
        label: 'Persistent DuckDB Catalog',
        cmd: './analytics.duckdb',
        hint: 'Store your columnar tables in a single local file.',
      },
    ],
    quickDefaults: {
      host: '',
      port: '',
      database: ':memory:',
      username: '',
      password: '',
    },
  },
  clickhouse: {
    title: 'ClickHouse Columnar Detective',
    catchphrase: 'ClickHouse communicates over HTTP port 8123!',
    steps: [
      {
        label: 'Test ClickHouse HTTP ping',
        cmd: 'curl http://localhost:8123/ping',
        hint: 'Should return `Ok.`. Default port is 8123, database is `default`.',
      },
    ],
    quickDefaults: {
      host: '127.0.0.1',
      port: '8123',
      database: 'default',
      username: 'default',
      password: '',
    },
  },
  mongodb: {
    title: 'MongoDB Document Detective',
    catchphrase: 'Uncover your local MongoDB collections and port!',
    steps: [
      {
        label: 'Check mongod service',
        cmd: 'sudo systemctl status mongod || sudo systemctl status mongodb',
        hint: 'Default MongoDB port is 27017 on 127.0.0.1.',
      },
      {
        label: 'List databases in mongosh',
        cmd: 'mongosh --eval "db.adminCommand(\'listDatabases\')"',
        hint: 'Default initial admin database is `admin` or `test`.',
      },
    ],
    quickDefaults: {
      host: '127.0.0.1',
      port: '27017',
      database: 'admin',
      username: '',
      password: '',
    },
  },
  neo4j: {
    title: 'Neo4j Graph Database Detective',
    catchphrase: 'Connecting via the high-speed Bolt protocol on port 7687!',
    steps: [
      {
        label: 'Verify Bolt port 7687',
        cmd: 'ss -tlnp | grep 7687',
        hint: 'Neo4j Bolt port is 7687 (note: web browser is on 7474).',
      },
    ],
    quickDefaults: {
      host: '127.0.0.1',
      port: '7687',
      database: 'neo4j',
      username: 'neo4j',
      password: '',
    },
  },
  redis: {
    title: 'Redis Key-Value Detective',
    catchphrase: 'Redis in-memory caching and fast key-value lookups!',
    steps: [
      {
        label: 'Check Redis ping',
        cmd: 'redis-cli ping',
        hint: 'Should return `PONG`. Standard port is 6379, database index is `0`.',
      },
    ],
    quickDefaults: {
      host: '127.0.0.1',
      port: '6379',
      database: '0',
      username: '',
      password: '',
    },
  },
  cassandra: {
    title: 'Apache Cassandra Detective',
    catchphrase: 'High-throughput CQL distributed table queries!',
    steps: [
      {
        label: 'Check CQL native port 9042',
        cmd: 'nodetool status && ss -tlnp | grep 9042',
        hint: 'Cassandra CQL port is 9042. Default keyspace is `system`.',
      },
    ],
    quickDefaults: {
      host: '127.0.0.1',
      port: '9042',
      database: 'system',
      username: '',
      password: '',
    },
  },
  custom: {
    title: 'Custom / Personal DBMS Detective',
    catchphrase: 'Connect any personal, proprietary, or custom SQL database endpoint!',
    steps: [
      {
        label: 'Step 1: Check wire compatibility',
        cmd: 'postgres | mysql | sqlite | duckdb | mongodb',
        hint: 'Most modern relational & cloud engines (CockroachDB, TiDB, Timescale, Redshift, MariaDB) use standard PostgreSQL or MySQL wire protocols.',
      },
      {
        label: 'Step 2: Verify custom server port',
        cmd: 'ss -tlnp | grep <port>',
        hint: 'Common custom ports: CockroachDB (26257), TiDB (4000), TimescaleDB (5432), MariaDB (3306), MongoDB (27017).',
      },
      {
        label: 'Step 3: Save as Personal Profile',
        cmd: 'localStorage',
        hint: 'Save your customized database profile so you can load and connect to it anytime with one click!',
      },
    ],
    quickDefaults: {
      host: '127.0.0.1',
      port: '5432',
      database: 'main',
      username: 'admin',
      password: '',
    },
  },
};

export const ConnectionModal: React.FC<ConnectionModalProps> = ({ isOpen, onClose }) => {
  const userId = useAppStore((s) => s.userId);
  const theme = useAppStore((s) => s.theme);
  const setIsDbConnected = useAppStore((s) => s.setIsDbConnected);
  const setConnectedEngine = useAppStore((s) => s.setConnectedEngine);
  const setDatabaseProfile = useAppStore((s) => s.setDatabaseProfile);
  const setAvailableDatabases = useAppStore((s) => s.setAvailableDatabases);
  const bumpSchemaVersion = useSchemaStore((s) => s.bumpSchemaVersion);
  const isDark = theme === 'dark';

  const [status, setStatus] = useState<ConnectionStatus>({ connected: false });
  const [connectorType, setConnectorType] = useState('mysql');
  const [database, setDatabase] = useState('mysql');
  const [host, setHost] = useState('127.0.0.1');
  const [port, setPort] = useState('3306');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [availableDbs, setAvailableDbs] = useState<string[]>([]);
  const [isFetchingDbs, setIsFetchingDbs] = useState(false);
  const [tables, setTables] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

  // Custom / Personal DBMS Profile State
  const [customName, setCustomName] = useState('My Custom DB');
  const [customProtocol, setCustomProtocol] = useState('postgres');
  const [savedProfiles, setSavedProfiles] = useState<{ id: string; name: string; protocol: string; host: string; port: string; database: string; username: string; password?: string }[]>(() => {
    try {
      const raw = localStorage.getItem('nl2sql_custom_db_profiles');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  const handleSaveCustomProfile = () => {
    const prof = {
      id: Date.now().toString(),
      name: customName.trim() || 'Custom DB',
      protocol: customProtocol,
      host: host.trim(),
      port: port.trim(),
      database: database.trim(),
      username: username.trim(),
      password,
    };
    const updated = [prof, ...savedProfiles.filter((p) => p.name !== prof.name)];
    setSavedProfiles(updated);
    try {
      localStorage.setItem('nl2sql_custom_db_profiles', JSON.stringify(updated));
    } catch {}
    setFeedback({
      type: 'success',
      message: `✨ Saved custom personal DBMS profile "${prof.name}"!`,
    });
  };

  const handleLoadCustomProfile = (profId: string) => {
    const prof = savedProfiles.find((p) => p.id === profId);
    if (!prof) return;
    setCustomName(prof.name);
    setCustomProtocol(prof.protocol);
    setHost(prof.host);
    setPort(prof.port);
    setDatabase(prof.database);
    setUsername(prof.username);
    setPassword(prof.password || '');
    setFeedback({
      type: 'info',
      message: `Loaded custom profile "${prof.name}". Ready to test or attach socket.`,
    });
  };

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
  // Comic book detective thought bubble state
  const [showComicHint, setShowComicHint] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  const currentInfo = PORT_INSTRUCTIONS[connectorType] || PORT_INSTRUCTIONS['mysql'];
  const currentConnectorMeta = CONNECTOR_TYPES.find((c) => c.id === connectorType);
  const currentTip = DETECTIVE_TIPS[connectorType] || DETECTIVE_TIPS['mysql'];

  const handleCopyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCmd(cmd);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const handleApplyQuickDefaults = () => {
    const tip = DETECTIVE_TIPS[connectorType] || DETECTIVE_TIPS['mysql'];
    if (tip?.quickDefaults) {
      if (tip.quickDefaults.host !== undefined) setHost(tip.quickDefaults.host);
      if (tip.quickDefaults.port !== undefined) setPort(tip.quickDefaults.port);
      if (tip.quickDefaults.database !== undefined) setDatabase(tip.quickDefaults.database);
      if (tip.quickDefaults.username !== undefined) setUsername(tip.quickDefaults.username);
      if (tip.quickDefaults.password !== undefined) setPassword(tip.quickDefaults.password);
      setFeedback({
        type: 'info',
        message: `✨ Pre-filled recommended local defaults for ${connectorType.toUpperCase()}!`,
      });
    }
  };

  // ── Focus trap and keyboard handling ──
  const modalRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      // Focus trap
      if (e.key === 'Tab' && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

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
        // Trigger ER diagram refresh on database switch
        bumpSchemaVersion();
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
        // Trigger ER diagram refresh after any successful SQL execution
        bumpSchemaVersion();
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
        } else {
          setDatabase('__none__');
          setDatabaseProfile('__none__');
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
        setAvailableDbs([]);
        setAvailableDatabases([]);
        setDatabaseProfile('__none__');
      }
    } catch {
      setStatus({ connected: false });
      setIsDbConnected(false);
      setConnectedEngine(null);
      setAvailableDbs([]);
      setAvailableDatabases([]);
      setDatabaseProfile('__none__');
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
        extra_params: connectorType === 'custom' ? {
          custom_name: customName || 'Custom DBMS',
          protocol: customProtocol,
        } : {},
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
        database: database.trim() === '__none__' ? '' : database.trim(),
        host: host.trim() || undefined,
        port: port ? parseInt(port, 10) : undefined,
        username: username.trim() || undefined,
        password: password || undefined,
        extra_params: connectorType === 'custom' ? {
          custom_name: customName || 'Custom DBMS',
          protocol: customProtocol,
        } : {},
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
        database: database.trim() === '__none__' ? '' : database.trim(),
        host: host.trim() || undefined,
        port: port ? parseInt(port, 10) : undefined,
        username: username.trim() || undefined,
        password: password || undefined,
        extra_params: connectorType === 'custom' ? {
          custom_name: customName || 'Custom DBMS',
          protocol: customProtocol,
        } : {},
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
        // Trigger ER diagram refresh after attaching
        bumpSchemaVersion();
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
      setAvailableDbs([]);
      setAvailableDatabases([]);
      setDatabaseProfile('__none__');
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
        database: database.trim() === '__none__' ? '' : database.trim(),
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
        database: database.trim() === '__none__' ? '' : database.trim(),
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
        message: `All done! Dependencies installed, connection verified, and socket attached to ${connectorType.toUpperCase()} [${database}].`,
      });
      await fetchStatus();
      // Trigger ER diagram refresh after one-click setup
      bumpSchemaVersion();
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'One-click setup failed' });
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const modalBg = isDark
    ? 'bg-[var(--bg-panel)] text-[var(--text-primary)] border-[var(--border-hairline)] shadow-black/80'
    : 'bg-[var(--bg-panel)] text-[var(--text-primary)] border-[var(--border-hairline)] shadow-2xl';
  const inputBg = isDark ? 'bg-[var(--bg-panel-alt)]' : 'bg-[var(--bg-panel-alt)]';
  const inputBorder = isDark ? 'border-[var(--border-hairline)]' : 'border-[var(--border-hairline)]';
  const muted = isDark ? 'text-[var(--text-recessive)]' : 'text-[var(--text-recessive)]';
  const mutedHover = isDark ? 'hover:text-[var(--text-primary)]' : 'hover:text-[var(--text-primary)]';
  const labelClass = isDark ? 'text-[var(--text-body)]' : 'text-[var(--text-body)]';
  const sectionBorder = isDark ? 'border-[var(--border-hairline)]' : 'border-[var(--border-hairline)]';
  const successBg = isDark ? 'bg-[var(--success)]/10 border-[var(--success)]/50 text-[var(--success)]' : 'bg-emerald-50 border-emerald-300 text-emerald-800';
  const errorBg = isDark ? 'bg-[var(--danger)]/10 border-[var(--danger)]/50 text-[var(--danger)]' : 'bg-rose-50 border-rose-300 text-rose-800';
  const infoBg = isDark ? 'bg-[var(--accent-primary)]/10 border-[var(--accent-primary)]/50 text-[var(--accent-primary)]' : 'bg-indigo-50 border-indigo-300 text-indigo-800';

  return createPortal(
    <div className="modal-overlay bg-black/80 backdrop-blur-sm animate-fade-in">
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="connection-modal-title"
        className={`w-full max-w-2xl border rounded-[var(--radius-panel)] shadow-2xl p-6 transition-colors duration-200 overflow-y-auto max-h-[calc(100vh-48px)] my-auto ${modalBg}`}
      >
        {/* Connection Steps Escort Hint Box */}
        <div className={`mb-4 p-3.5 rounded-[var(--radius-panel)] border text-[11px] font-mono leading-snug shadow-sm ${
          isDark
            ? 'bg-[var(--bg-ghost)] border-[var(--border-hairline)] text-[var(--text-body)]'
            : 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-body)]'
        }`}>
          <div className="font-bold text-[var(--accent-primary)] mb-1.5 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> How to Connect to Your Database
          </div>
          <ol className="list-decimal list-inside space-y-1 pl-1">
            <li><strong>1.</strong> Select connector type (PostgreSQL / MySQL / SQLite / DuckDB / etc.).</li>
            <li><strong>2.</strong> Click <strong>Install Dependencies</strong> to auto-install the required Python driver.</li>
            <li><strong>3.</strong> Enter host, port, database name, username, and password.</li>
            <li><strong>4.</strong> Click <strong>Test Connection</strong> to verify socket handshake, then <strong>Attach Socket</strong> to bind.</li>
            <li><strong>5.</strong> Or use <strong>One-Click Setup</strong> to do all steps automatically!</li>
          </ol>
        </div>

        {/* Header */}
        <div className={`flex items-center justify-between pb-3 border-b ${sectionBorder} relative`}>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 flex items-center justify-center bg-[var(--accent-primary)]/20 text-[var(--accent-primary)]">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <h2 id="connection-modal-title" className="text-sm font-bold tracking-tight">Myspire — Live DBMS Socket Connector</h2>
              <p className={`text-[11px] ${muted}`}>
                Session: <code className="font-mono text-[var(--accent-primary)]">{userId}</code>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Detective Hints Magnifying Glass Button (Comic Book Style) */}
            <button
              type="button"
              onClick={() => setShowComicHint((prev) => !prev)}
              aria-label="Toggle Database Detective Thought Bubble"
              title="Don't know your database credentials? Click for Detective hints!"
              className={`relative flex items-center gap-1.5 px-3 py-1 text-[11px] font-black uppercase tracking-wider rounded-full border-2 border-black transition-transform duration-100 active:translate-x-0.5 active:translate-y-0.5 cursor-pointer select-none ${
                showComicHint
                  ? 'bg-[#FFE600] text-black shadow-[1px_1px_0px_0px_#000]'
                  : 'bg-[#FFF9C4] hover:bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]'
              }`}
            >
              <Search className={`w-3.5 h-3.5 stroke-[3] ${showComicHint ? 'animate-bounce' : ''}`} />
              <span>Clues</span>
              <span className="w-1.5 h-1.5 rounded-full bg-black inline-block" />
            </button>
            <button
              onClick={onClose}
              aria-label="Close connection modal"
              className={`p-1.5 transition-colors duration-200 cursor-pointer rounded-[var(--radius-pill)] ${muted} ${mutedHover}`}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Comic Book Style Detective Thought Bubble (One-Tone Dithered Pop-Up, No Gradients) */}
        {showComicHint && (
          <div className="relative mt-4 mb-3 animate-fade-in z-20">
            {/* Thought bubble trail puffs (ascending comic dots) */}
            <div className="flex justify-end pr-14 -mb-1 space-x-1.5 pointer-events-none select-none">
              <span className="w-2 h-2 rounded-full border-2 border-black bg-[#FFE600] shadow-[1px_1px_0px_0px_#000] inline-block" />
              <span className="w-3.5 h-3.5 rounded-full border-2 border-black bg-[#FFE600] shadow-[2px_2px_0px_0px_#000] inline-block" />
              <span className="w-5 h-5 rounded-full border-2 border-black bg-[#FFE600] shadow-[2px_2px_0px_0px_#000] inline-block" />
            </div>

            {/* Main Comic Thought Bubble Cloud Container - One Tone with Halftone Dither Dot Matrix */}
            <div
              className="relative rounded-[24px] border-[3px] border-black bg-[#FFFBEA] dark:bg-[#1A1A1A] text-black dark:text-zinc-100 p-5 shadow-[6px_6px_0px_0px_#000] overflow-hidden"
            >
              {/* Halftone / Ben-Day Dot Dither Pattern Overlay (Flat, Repeating Dots, No Gradient) */}
              <div
                className="absolute inset-0 pointer-events-none opacity-15 dark:opacity-20"
                style={{
                  backgroundImage: 'radial-gradient(currentColor 1.2px, transparent 1.2px)',
                  backgroundSize: '6px 6px',
                }}
              />

              {/* Comic bubble header row */}
              <div className="relative z-10 flex items-start justify-between gap-3 border-b-2 border-black dark:border-zinc-700 pb-3 mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2.5 py-0.5 text-[10px] font-black uppercase tracking-widest bg-[#FFE600] text-black border-2 border-black shadow-[2px_2px_0px_0px_#000]">
                    POW! DETECTIVE CLUES
                  </span>
                  <span className="text-xs font-black tracking-tight uppercase text-black dark:text-[#FFE600]">
                    {currentTip.title}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={handleApplyQuickDefaults}
                    className="px-2.5 py-1 text-[10px] font-black uppercase tracking-wider bg-[#86EFAC] hover:bg-[#4ADE80] text-black border-2 border-black shadow-[2px_2px_0px_0px_#000] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all cursor-pointer flex items-center gap-1"
                    title="Pre-fill form with standard local parameters"
                  >
                    <Sparkles className="w-3 h-3 stroke-[2.5]" />
                    <span>Auto-Fill Defaults</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowComicHint(false)}
                    aria-label="Close thought bubble"
                    className="w-6 h-6 flex items-center justify-center font-black bg-white hover:bg-slate-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-black dark:text-white border-2 border-black shadow-[1px_1px_0px_0px_#000] cursor-pointer rounded-full text-xs"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Catchphrase dialogue banner */}
              <div className="relative z-10 mb-3 px-3 py-1.5 bg-white dark:bg-zinc-900 border-2 border-black shadow-[2px_2px_0px_0px_#000] text-[11px] font-bold italic text-black dark:text-zinc-200">
                "{currentTip.catchphrase}"
              </div>

              {/* Quick Clue Box: Host, Port, User, DB (Flat Solid Boxes, No Gradients) */}
              <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3 text-[11px] font-mono">
                <div className="p-2 border-2 border-black bg-white dark:bg-zinc-900 shadow-[2px_2px_0px_0px_#000]">
                  <div className="text-[9px] font-black uppercase text-black/60 dark:text-zinc-400">Host</div>
                  <div className="font-extrabold truncate text-black dark:text-white">{currentTip.quickDefaults.host || 'None (Local)'}</div>
                </div>
                <div className="p-2 border-2 border-black bg-white dark:bg-zinc-900 shadow-[2px_2px_0px_0px_#000]">
                  <div className="text-[9px] font-black uppercase text-black/60 dark:text-zinc-400">Port</div>
                  <div className="font-extrabold truncate text-black dark:text-white">{currentTip.quickDefaults.port || 'N/A'}</div>
                </div>
                <div className="p-2 border-2 border-black bg-white dark:bg-zinc-900 shadow-[2px_2px_0px_0px_#000]">
                  <div className="text-[9px] font-black uppercase text-black/60 dark:text-zinc-400">Default DB</div>
                  <div className="font-extrabold truncate text-black dark:text-white">{currentTip.quickDefaults.database || ':memory:'}</div>
                </div>
                <div className="p-2 border-2 border-black bg-white dark:bg-zinc-900 shadow-[2px_2px_0px_0px_#000]">
                  <div className="text-[9px] font-black uppercase text-black/60 dark:text-zinc-400">Default User</div>
                  <div className="font-extrabold truncate text-black dark:text-white">{currentTip.quickDefaults.username || 'None'}</div>
                </div>
              </div>

              {/* Step-by-step terminal cheat commands */}
              <div className="relative z-10 space-y-2 mt-2">
                <div className="text-[10px] font-black uppercase tracking-wider text-black dark:text-[#FFE600] flex items-center gap-1">
                  <Terminal className="w-3.5 h-3.5 stroke-[2.5]" />
                  <span>Terminal Inspector Commands (Click command to Copy):</span>
                </div>
                {currentTip.steps.map((st, i) => (
                  <div
                    key={i}
                    className="p-2.5 border-2 border-black bg-white dark:bg-zinc-900 shadow-[2px_2px_0px_0px_#000] flex flex-col gap-1"
                  >
                    <div className="flex items-center justify-between text-[11px] font-bold text-black dark:text-zinc-100">
                      <span>{st.label}</span>
                      <span className="text-[10px] font-normal italic text-black/70 dark:text-zinc-400">{st.hint}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2 bg-black text-[#FFE600] px-2.5 py-1.5 font-mono text-[11px] border-2 border-black overflow-x-auto shadow-[1px_1px_0px_0px_#000]">
                      <span className="select-all truncate">{st.cmd}</span>
                      <button
                        type="button"
                        onClick={() => handleCopyCommand(st.cmd)}
                        className="shrink-0 p-1 hover:text-white transition-colors cursor-pointer"
                        title="Copy command to clipboard"
                      >
                        {copiedCmd === st.cmd ? <Check className="w-3.5 h-3.5 text-[#4ADE80]" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Status Indicator */}
        <div
          className={`mt-4 p-3 flex items-center justify-between text-xs font-mono border rounded-[var(--radius-panel)] ${
            status.connected ? 'bg-[var(--success)]/10 border-[var(--success)] text-[var(--success)]' : `${inputBg} ${inputBorder} ${muted}`
          }`}
        >
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 inline-block rounded-full ${status.connected ? 'bg-[var(--success)]' : 'bg-[var(--text-recessive)]'}`} />
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
              className="text-[var(--danger)] hover:opacity-80 flex items-center gap-1 font-semibold cursor-pointer text-[11px] transition-colors duration-200"
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
              className={`w-full px-3 py-2 border rounded-[var(--radius-pill)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)] focus:border-[var(--border-focus)] font-mono text-xs transition-colors duration-200 ${inputBg} ${inputBorder} ${isDark ? 'text-[var(--text-primary)]' : 'text-slate-900'}`}
            >
              {CONNECTOR_TYPES.map((c) => (
                <option key={c.id} value={c.id} className={isDark ? 'bg-[var(--bg-panel)] text-[var(--text-primary)]' : 'bg-white text-slate-900'}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* ── Custom Personal DBMS Configuration Panel ── */}
          {connectorType === 'custom' && (
            <div className={`p-3.5 border rounded-[var(--radius-panel)] space-y-3 ${isDark ? 'bg-[var(--bg-ghost)] border-[var(--border-hairline)]' : 'bg-blue-50/60 border-blue-200'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-semibold text-xs text-[var(--accent-primary)]">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Personal / Custom Database Configuration</span>
                </div>
                {savedProfiles.length > 0 && (
                  <span className="text-[10px] text-[var(--text-muted)] font-mono">
                    {savedProfiles.length} saved profile(s)
                  </span>
                )}
              </div>

              {/* Saved Profiles Dropdown */}
              {savedProfiles.length > 0 && (
                <div>
                  <label className={`block text-[11px] font-semibold ${muted} mb-1`}>Load Saved Personal Profile:</label>
                  <select
                    onChange={(e) => {
                      if (e.target.value) handleLoadCustomProfile(e.target.value);
                    }}
                    defaultValue=""
                    className={`w-full px-2.5 py-1.5 border rounded-[var(--radius-pill)] text-xs font-mono focus:outline-none ${inputBg} ${inputBorder} ${isDark ? 'text-[var(--text-primary)]' : 'text-slate-900'}`}
                  >
                    <option value="" disabled>-- Select a Profile to Load --</option>
                    {savedProfiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.protocol.toUpperCase()} @ {p.host || 'localhost'}:{p.port || 'default'})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Profile Name & Wire Protocol */}
              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className={`block text-[11px] font-semibold ${muted} mb-1`}>Custom DBMS Label:</label>
                  <input
                    type="text"
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    placeholder="e.g. My TiDB Cluster / Internal DB"
                    className={`w-full px-2.5 py-1.5 border rounded-[var(--radius-pill)] font-mono text-xs focus:outline-none ${inputBg} ${inputBorder} ${isDark ? 'text-[var(--text-primary)]' : 'text-slate-900'}`}
                  />
                </div>
                <div>
                  <label className={`block text-[11px] font-semibold ${muted} mb-1`}>Base Wire Protocol:</label>
                  <select
                    value={customProtocol}
                    onChange={(e) => {
                      const proto = e.target.value;
                      setCustomProtocol(proto);
                      if (proto === 'postgres') setPort('5432');
                      else if (proto === 'mysql') setPort('3306');
                      else if (proto === 'mongodb') setPort('27017');
                      else if (proto === 'clickhouse') setPort('8123');
                      else if (proto === 'sqlite' || proto === 'duckdb') setPort('');
                    }}
                    className={`w-full px-2.5 py-1.5 border rounded-[var(--radius-pill)] font-mono text-xs focus:outline-none ${inputBg} ${inputBorder} ${isDark ? 'text-[var(--text-primary)]' : 'text-slate-900'}`}
                  >
                    <option value="postgres">PostgreSQL Wire (CockroachDB, Timescale, Redshift, Supabase)</option>
                    <option value="mysql">MySQL Wire (MariaDB, TiDB, SingleStore, Percona)</option>
                    <option value="sqlite">SQLite / Embedded File (LibSQL, Turso)</option>
                    <option value="duckdb">DuckDB Columnar OLAP</option>
                    <option value="mongodb">MongoDB Document Wire</option>
                    <option value="clickhouse">ClickHouse HTTP API</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[10px] text-[var(--text-muted)]">
                  Configure server parameters below, then click Save or Attach.
                </span>
                <button
                  type="button"
                  onClick={handleSaveCustomProfile}
                  className="px-2.5 py-1 text-[11px] font-semibold rounded-[var(--radius-pill)] bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/25 cursor-pointer flex items-center gap-1 transition-colors duration-200"
                >
                  <Check className="w-3 h-3" />
                  <span>Save Personal Profile</span>
                </button>
              </div>
            </div>
          )}

          {/* ── Install Dependencies Section ── */}
          <div className={`p-3.5 border rounded-[var(--radius-panel)] ${isDark ? 'bg-[var(--bg-ghost)] border-[var(--border-hairline)]' : 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)]'}`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Package className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
                <span className="text-[11px] font-semibold text-[var(--text-secondary)]">
                  Python Driver Dependencies
                </span>
              </div>
              <div className="flex items-center gap-2">
                {isCheckingDeps && <Loader2 className="w-3 h-3 animate-spin text-[var(--accent-primary)]" />}
                {depStatus && (
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-[var(--radius-pill)] ${
                    depStatus.allInstalled
                      ? isDark
                        ? 'bg-[var(--success)]/10 border border-[var(--success)]/40 text-[var(--success)]'
                        : 'bg-emerald-50 border border-emerald-300 text-emerald-700'
                      : isDark
                        ? 'bg-[var(--warning)]/10 border border-[var(--warning)]/40 text-[var(--warning)]'
                        : 'bg-amber-50 border border-amber-300 text-amber-700'
                  }`}>
                    {depStatus.allInstalled ? 'Ready' : 'Missing'}
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
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-[var(--radius-panel)] text-[10px] font-mono border ${
                      p.installed
                        ? isDark
                          ? 'bg-[var(--success)]/10 border-[var(--success)]/30 text-[var(--success)]'
                          : 'bg-emerald-50 border-emerald-200 text-emerald-700'
                        : isDark
                          ? 'bg-[var(--danger)]/10 border-[var(--danger)]/30 text-[var(--danger)]'
                          : 'bg-rose-50 border-rose-200 text-rose-700'
                    }`}
                  >
                    <span className="flex items-center gap-1"><Package className="w-3 h-3" /> {p.package}</span>
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
                className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold border cursor-pointer rounded-[var(--radius-pill)] transition-colors duration-200 ${
                  depStatus?.allInstalled
                    ? 'bg-[var(--success)]/10 border-[var(--success)] text-[var(--success)] opacity-70 cursor-default'
                    : 'bg-[var(--accent-primary)]/20 border-[var(--accent-primary)]/50 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/30'
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
                    ? 'All Installed'
                    : 'Install Dependencies'}
              </button>
              <button
                type="button"
                onClick={() => checkDeps()}
                disabled={isCheckingDeps}
                className={`p-1.5 border cursor-pointer rounded-[var(--radius-pill)] transition-colors duration-200 ${inputBg} ${inputBorder} ${muted} ${mutedHover}`}
                title="Re-check dependency status"
              >
                <RefreshCw className={`w-3 h-3 ${isCheckingDeps ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* ── How to Find Port & Server — Collapsible Instructions ── */}
          <div className={`border rounded-[var(--radius-panel)] overflow-hidden ${inputBorder}`}>
            <button
              type="button"
              onClick={() => setShowInstructions(!showInstructions)}
              className={`w-full flex items-center justify-between px-3 py-2 text-[11px] font-semibold cursor-pointer transition-colors duration-200 ${
                isDark ? 'bg-[var(--bg-card-header)] hover:bg-[var(--bg-subtle)]' : 'bg-[var(--bg-card-header)] hover:bg-[var(--bg-subtle)]'
              } text-[var(--text-secondary)]`}
            >
              <div className="flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
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
                <div className={`mt-2 p-2 rounded-[var(--radius-panel)] border text-[9px] ${
                  isDark ? 'bg-[var(--bg-panel-alt)] border-[var(--border-subtle)] text-[var(--text-recessive)]' : 'bg-amber-50 border-amber-200 text-amber-800'
                }`}>
                  <strong>Quick Reference — Default Ports:</strong>
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
                className={`w-full px-3 py-2 border rounded-[var(--radius-pill)] font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)] focus:border-[var(--border-focus)] transition-colors duration-200 ${
                  isDark
                    ? 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-primary)] placeholder-[var(--text-recessive)]'
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
                className={`w-full px-3 py-2 border rounded-[var(--radius-pill)] font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)] focus:border-[var(--border-focus)] transition-colors duration-200 ${
                  isDark
                    ? 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-primary)] placeholder-[var(--text-recessive)]'
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
                  className={`w-full px-3 py-2 border rounded-[var(--radius-pill)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)] focus:border-[var(--border-focus)] font-mono text-xs transition-colors duration-200 ${
                    isDark
                      ? 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-primary)]'
                      : 'bg-white border-slate-300 text-slate-900'
                  }`}
                >
                  <option value="__none__" className={isDark ? 'bg-[var(--bg-panel)] text-[var(--warning)] font-semibold' : 'bg-white text-amber-700 font-semibold'}>
                    No Database (Create New DB / Scratch)
                  </option>
                  <optgroup label="Available Databases">
                    {availableDbs.map((d) => (
                      <option key={d} value={d} className={isDark ? 'bg-[var(--bg-panel)] text-[var(--text-primary)]' : 'bg-white text-slate-900'}>
                        {d}
                      </option>
                    ))}
                  </optgroup>
                </select>
                <button
                  type="button"
                  onClick={fetchDatabases}
                  disabled={isFetchingDbs}
                  title="Re-list accessible databases"
                  className={`shrink-0 p-2 border rounded-[var(--radius-pill)] cursor-pointer transition-colors duration-200 ${
                    isDark
                      ? 'bg-[var(--bg-ghost)] border-[var(--border-hairline)] text-[var(--text-body)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-panel-alt)]'
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
                className={`w-full px-3 py-2 border rounded-[var(--radius-pill)] font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)] focus:border-[var(--border-focus)] transition-colors duration-200 ${
                  isDark
                    ? 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-primary)] placeholder-[var(--text-recessive)]'
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
                className={`w-full px-3 py-2 border rounded-[var(--radius-pill)] font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)] focus:border-[var(--border-focus)] transition-colors duration-200 ${
                  isDark
                    ? 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-primary)] placeholder-[var(--text-recessive)]'
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
                className={`w-full px-3 py-2 border rounded-[var(--radius-pill)] font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)] focus:border-[var(--border-focus)] transition-colors duration-200 ${
                  isDark
                    ? 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-primary)] placeholder-[var(--text-recessive)]'
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
                className={`max-h-36 overflow-y-auto px-3 py-2 border rounded-[var(--radius-panel)] font-mono text-[10px] ${
                  isDark
                    ? 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-body)]'
                    : 'bg-white border-slate-300 text-slate-800'
                }`}
              >
                {tables.map((t) => (
                  <div key={t} className={`py-0.5 ${isDark ? 'text-[var(--text-body)]' : 'text-slate-700'}`}>
                    • {t}
                  </div>
                ))}
              </div>
            ) : (
              <div className={`p-2.5 border rounded-[var(--radius-panel)] font-mono text-[11px] ${
                isDark
                  ? 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-recessive)]'
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
            <label className="block text-[11px] font-semibold text-[var(--success)] mb-1">
              Direct DB Mutation & Changes [{database}]:
            </label>
            <div className="space-y-1.5">
              <textarea
                rows={2}
                value={directSql}
                onChange={(e) => setDirectSql(e.target.value)}
                placeholder="e.g. CREATE TABLE test_table (id INT PRIMARY KEY, name VARCHAR(50)); or INSERT INTO ...;"
                className={`w-full px-2.5 py-1.5 border rounded-[var(--radius-panel)] font-mono text-xs focus:outline-none focus:border-[var(--border-focus)] focus:ring-1 focus:ring-[var(--border-focus)] transition-colors duration-200 ${
                  isDark
                    ? 'bg-[var(--bg-panel-alt)] border-[var(--border-hairline)] text-[var(--text-primary)] placeholder-[var(--text-recessive)]'
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
                  className="px-3 py-1 text-xs font-semibold bg-[var(--success)] hover:opacity-90 text-[var(--text-heading)] cursor-pointer border border-[var(--success)] transition-colors duration-200 rounded-[var(--radius-pill)]"
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
            className={`mt-4 p-2.5 border rounded-[var(--radius-panel)] text-xs flex items-center gap-2 ${
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
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-bold border cursor-pointer rounded-[var(--radius-pill)] transition-colors duration-200 bg-[var(--accent-primary)]/20 border-[var(--accent-primary)]/50 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/30 shadow-md"
            title="Auto-install dependencies, test connection, and attach socket in one click"
          >
            <Download className="w-3.5 h-3.5" />
            <span>One-Click Setup</span>
          </button>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleTest}
              disabled={isLoading}
              className={`px-3 py-1.5 text-xs font-semibold border cursor-pointer rounded-[var(--radius-pill)] transition-colors duration-200 ${
                isDark
                  ? 'bg-[var(--bg-ghost)] border-[var(--border-hairline)] text-[var(--text-primary)] hover:bg-[var(--bg-panel-alt)]'
                  : 'bg-slate-100 border-slate-300 text-slate-800 hover:bg-slate-200'
              }`}
            >
              <RefreshCw className={`w-3.5 h-3.5 inline mr-1 ${isLoading ? 'animate-spin' : ''}`} />
              Test Connection
            </button>
            <button
              onClick={handleAttach}
              disabled={isLoading}
              className="px-4 py-1.5 text-xs font-semibold bg-[var(--accent-primary)] hover:opacity-90 text-[var(--text-heading)] font-bold cursor-pointer shadow-md rounded-[var(--radius-pill)] transition-colors duration-200 flex items-center gap-1.5"
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
