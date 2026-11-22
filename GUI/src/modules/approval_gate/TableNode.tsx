// src/modules/m14/TableNode.tsx
import React, { memo, useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import { GripVertical, Plus, Eye, EyeOff, Minus, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import type { TableInfo } from '../../types/schema';

interface TableNodeProps {
  data: {
    table: TableInfo;
    impactLevel: 'direct' | 'referenced' | 'none';
    operation?: string | null;
    isSelectedEntity?: boolean;
    isNewlyGenerated?: boolean;
  };
}

export const TableNode = memo(({ data }: TableNodeProps) => {
  const { table, impactLevel, operation, isSelectedEntity, isNewlyGenerated } = data;
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';
  const [expandedCols, setExpandedCols] = useState<Set<string>>(new Set());
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(new Set());

  const toggleExpand = (colName: string) => {
    setExpandedCols((prev) => {
      const next = new Set(prev);
      if (next.has(colName)) next.delete(colName);
      else next.add(colName);
      return next;
    });
  };

  const toggleVisibility = (e: React.MouseEvent, colName: string) => {
    e.stopPropagation();
    setHiddenCols((prev) => {
      const next = new Set(prev);
      if (next.has(colName)) next.delete(colName);
      else next.add(colName);
      return next;
    });
  };

  const isPrimaryOrSelected = isSelectedEntity || impactLevel === 'direct' || impactLevel === 'referenced';

  return (
    <div
      className={`w-72 rounded-[var(--radius-panel)] overflow-hidden font-sans transition-colors duration-200 select-none border ${
        isNewlyGenerated
          ? isDark
            ? 'bg-[var(--bg-panel-alt)] border-[var(--success)]/80 shadow-[0_8px_30px_rgba(52,211,153,0.23)] hover:border-[var(--success)]'
            : 'bg-[var(--bg-panel-alt)] border-[var(--success)] shadow-[0_8px_30px_rgba(21,128,61,0.18)] hover:border-[var(--success)]'
          : isDark
          ? 'bg-[var(--er-node-bg)] border-[var(--er-node-border)] shadow-[0_8px_30px_rgba(0,0,0,0.6)] hover:border-[var(--accent-primary)]/50 hover:shadow-[0_12px_36px_rgba(196,181,253,0.12)]'
          : 'bg-[var(--er-node-bg)] border-[var(--er-node-border)] shadow-[0_8px_30px_rgba(0,0,0,0.08)] hover:border-[var(--accent-primary)]/40 hover:shadow-[0_12px_36px_rgba(77,47,135,0.10)]'
      }`}
    >
      {/* Node-level Fallback Handles */}
      <Handle type="target" id="target" position={Position.Left} className="!opacity-0 !w-1 !h-1" />
      <Handle type="source" id="source" position={Position.Right} className="!opacity-0 !w-1 !h-1" />

      {/* Table Header */}
      <div
        className={`px-3.5 py-2.5 flex items-center justify-between border-b ${
          isNewlyGenerated
            ? isDark
              ? 'bg-gradient-to-r from-[var(--success)] via-teal-800 to-[var(--bg-ghost)] border-[var(--success)]/40 text-[var(--text-primary)]'
              : 'bg-gradient-to-r from-[var(--success)] via-teal-600 to-[var(--bg-ghost)] border-[var(--success)] text-[var(--text-primary)]'
            : isPrimaryOrSelected
            ? isDark
              ? 'bg-gradient-to-r from-[var(--er-header-gradient-from)] to-[var(--er-header-gradient-to)] border-[var(--er-node-border)] text-[var(--text-primary)]'
              : 'bg-gradient-to-r from-[var(--er-header-gradient-from)] to-[var(--er-header-gradient-to)] border-[var(--er-node-border)] text-[var(--text-primary)]'
            : isDark
            ? 'bg-[var(--bg-ghost)] border-[var(--er-node-border)] text-[var(--text-heading)]'
            : 'bg-[var(--bg-ghost)] border-[var(--er-node-border)] text-[var(--text-primary)]'
        }`}
      >
        <div className="flex items-center gap-2 truncate">
          <span
            className={`font-bold text-sm tracking-tight truncate ${
              isNewlyGenerated || isPrimaryOrSelected
                ? 'text-[var(--text-primary)] drop-shadow-xs'
                : isDark
                ? 'text-[var(--text-primary)]'
                : 'text-[var(--text-heading)]'
            }`}
          >
            {table.name}
          </span>
          {isNewlyGenerated && (
            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-[var(--radius-pill)] bg-[var(--success)] text-white shadow-xs flex items-center gap-0.5">
              <Sparkles className="w-2.5 h-2.5" aria-hidden="true" />
              <span>NEW</span>
            </span>
          )}
          {!isNewlyGenerated && (
            <span className={`text-[8px] font-mono font-medium px-1.5 py-0.2 rounded-[var(--radius-pill)] border ${
              isDark ? 'bg-white/5 border-white/10 text-[var(--text-recessive)]' : 'bg-black/5 border-black/10 text-[var(--text-recessive)]'
            }`}>
              EXISTING
            </span>
          )}
          {table.row_count !== undefined && table.row_count !== null && (
            <span
              className={`text-[9px] font-mono font-medium px-1.5 py-0.2 rounded-[var(--radius-pill)] border ${
                isNewlyGenerated || isPrimaryOrSelected
                  ? 'bg-white/20 border-white/30 text-white'
                  : isDark
                  ? 'bg-white/5 border-white/10 text-[var(--text-body)]'
                  : 'bg-black/5 border-black/10 text-[var(--text-body)]'
              }`}
              title={`${table.row_count} rows in table`}
            >
              {table.row_count} {table.row_count === 1 ? 'row' : 'rows'}
            </span>
          )}
          {operation && (
            <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-[var(--radius-pill)] bg-[var(--danger)] text-white shadow-xs">
              {operation}
            </span>
          )}
        </div>

        {/* Right-aligned ∷ drag and + add icons */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            className={`p-1 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer ${
              isPrimaryOrSelected
                ? 'text-white/80 hover:text-white hover:bg-white/20'
                : isDark
                ? 'text-[var(--text-recessive)] hover:text-white hover:bg-white/10'
                : 'text-[var(--text-recessive)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-panel-alt)]'
            }`}
            title="Add attribute"
          >
            <Plus className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
          <div
            className={`cursor-grab active:cursor-grabbing p-1 ${
              isPrimaryOrSelected ? 'text-white/80' : isDark ? 'text-[var(--text-recessive)]' : 'text-[var(--text-recessive)]'
            }`}
            title="Drag table"
          >
            <GripVertical className="w-3.5 h-3.5" aria-hidden="true" />
          </div>
        </div>
      </div>

      {/* Attributes List */}
      <div className="p-2 space-y-1.5 bg-[var(--er-node-bg)]">
        {table.columns.map((col) => {
          const isExpanded = expandedCols.has(col.name);
          const isHidden = hiddenCols.has(col.name);

          return (
            <div key={col.name} className="relative">
              {/* Connector Handles located at the exact attribute row level */}
              <Handle
                type="target"
                id={`${table.name}-${col.name}`}
                position={Position.Left}
                className="!w-2 !h-2 !border-none !-left-[9px] !top-1/2 !-translate-y-1/2 !rounded-none !bg-[var(--er-edge-color-from)]"
                title={`Target: ${table.name}.${col.name}`}
              />
              <Handle
                type="source"
                id={`${table.name}-${col.name}`}
                position={Position.Right}
                className="!w-2 !h-2 !border-none !-right-[9px] !top-1/2 !-translate-y-1/2 !rounded-none !bg-[var(--er-edge-color-from)]"
                title={`Source: ${table.name}.${col.name}`}
              />

              {/* Recessed row */}
              <div
                onClick={() => toggleExpand(col.name)}
                className={`group px-2.5 py-1.5 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer flex items-center justify-between border bg-[var(--er-attr-bg)] hover:bg-[var(--bg-ghost)] border-transparent hover:border-[var(--border-hairline)] ${
                  isHidden ? 'opacity-40' : ''
                }`}
              >
                {/* Left side: Square Key Badge + Attribute Name */}
                <div className="flex items-center gap-2 truncate min-w-0">
                  {col.is_primary_key ? (
                    <span
                      className="w-5 h-5 rounded-none text-white font-bold text-[9px] flex items-center justify-center shrink-0 shadow-xs bg-[var(--er-pk-badge)]"
                      title="Primary Key"
                    >
                      PK
                    </span>
                  ) : col.is_foreign_key ? (
                    <span
                      className="w-5 h-5 rounded-none text-white font-bold text-[9px] flex items-center justify-center shrink-0 shadow-xs bg-[var(--accent-primary)]"
                      title={`Foreign Key -> ${col.fk_references || ''}`}
                    >
                      FK
                    </span>
                  ) : (
                    <span
                      className="w-5 h-5 rounded-none font-mono text-[9px] flex items-center justify-center shrink-0 bg-[var(--bg-ghost)] text-[var(--text-recessive)]"
                    >
                      •
                    </span>
                  )}

                  <span className="text-xs font-semibold truncate text-[var(--er-attr-text)]">
                    {col.name}
                  </span>
                </div>

                {/* Right side: Data type pill + Visibility Eye + Remove '-' Icon */}
                <div className="flex items-center gap-1.5 shrink-0 ml-2">
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded-[var(--radius-pill)] border text-[var(--er-attr-type)] bg-[var(--bg-ghost)] border-[var(--border-hairline)]"
                  >
                    {col.data_type}
                  </span>

                  <button
                    type="button"
                    onClick={(e) => toggleVisibility(e, col.name)}
                    className={`p-0.5 rounded-[var(--radius-control)] transition-colors duration-200 opacity-70 group-hover:opacity-100 ${
                      isDark ? 'text-[var(--text-recessive)] hover:text-white' : 'text-[var(--text-recessive)] hover:text-[var(--text-primary)]'
                    }`}
                    title={isHidden ? 'Show attribute' : 'Hide attribute'}
                  >
                    {isHidden ? <EyeOff className="w-3 h-3" aria-hidden="true" /> : <Eye className="w-3 h-3" aria-hidden="true" />}
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                    }}
                    className="p-0.5 rounded-[var(--radius-control)] transition-colors duration-200 opacity-70 group-hover:opacity-100 text-[var(--text-recessive)] hover:text-[var(--danger)]"
                    title="Remove attribute"
                  >
                    <Minus className="w-3 h-3" aria-hidden="true" />
                  </button>

                  <div className="text-[var(--text-recessive)]">
                    {isExpanded ? <ChevronUp className="w-3 h-3" aria-hidden="true" /> : <ChevronDown className="w-3 h-3" aria-hidden="true" />}
                  </div>
                </div>
              </div>

              {/* Expandable 2-column sub-rows for secondary metadata */}
              {isExpanded && (
                <div
                  className="mt-1 p-2 rounded-[var(--radius-control)] text-[10px] space-y-2 shadow-xs animate-fade-in border bg-[var(--er-attr-bg)] border-[var(--border-hairline)] text-[var(--text-body)]"
                >
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <div>
                        <span className="block text-[9px] uppercase font-bold text-[var(--text-recessive)]">
                          Default:
                        </span>
                        <span className="font-mono font-medium text-[var(--er-attr-text)]">
                          {col.default_value !== undefined && col.default_value !== null
                            ? col.default_value
                            : col.is_primary_key
                            ? 'AUTO_INCREMENT'
                            : 'NULL'}
                        </span>
                      </div>
                      <div>
                        <span className="block text-[9px] uppercase font-bold text-[var(--text-recessive)]">
                          Index:
                        </span>
                        <span className="font-mono font-medium text-[var(--er-attr-text)]">
                          {col.is_primary_key ? 'PRIMARY (BTREE)' : col.is_foreign_key ? 'INDEX (FK)' : 'NONE'}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div>
                        <span className="block text-[9px] uppercase font-bold text-[var(--text-recessive)]">
                          Nullable:
                        </span>
                        <span className="font-mono font-medium text-[var(--er-attr-text)]">
                          {col.nullable ? 'YES' : 'NO'}
                        </span>
                      </div>
                      <div>
                        <span className="block text-[9px] uppercase font-bold text-[var(--text-recessive)]">
                          {col.is_foreign_key ? 'References:' : 'Collation:'}
                        </span>
                        <span className="font-mono font-medium truncate block text-[var(--er-attr-text)]">
                          {col.is_foreign_key ? col.fk_references || 'FOREIGN KEY' : 'utf8mb4_bin'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Sample data values row (if populated by introspection) */}
                  {col.sample_values && col.sample_values.length > 0 && (
                    <div className="pt-1 border-t border-[var(--border-hairline)]">
                      <span className="block text-[9px] uppercase font-bold mb-0.5 text-[var(--text-recessive)]">
                        Sample Data:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {col.sample_values.map((val, idx) => (
                          <span
                            key={idx}
                            className="text-[9px] font-mono px-1 py-0.2 rounded-[var(--radius-pill)] border bg-[var(--success)]/10 border-[var(--success)]/20 text-[var(--success)]"
                          >
                            {String(val)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
});
