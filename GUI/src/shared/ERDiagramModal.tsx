// src/shared/ERDiagramModal.tsx — On-Demand ER Schema Graph Popup
import React from 'react';
import { X, Database, Maximize2 } from 'lucide-react';
import { ERDiagramPanel } from '../modules/approval_gate/ERDiagramPanel';
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
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-6xl h-[85vh] border rounded-2xl shadow-2xl flex flex-col overflow-hidden bg-[var(--bg-card)] border-[var(--border-main)]">
        {/* Header */}
        <div className="h-12 px-4 border-b flex items-center justify-between shrink-0 bg-[var(--bg-card-header)] border-[var(--border-subtle)]">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-[var(--accent-glow)] text-[var(--accent-primary)]">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight text-[var(--text-main)]">{title}</h2>
              <p className="text-[10px] text-[var(--text-muted)] font-mono">
                {schema?.tables ? `${schema.tables.length} tables · ${schema.foreign_keys?.length || 0} foreign key relations` : 'Loading schema topology...'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg transition-colors cursor-pointer text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)]"
              title="Close Diagram"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Canvas Body */}
        <div className="flex-1 min-h-0 p-3 bg-[var(--bg-app)]">
          <ERDiagramPanel schema={schema} impactedTables={impactedTables} />
        </div>
      </div>
    </div>
  );
};
