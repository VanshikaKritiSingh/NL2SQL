// src/shared/ERDiagramModal.tsx — On-Demand ER Schema Graph Popup
import React, { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, Database, RefreshCw } from 'lucide-react';
import { ERDiagramPanel } from '../modules/approval_gate/ERDiagramPanel';
import { useAppStore } from '../store/useAppStore';
import { useSchemaStore } from '../store/useSchemaStore';
import type { SchemaInfo } from '../types/schema';
import type { ImpactedTable } from '../types/approval';

interface ERDiagramModalProps {
  isOpen: boolean;
  onClose: () => void;
  schema: SchemaInfo | null;
  impactedTables?: ImpactedTable[];
  generatedSql?: string | null;
  defaultScope?: 'query' | 'all';
  title?: string;
}

export const ERDiagramModal: React.FC<ERDiagramModalProps> = ({
  isOpen,
  onClose,
  schema,
  impactedTables = [],
  generatedSql,
  defaultScope,
  title = 'Database ER Schema Graph',
}) => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';
  const bumpSchemaVersion = useSchemaStore((s) => s.bumpSchemaVersion);
  const isFetching = useSchemaStore((s) => s.isFetching);

  // Escape key handler
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  const totalColumns = schema?.tables
    ? schema.tables.reduce((acc, t) => acc + t.columns.length, 0)
    : 0;

  const modalTitleId = 'er-diagram-modal-title';

  return createPortal(
    <div className="modal-overlay bg-black/80 backdrop-blur-md animate-fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={modalTitleId}
        className="w-full max-w-6xl h-[min(88vh,calc(100vh-48px))] max-h-[calc(100vh-48px)] rounded-[var(--radius-panel)] shadow-2xl flex flex-col overflow-hidden transition-colors duration-200 my-auto bg-[var(--bg-panel)] border border-[var(--border-hairline)] text-[var(--text-body)]"
      >
        {/* Header */}
        <div className="h-14 px-5 border-b flex items-center justify-between shrink-0 bg-[var(--bg-panel-alt)] border-[var(--border-subtle)] text-[var(--text-heading)]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-[var(--radius-control)] flex items-center justify-center bg-[var(--accent-primary)] text-[var(--btn-primary-text)] shadow-md">
              <Database className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <h2 id={modalTitleId} className="text-sm font-bold tracking-tight text-[var(--text-heading)]">{title}</h2>
              <p className="text-[10px] font-mono text-[var(--text-recessive)]">
                {schema?.tables
                  ? `${schema.database_name} · ${schema.tables.length} tables · ${totalColumns} columns · ${schema.foreign_keys?.length || 0} FK relations`
                  : 'Loading schema topology...'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Refresh button */}
            <button
              onClick={() => bumpSchemaVersion()}
              disabled={isFetching}
              className="p-1.5 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer text-[var(--text-recessive)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-ghost)]"
              title="Refresh schema from database"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} aria-hidden="true" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer text-[var(--text-recessive)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-ghost)]"
              title="Close Diagram"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Canvas Body — ER Diagram Canvas View */}
        <div className="flex-1 min-h-0 p-3 bg-[var(--bg-canvas)]">
          {schema && schema.tables.length > 0 ? (
            <ERDiagramPanel
              schema={schema}
              impactedTables={impactedTables}
              generatedSql={generatedSql}
              initialScope={defaultScope}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-[var(--text-recessive)]">
              <Database className="w-10 h-10 opacity-40" aria-hidden="true" />
              <p className="text-sm font-medium">No tables found in the current database</p>
              <p className="text-xs opacity-70">
                {schema
                  ? 'The connected database has no tables yet. Create a table using the Direct SQL executor in the Connection Modal.'
                  : 'Connect to a database to visualize its schema, or run a CREATE TABLE statement.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};
