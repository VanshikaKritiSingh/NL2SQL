// src/modules/approval_gate/ERDiagramPanel.tsx
import React, { useMemo, useState, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { TableNode } from './TableNode';
import { useAppStore } from '../../store/useAppStore';
import { parseTablesFromDDL } from '../../utils/ddlParser';
import type { SchemaInfo, TableInfo, ForeignKey } from '../../types/schema';
import type { ImpactedTable } from '../../types/approval';
import { Sparkles, Layers, Eye } from 'lucide-react';

interface ERDiagramPanelProps {
  schema: SchemaInfo | null;
  impactedTables?: ImpactedTable[];
  generatedSql?: string | null;
  initialScope?: 'query' | 'all';
}

const nodeTypes = {
  tableNode: TableNode,
};

/**
 * Compute an optimal grid layout based on the number of tables.
 */
function computeGridLayout(tableCount: number): { cols: number; xGap: number; yGap: number } {
  if (tableCount <= 1) return { cols: 1, xGap: 0, yGap: 0 };
  if (tableCount <= 2) return { cols: 2, xGap: 420, yGap: 300 };
  if (tableCount <= 4) return { cols: 2, xGap: 400, yGap: 320 };
  if (tableCount <= 6) return { cols: 3, xGap: 380, yGap: 320 };
  if (tableCount <= 9) return { cols: 3, xGap: 360, yGap: 300 };
  return { cols: Math.min(4, Math.ceil(Math.sqrt(tableCount))), xGap: 350, yGap: 300 };
}

export const ERDiagramPanel: React.FC<ERDiagramPanelProps> = ({
  schema,
  impactedTables = [],
  generatedSql,
  initialScope,
}) => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  // Parse DDL statements from generated SQL to synthesize virtual tables if not yet in live schema
  const parsedDDL = useMemo(() => {
    return parseTablesFromDDL(generatedSql);
  }, [generatedSql]);

  // Set of newly generated table names (only explicitly created tables)
  const newTableSet = useMemo(() => {
    const s = new Set<string>();
    parsedDDL.tableNames.forEach((name) => s.add(name.toLowerCase()));
    impactedTables.forEach((t) => {
      const op = (t.operation || '').toUpperCase();
      if (op === 'CREATE') {
        s.add(t.name.toLowerCase());
      }
    });
    return s;
  }, [parsedDDL, impactedTables]);

  // Set of all query-impacted table names
  const impactedSet = useMemo(() => {
    const s = new Set<string>();
    impactedTables.forEach((t) => s.add(t.name.toLowerCase()));
    parsedDDL.tableNames.forEach((t) => s.add(t.toLowerCase()));
    return s;
  }, [impactedTables, parsedDDL]);

  const hasQueryScope = impactedSet.size > 0;

  // View scope state: 'query' (focused on impacted/new tables) or 'all' (entire database)
  const [scope, setScope] = useState<'query' | 'all'>(() => {
    if (initialScope) return initialScope;
    return hasQueryScope ? 'query' : 'all';
  });

  useEffect(() => {
    if (initialScope) {
      setScope(initialScope);
    }
  }, [initialScope]);

  // Merge schema tables with newly declared DDL tables
  const mergedTables = useMemo<TableInfo[]>(() => {
    const existing = schema?.tables ? [...schema.tables] : [];
    const existingMap = new Set(existing.map((t) => t.name.toLowerCase()));

    // Add synthesized tables that are not yet committed to live schema
    parsedDDL.tables.forEach((dt) => {
      if (!existingMap.has(dt.name.toLowerCase())) {
        existing.push(dt);
        existingMap.add(dt.name.toLowerCase());
      }
    });

    return existing;
  }, [schema, parsedDDL]);

  // Merge foreign keys
  const mergedForeignKeys = useMemo<ForeignKey[]>(() => {
    const existing = schema?.foreign_keys ? [...schema.foreign_keys] : [];
    const fkKeys = new Set(
      existing.map((fk) => `${fk.from_table}.${fk.from_column}->${fk.to_table}.${fk.to_column}`.toLowerCase())
    );

    parsedDDL.foreignKeys.forEach((fk) => {
      const key = `${fk.from_table}.${fk.from_column}->${fk.to_table}.${fk.to_column}`.toLowerCase();
      if (!fkKeys.has(key)) {
        existing.push(fk);
        fkKeys.add(key);
      }
    });

    return existing;
  }, [schema, parsedDDL]);

  // Determine active tables based on scope
  const visibleTables = useMemo<TableInfo[]>(() => {
    if (scope === 'query' && hasQueryScope) {
      const filtered = mergedTables.filter((t) => impactedSet.has(t.name.toLowerCase()));
      return filtered.length > 0 ? filtered : mergedTables;
    }
    return mergedTables;
  }, [mergedTables, scope, hasQueryScope, impactedSet]);

  // Convert visible tables to React Flow nodes with auto-grid layout
  const initialNodes = useMemo(() => {
    if (visibleTables.length === 0) return [];

    const impactedMap = new Map<string, { level: 'direct' | 'referenced'; operation?: string | null }>();
    impactedTables.forEach((t) => {
      impactedMap.set(t.name.toLowerCase(), {
        level: t.impact_level,
        operation: t.operation,
      });
    });

    const { cols, xGap, yGap } = computeGridLayout(visibleTables.length);

    return visibleTables.map((tbl, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const isNew = newTableSet.has(tbl.name.toLowerCase());
      const impact = impactedMap.get(tbl.name.toLowerCase());
      const isSelected = isNew || impact !== undefined;

      return {
        id: tbl.name,
        type: 'tableNode',
        position: { x: col * xGap + 40, y: row * yGap + 40 },
        data: {
          table: tbl,
          impactLevel: impact ? impact.level : isNew ? 'direct' : 'none',
          operation: impact?.operation || (isNew ? 'CREATE' : null),
          isSelectedEntity: isSelected,
          isNewlyGenerated: isNew,
        },
      };
    });
  }, [visibleTables, impactedTables, newTableSet]);

  // Connectors: Link Foreign Key rows between visible tables
  const initialEdges = useMemo(() => {
    if (mergedForeignKeys.length === 0) return [];

    const visibleNameSet = new Set(visibleTables.map((t) => t.name.toLowerCase()));
    const edgeColor = isDark ? '#A78BFA' : '#6712DC';
    const edgeLabelColor = isDark ? '#E0E7FF' : '#6712DC';
    const edgeLabelBg = isDark ? '#1E1E2C' : '#FFFFFF';

    return mergedForeignKeys
      .filter((fk) => visibleNameSet.has(fk.from_table.toLowerCase()) && visibleNameSet.has(fk.to_table.toLowerCase()))
      .map((fk, i) => {
        const isImpacted =
          impactedSet.has(fk.from_table.toLowerCase()) || impactedSet.has(fk.to_table.toLowerCase());

        return {
          id: `fk-${fk.from_table}-${fk.from_column}-${fk.to_table}-${fk.to_column}-${i}`,
          source: fk.from_table,
          sourceHandle: `${fk.from_table}-${fk.from_column}`,
          target: fk.to_table,
          targetHandle: `${fk.to_table}-${fk.to_column}`,
          type: 'smoothstep',
          pathOptions: { borderRadius: 12 },
          animated: isImpacted,
          label: `${fk.from_column} → ${fk.to_column}`,
          labelStyle: { fill: edgeLabelColor, fontSize: 10, fontFamily: 'monospace', fontWeight: 600 },
          labelBgStyle: { fill: edgeLabelBg, fillOpacity: 0.95, rx: 0, ry: 0 },
          labelBgPadding: [6, 4] as [number, number],
          style: {
            stroke: edgeColor,
            strokeWidth: 2,
          },
          markerEnd: {
            type: MarkerType.Arrow,
            color: edgeColor,
            strokeWidth: 2,
            width: 14,
            height: 14,
          },
        };
      });
  }, [mergedForeignKeys, visibleTables, impactedSet, isDark]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  // Re-key ReactFlow when scope or visible tables change so fitView recalculates cleanly
  const flowKey = `er-${scope}-${visibleTables.length}-${initialEdges.length}-${theme}`;

  return (
    <div
      className={`w-full h-full rounded-none overflow-hidden relative shadow-inner ${
        isDark ? 'border border-white/15 bg-[#101018]' : 'border border-[#DDE1E8] bg-[#E8E8EC]'
      }`}
    >
      <ReactFlow
        key={flowKey}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.25, maxZoom: 1.5 }}
        minZoom={0.1}
        maxZoom={2.5}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1.5}
          color={isDark ? 'rgba(255, 255, 255, 0.15)' : '#D2D2D8'}
        />
        <Controls
          className={
            isDark
              ? '!bg-[#181824] !border !border-white/20 !shadow-2xl !rounded-none overflow-hidden [&_button]:!bg-[#181824] [&_button]:!border-white/15 [&_button]:!fill-slate-300 [&_button:hover]:!bg-[#222232] [&_path]:!fill-slate-300'
              : '!bg-white !border !border-[#EBE6EE] !shadow-lg !rounded-none overflow-hidden [&_button]:!bg-white [&_button]:!border-[#EBE6EE] [&_button]:!fill-slate-600 [&_button:hover]:!bg-[#F4F4F6]'
          }
        />
        <MiniMap
          nodeColor={(n) => {
            if (n.data?.isNewlyGenerated) return isDark ? '#10B981' : '#059669';
            if (n.data?.impactLevel === 'direct') return isDark ? '#F43F5E' : '#E11D48';
            return isDark ? '#8E94F2' : '#6712DC';
          }}
          maskColor={isDark ? 'rgba(16, 16, 24, 0.75)' : 'rgba(232, 232, 236, 0.7)'}
          className={
            isDark
              ? '!bg-[#181824] !border !border-white/20 !rounded-none !shadow-xl'
              : '!bg-white !border !border-[#EBE6EE] !rounded-none !shadow-md'
          }
        />
      </ReactFlow>

      {/* Floating Toolbar & Legend Overlay */}
      <div
        className={`absolute top-3 left-3 backdrop-blur-md rounded-none p-2 text-[11px] font-sans shadow-lg flex flex-wrap items-center gap-3 z-10 ${
          isDark
            ? 'bg-[#181824]/95 border border-white/15 text-slate-200'
            : 'bg-white/95 border border-[#EBE6EE] text-[#1E1E24]'
        }`}
      >
        {/* Scope Switcher: Focused View (Query Scope) vs Entire Database */}
        {hasQueryScope && (
          <div className="flex items-center gap-1 p-0.5 rounded-none border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5">
            <button
              type="button"
              onClick={() => setScope('query')}
              className={`flex items-center gap-1.5 px-2 py-1 text-[10px] font-semibold transition-all cursor-pointer rounded-none ${
                scope === 'query'
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Show only tables touched by this query"
            >
              <Eye className="w-3 h-3" />
              <span>Query Scope ({visibleTables.length})</span>
            </button>
            <button
              type="button"
              onClick={() => setScope('all')}
              className={`flex items-center gap-1.5 px-2 py-1 text-[10px] font-semibold transition-all cursor-pointer rounded-none ${
                scope === 'all'
                  ? isDark ? 'bg-indigo-600 text-white shadow-xs' : 'bg-[#6712DC] text-white shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Show all tables in the database"
            >
              <Layers className="w-3 h-3" />
              <span>Whole Database ({mergedTables.length})</span>
            </button>
          </div>
        )}

        {/* Legend: New Table distinction */}
        {newTableSet.size > 0 && (
          <div className="flex items-center gap-1.5 font-medium text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="flex items-center gap-0.5 font-bold">
              <Sparkles className="w-2.5 h-2.5" />
              New Table
            </span>
          </div>
        )}

        <div className="flex items-center gap-1.5 text-slate-400">
          <span className="w-2 h-2 rounded-none border border-slate-400 bg-slate-500/20" />
          <span>Existing Table</span>
        </div>

        <div className="flex items-center gap-1.5">
          <span
            className={`w-4 h-4 rounded-none text-white text-[8px] font-bold flex items-center justify-center ${
              isDark ? 'bg-[#7B2CBF]' : 'bg-[#6712DC]'
            }`}
          >
            PK
          </span>
          <span className={`font-medium ${isDark ? 'text-slate-200' : 'text-[#1E1E24]'}`}>PK</span>
        </div>

        <div className="flex items-center gap-1.5">
          <span
            className={`w-4 h-4 rounded-none text-white text-[8px] font-bold flex items-center justify-center ${
              isDark ? 'bg-[#9D4EDD]' : 'bg-[#8D3CFF]'
            }`}
          >
            FK
          </span>
          <span className={`font-medium ${isDark ? 'text-slate-200' : 'text-[#1E1E24]'}`}>FK</span>
        </div>

        <div className={`text-[10px] font-mono ${isDark ? 'text-slate-500' : 'text-[#ABABAB]'}`}>
          {visibleTables.length}T · {initialEdges.length}FK
        </div>
      </div>
    </div>
  );
};
