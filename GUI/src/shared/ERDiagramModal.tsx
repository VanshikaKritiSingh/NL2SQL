// src/shared/ERDiagramModal.tsx — On-Demand ER Schema Graph Popup
import React from 'react';
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
  title?: string;
}

export const ERDiagramModal: React.FC<ERDiagramModalProps> = ({
  isOpen,
  onClose,
  schema,
  impactedTables = [],
  title = 'Database ER Schema Graph',
}) => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';
  const bumpSchemaVersion = useSchemaStore((s) => s.bumpSchemaVersion);
  const isFetching = useSchemaStore((s) => s.isFetching);

  if (!isOpen) return null;

  const totalColumns = schema?.tables
    ? schema.tables.reduce((acc, t) => acc + t.columns.length, 0)
    : 0;

  return createPortal(
    <div className="modal-overlay bg-black/80 backdrop-blur-md animate-fade-in">
      <div
        className="w-full max-w-6xl h-[min(88vh,calc(100vh-48px))] max-h-[calc(100vh-48px)] rounded-none shadow-2xl flex flex-col overflow-hidden transition-all duration-300 my-auto"
        style={{
          backgroundColor: isDark ? '#181824' : '#FFFFFF',
          border: isDark ? '1px solid rgba(255,255,255,0.18)' : '1px solid #DDE1E8',
        }}
      >
        {/* Header */}
        <div className={`h-14 px-5 border-b flex items-center justify-between shrink-0 ${
          isDark ? 'bg-[#1E1E2C] border-white/12 text-white' : 'bg-[#FAF7FC] border-[#EBE6EE] text-[#1E1E24]'
        }`}>
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-none flex items-center justify-center text-white shadow-md ${
              isDark ? 'bg-gradient-to-tr from-[#7B2CBF] to-[#9D4EDD]' : 'bg-gradient-to-tr from-[#6712DC] to-[#8D3CFF]'
            }`}>
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h2 className={`text-sm font-bold tracking-tight ${isDark ? 'text-white' : 'text-[#1E1E24]'}`}>{title}</h2>
              <p className={`text-[10px] font-mono ${isDark ? 'text-slate-400' : 'text-[#8E8E98]'}`}>
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
              className={`p-1.5 rounded-none transition-colors cursor-pointer ${
                isDark ? 'text-slate-400 hover:text-white hover:bg-white/10' : 'text-[#8E8E98] hover:text-[#1E1E24] hover:bg-[#F4F4F6]'
              }`}
              title="Refresh schema from database"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className={`p-1.5 rounded-none transition-colors cursor-pointer ${
                isDark ? 'text-slate-400 hover:text-white hover:bg-white/10' : 'text-[#8E8E98] hover:text-[#1E1E24] hover:bg-[#F4F4F6]'
              }`}
              title="Close Diagram"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Canvas Body — ER Diagram Canvas View */}
        <div className={`flex-1 min-h-0 p-3 ${isDark ? 'bg-[#101018]' : 'bg-[#E8E8EC]'}`}>
          {schema && schema.tables.length > 0 ? (
            <ERDiagramPanel schema={schema} impactedTables={impactedTables} />
          ) : (
            <div className={`flex flex-col items-center justify-center h-full gap-3 ${isDark ? 'text-slate-400' : 'text-[#8E8E98]'}`}>
              <Database className="w-10 h-10 opacity-40" />
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
