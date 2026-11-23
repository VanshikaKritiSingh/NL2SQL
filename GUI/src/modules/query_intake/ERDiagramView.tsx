// src/modules/query_intake/ERDiagramView.tsx
import React, { useEffect, useCallback } from 'react';
import { Database, RefreshCw } from 'lucide-react';
import { ERDiagramPanel } from '../approval_gate/ERDiagramPanel';
import { useAppStore } from '../../store/useAppStore';
import { useSchemaStore } from '../../store/useSchemaStore';
import { useQueryStore } from '../../store/useQueryStore';
import { getLiveSchema } from '../../api/schemaApi';

export const ERDiagramView: React.FC = () => {
  const userId = useAppStore((s) => s.userId);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const connectedEngine = useAppStore((s) => s.connectedEngine);
  const isDbConnected = useAppStore((s) => s.isDbConnected);
  const databaseProfile = useAppStore((s) => s.databaseProfile);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const schema = useSchemaStore((s) => s.schema);
  const schemaVersion = useSchemaStore((s) => s.schemaVersion);
  const isFetchingSchema = useSchemaStore((s) => s.isFetching);
  const updateSchema = useSchemaStore((s) => s.updateSchema);
  const setFetching = useSchemaStore((s) => s.setFetching);
  const setFetchError = useSchemaStore((s) => s.setFetchError);
  const bumpSchemaVersion = useSchemaStore((s) => s.bumpSchemaVersion);

  const lastResponse = useQueryStore((s) => s.lastResponse);

  const fetchSchema = useCallback(async () => {
    setFetching(true);
    setFetchError(null);
    try {
      const dialect = connectedEngine || (targetDialect === 'auto' ? 'mysql' : targetDialect);
      const fetched = await getLiveSchema(userId, dialect);
      updateSchema(fetched);
    } catch (err: any) {
      setFetchError(err.message || 'Failed to fetch schema');
    } finally {
      setFetching(false);
    }
  }, [userId, targetDialect, connectedEngine, databaseProfile, updateSchema, setFetching, setFetchError]);

  useEffect(() => {
    fetchSchema();
  }, [fetchSchema, schemaVersion, isDbConnected, databaseProfile]);

  const totalColumns = schema?.tables
    ? schema.tables.reduce((acc, t) => acc + t.columns.length, 0)
    : 0;

  const hasTables = Boolean(schema && schema.tables && schema.tables.length > 0) || Boolean(lastResponse?.generated_sql);

  return (
    <div
      className="flex flex-col h-full overflow-hidden shadow-lg transition-colors duration-200 bento-card rounded-[var(--radius-panel)] border border-[var(--border-hairline)] bg-[var(--bg-card)]"
    >
      {/* Panel Header */}
      <div
        className={`px-4 py-2.5 border-b flex items-center justify-between shrink-0 transition-colors duration-200 ${
          isDark
            ? 'bg-[var(--bg-card-header)] border-[var(--border-main)]'
            : 'bg-[var(--bg-card-header)] border-[var(--border-subtle)]'
        }`}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Database aria-hidden="true" className="w-4 h-4 text-[var(--accent-primary)] shrink-0" />
          <span className="text-xs font-semibold text-[var(--text-heading)] whitespace-nowrap">
            Database ER Schema Diagram
          </span>
          {schema && (
            <span className="hidden sm:inline-flex text-[10px] px-2 py-0.5 rounded-[var(--radius-pill)] bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] font-mono font-medium truncate">
              {schema.database_name || 'Active Database'} · {schema.tables?.length || 0} tables · {totalColumns} cols · {schema.foreign_keys?.length || 0} FKs
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Refresh Schema Button */}
          <button
            onClick={() => bumpSchemaVersion()}
            disabled={isFetchingSchema}
            className="p-1.5 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer text-[var(--text-recessive)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-hover)]"
            title="Refresh schema from live database"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetchingSchema ? 'animate-spin' : ''}`} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Canvas Area */}
      <div className="flex-1 min-h-0 p-2 bg-[var(--bg-canvas)] relative">
        {hasTables ? (
          <ERDiagramPanel
            schema={schema}
            impactedTables={[]}
            generatedSql={lastResponse?.generated_sql}
            initialScope="all"
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-[var(--text-recessive)] p-6 text-center">
            <Database className="w-10 h-10 opacity-30 text-[var(--accent-primary)]" aria-hidden="true" />
            <p className="text-sm font-medium text-[var(--text-heading)]">No Schema Tables Found</p>
            <p className="text-xs max-w-sm text-center text-[var(--text-recessive)] leading-relaxed">
              Connect to a database via Settings &gt; Connect DB or execute a CREATE TABLE statement in the SQL editor to visualize table entities and foreign keys.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
