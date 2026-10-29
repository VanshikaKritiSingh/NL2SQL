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
      className={`w-72 rounded-none overflow-hidden font-sans transition-all select-none border ${
        isNewlyGenerated
          ? isDark
            ? 'bg-[#141E18] border-emerald-500/80 shadow-[0_8px_30px_rgba(16,185,129,0.25)] hover:border-emerald-400'
            : 'bg-[#F4FAF6] border-emerald-600 shadow-[0_8px_30px_rgba(16,185,129,0.18)] hover:border-emerald-500'
          : isDark
          ? 'bg-[#181824] border-white/15 shadow-[0_8px_30px_rgba(0,0,0,0.6)] hover:border-[#8E94F2]/50 hover:shadow-[0_12px_36px_rgba(142,148,242,0.18)]'
          : 'bg-[#FFFFFF] border-[#EBE6EE] shadow-[0_8px_30px_rgba(0,0,0,0.08)] hover:border-[#8D3CFF]/40 hover:shadow-[0_12px_36px_rgba(103,18,220,0.12)]'
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
              ? 'bg-gradient-to-r from-emerald-700 via-teal-800 to-[#10241A] border-emerald-500/40 text-white'
              : 'bg-gradient-to-r from-emerald-600 via-teal-600 to-[#E8F8F0] border-emerald-300 text-white'
            : isPrimaryOrSelected
            ? isDark
              ? 'bg-gradient-to-r from-[#7B2CBF] to-[#201A30] border-white/15 text-white'
              : 'bg-gradient-to-r from-[#8D3CFF] to-[#FAF7FC] border-[#EBE6EE] text-white'
            : isDark
            ? 'bg-[#1E1E2C] border-white/15 text-slate-100'
            : 'bg-[#FAF7FC] border-[#EBE6EE] text-[#1E1E24]'
        }`}
      >
        <div className="flex items-center gap-2 truncate">
          <span
            className={`font-bold text-sm tracking-tight truncate ${
              isNewlyGenerated || isPrimaryOrSelected
                ? 'text-white drop-shadow-xs'
                : isDark
                ? 'text-white'
                : 'text-[#1E1E24]'
            }`}
          >
            {table.name}
          </span>
          {isNewlyGenerated && (
            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-none bg-emerald-500 text-white shadow-xs flex items-center gap-0.5">
              <Sparkles className="w-2.5 h-2.5" />
              <span>NEW</span>
            </span>
          )}
          {!isNewlyGenerated && (
            <span className={`text-[8px] font-mono font-medium px-1.5 py-0.2 rounded-none border ${
              isDark ? 'bg-white/5 border-white/10 text-slate-400' : 'bg-black/5 border-black/10 text-slate-500'
            }`}>
              EXISTING
            </span>
          )}
          {table.row_count !== undefined && table.row_count !== null && (
            <span
              className={`text-[9px] font-mono font-medium px-1.5 py-0.2 rounded-none border ${
                isNewlyGenerated || isPrimaryOrSelected
                  ? 'bg-white/20 border-white/30 text-white'
                  : isDark
                  ? 'bg-white/5 border-white/10 text-slate-300'
                  : 'bg-black/5 border-black/10 text-slate-600'
              }`}
              title={`${table.row_count} rows in table`}
            >
              {table.row_count} {table.row_count === 1 ? 'row' : 'rows'}
            </span>
          )}
          {operation && (
            <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-none bg-rose-600 text-white shadow-xs">
              {operation}
            </span>
          )}
        </div>

        {/* Right-aligned ∷ drag and + add icons */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            className={`p-1 rounded-none transition-colors cursor-pointer ${
              isPrimaryOrSelected
                ? 'text-white/80 hover:text-white hover:bg-white/20'
                : isDark
                ? 'text-slate-400 hover:text-white hover:bg-white/10'
                : 'text-[#8E8E98] hover:text-[#1E1E24] hover:bg-[#F4F4F6]'
            }`}
            title="Add attribute"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <div
            className={`cursor-grab active:cursor-grabbing p-1 ${
              isPrimaryOrSelected ? 'text-white/80' : isDark ? 'text-slate-400' : 'text-[#8E8E98]'
            }`}
            title="Drag table"
          >
            <GripVertical className="w-3.5 h-3.5" />
          </div>
        </div>
      </div>

      {/* Attributes List */}
      <div className={`p-2 space-y-1.5 ${isDark ? 'bg-[#181824]' : 'bg-[#FFFFFF]'}`}>
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
                className={`!w-2 !h-2 !border-none !-left-[9px] !top-1/2 !-translate-y-1/2 !rounded-none ${
                  isDark ? '!bg-[#8E94F2]' : '!bg-[#6712DC]'
                }`}
                title={`Target: ${table.name}.${col.name}`}
              />
              <Handle
                type="source"
                id={`${table.name}-${col.name}`}
                position={Position.Right}
                className={`!w-2 !h-2 !border-none !-right-[9px] !top-1/2 !-translate-y-1/2 !rounded-none ${
                  isDark ? '!bg-[#C4B5FD]' : '!bg-[#8D3CFF]'
                }`}
                title={`Source: ${table.name}.${col.name}`}
              />

              {/* Recessed row with sharp 90-degree corners */}
              <div
                onClick={() => toggleExpand(col.name)}
                className={`group px-2.5 py-1.5 rounded-none transition-all cursor-pointer flex items-center justify-between border ${
                  isDark
                    ? 'bg-[#12121A] hover:bg-[#1E1E2C] border-transparent hover:border-white/12'
                    : 'bg-[#F4F4F6] hover:bg-[#ECECEF] border-transparent hover:border-[#E4E4E8]'
                } ${isHidden ? 'opacity-40' : ''}`}
              >
                {/* Left side: Square Key Badge + Attribute Name */}
                <div className="flex items-center gap-2 truncate min-w-0">
                  {col.is_primary_key ? (
                    <span
                      className={`w-5 h-5 rounded-none text-white font-bold text-[9px] flex items-center justify-center shrink-0 shadow-xs ${
                        isDark ? 'bg-[#7B2CBF]' : 'bg-[#6712DC]'
                      }`}
                      title="Primary Key"
                    >
                      PK
                    </span>
                  ) : col.is_foreign_key ? (
                    <span
                      className={`w-5 h-5 rounded-none text-white font-bold text-[9px] flex items-center justify-center shrink-0 shadow-xs ${
                        isDark ? 'bg-[#9D4EDD]' : 'bg-[#8D3CFF]'
                      }`}
                      title={`Foreign Key -> ${col.fk_references || ''}`}
                    >
                      FK
                    </span>
                  ) : (
                    <span
                      className={`w-5 h-5 rounded-none font-mono text-[9px] flex items-center justify-center shrink-0 ${
                        isDark ? 'bg-[#222232] text-slate-400' : 'bg-[#E8E8EE] text-[#8E8E98]'
                      }`}
                    >
                      •
                    </span>
                  )}

                  <span className={`text-xs font-semibold truncate ${isDark ? 'text-slate-100' : 'text-[#1E1E24]'}`}>
                    {col.name}
                  </span>
                </div>

                {/* Right side: Data type pill + Visibility Eye + Remove '-' Icon */}
                <div className="flex items-center gap-1.5 shrink-0 ml-2">
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded-none border ${
                      isDark
                        ? 'text-slate-300 bg-[#1E1E2C] border-white/10'
                        : 'text-[#8E8E98] bg-white border-[#E8E8EC]'
                    }`}
                  >
                    {col.data_type}
                  </span>

                  <button
                    type="button"
                    onClick={(e) => toggleVisibility(e, col.name)}
                    className={`p-0.5 rounded-none transition-colors opacity-70 group-hover:opacity-100 ${
                      isDark ? 'text-slate-400 hover:text-white' : 'text-[#8E8E98] hover:text-[#1E1E24]'
                    }`}
                    title={isHidden ? 'Show attribute' : 'Hide attribute'}
                  >
                    {isHidden ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                    }}
                    className={`p-0.5 rounded-none transition-colors opacity-70 group-hover:opacity-100 ${
                      isDark ? 'text-slate-400 hover:text-rose-400' : 'text-[#8E8E98] hover:text-rose-500'
                    }`}
                    title="Remove attribute"
                  >
                    <Minus className="w-3 h-3" />
                  </button>

                  <div className={isDark ? 'text-slate-400' : 'text-[#8E8E98]'}>
                    {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </div>
                </div>
              </div>

              {/* Expandable 2-column sub-rows for secondary metadata */}
              {isExpanded && (
                <div
                  className={`mt-1 p-2 rounded-none text-[10px] space-y-2 shadow-xs animate-fade-in border ${
                    isDark
                      ? 'bg-[#14141E] border-white/12 text-slate-300'
                      : 'bg-white border-[#EBE6EE] text-[#555560]'
                  }`}
                >
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <div>
                        <span className={`block text-[9px] uppercase font-bold ${isDark ? 'text-slate-400' : 'text-[#8E8E98]'}`}>
                          Default:
                        </span>
                        <span className={`font-mono font-medium ${isDark ? 'text-slate-100' : 'text-[#1E1E24]'}`}>
                          {col.default_value !== undefined && col.default_value !== null
                            ? col.default_value
                            : col.is_primary_key
                            ? 'AUTO_INCREMENT'
                            : 'NULL'}
                        </span>
                      </div>
                      <div>
                        <span className={`block text-[9px] uppercase font-bold ${isDark ? 'text-slate-400' : 'text-[#8E8E98]'}`}>
                          Index:
                        </span>
                        <span className={`font-mono font-medium ${isDark ? 'text-slate-100' : 'text-[#1E1E24]'}`}>
                          {col.is_primary_key ? 'PRIMARY (BTREE)' : col.is_foreign_key ? 'INDEX (FK)' : 'NONE'}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div>
                        <span className={`block text-[9px] uppercase font-bold ${isDark ? 'text-slate-400' : 'text-[#8E8E98]'}`}>
                          Nullable:
                        </span>
                        <span className={`font-mono font-medium ${isDark ? 'text-slate-100' : 'text-[#1E1E24]'}`}>
                          {col.nullable ? 'YES' : 'NO'}
                        </span>
                      </div>
                      <div>
                        <span className={`block text-[9px] uppercase font-bold ${isDark ? 'text-slate-400' : 'text-[#8E8E98]'}`}>
                          {col.is_foreign_key ? 'References:' : 'Collation:'}
                        </span>
                        <span className={`font-mono font-medium truncate block ${isDark ? 'text-slate-100' : 'text-[#1E1E24]'}`}>
                          {col.is_foreign_key ? col.fk_references || 'FOREIGN KEY' : 'utf8mb4_bin'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Sample data values row (if populated by introspection) */}
                  {col.sample_values && col.sample_values.length > 0 && (
                    <div className={`pt-1 border-t ${isDark ? 'border-white/10' : 'border-slate-200'}`}>
                      <span className={`block text-[9px] uppercase font-bold mb-0.5 ${isDark ? 'text-slate-400' : 'text-[#8E8E98]'}`}>
                        Sample Data:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {col.sample_values.map((val, idx) => (
                          <span
                            key={idx}
                            className={`text-[9px] font-mono px-1 py-0.2 rounded-none border ${
                              isDark
                                ? 'bg-white/5 border-white/10 text-emerald-300'
                                : 'bg-emerald-50 border-emerald-200 text-emerald-800'
                            }`}
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
