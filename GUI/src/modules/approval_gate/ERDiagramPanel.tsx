// src/modules/approval_gate/ERDiagramPanel.tsx
import React, { useMemo, useCallback } from 'react';
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
import type { SchemaInfo } from '../../types/schema';
import type { ImpactedTable } from '../../types/approval';

interface ERDiagramPanelProps {
  schema: SchemaInfo | null;
  impactedTables: ImpactedTable[];
}

const nodeTypes = {
  tableNode: TableNode,
};

/**
 * Compute an optimal grid layout based on the number of tables.
 * For small numbers (1-4), use a single row or 2×2.
 * For larger counts, use 2-3 columns with appropriate gaps.
 */
function computeGridLayout(tableCount: number): { cols: number; xGap: number; yGap: number } {
  if (tableCount <= 1) return { cols: 1, xGap: 0, yGap: 0 };
  if (tableCount <= 2) return { cols: 2, xGap: 420, yGap: 300 };
  if (tableCount <= 4) return { cols: 2, xGap: 400, yGap: 320 };
  if (tableCount <= 6) return { cols: 3, xGap: 380, yGap: 320 };
  if (tableCount <= 9) return { cols: 3, xGap: 360, yGap: 300 };
  return { cols: Math.min(4, Math.ceil(Math.sqrt(tableCount))), xGap: 350, yGap: 300 };
}

export const ERDiagramPanel: React.FC<ERDiagramPanelProps> = ({ schema, impactedTables }) => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  // Convert schema tables to React Flow nodes with auto-grid layout
  const initialNodes = useMemo(() => {
    if (!schema || !schema.tables || schema.tables.length === 0) return [];

    const impactedMap = new Map<string, { level: 'direct' | 'referenced'; operation?: string | null }>();
    impactedTables.forEach((t) => {
      impactedMap.set(t.name.toLowerCase(), {
        level: t.impact_level,
        operation: t.operation,
      });
    });

    const { cols, xGap, yGap } = computeGridLayout(schema.tables.length);

    return schema.tables.map((tbl, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const impact = impactedMap.get(tbl.name.toLowerCase());
      const isSelected = i === 0 || impact !== undefined;

      return {
        id: tbl.name,
        type: 'tableNode',
        position: { x: col * xGap + 40, y: row * yGap + 40 },
        data: {
          table: tbl,
          impactLevel: impact ? impact.level : 'none',
          operation: impact?.operation || null,
          isSelectedEntity: isSelected,
        },
      };
    });
  }, [schema, impactedTables, isDark]);

  // Connectors: Link exact Foreign Key rows to Primary Key rows using orthogonal elbow paths
  const initialEdges = useMemo(() => {
    if (!schema || !schema.foreign_keys || schema.foreign_keys.length === 0) return [];

    // Validate that both source and target tables exist
    const tableNames = new Set(schema.tables.map((t) => t.name));

    const impactedNames = new Set(impactedTables.map((t) => t.name.toLowerCase()));
    const edgeColor = isDark ? '#A78BFA' : '#6712DC';
    const edgeLabelColor = isDark ? '#E0E7FF' : '#6712DC';
    const edgeLabelBg = isDark ? '#1E1E2C' : '#FFFFFF';

    return schema.foreign_keys
      .filter((fk) => tableNames.has(fk.from_table) && tableNames.has(fk.to_table))
      .map((fk, i) => {
        const isImpacted =
          impactedNames.has(fk.from_table.toLowerCase()) || impactedNames.has(fk.to_table.toLowerCase());

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
  }, [schema, impactedTables, isDark]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  React.useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  React.useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  // Re-key ReactFlow when schema or theme changes so fitView runs fresh
  const flowKey = schema
    ? `${schema.dialect}-${schema.database_name}-${schema.tables.length}-${schema.foreign_keys?.length || 0}-${theme}`
    : `empty-${theme}`;

  return (
    <div
      className={`w-full h-full rounded-none overflow-hidden relative shadow-inner ${
        isDark ? 'border border-white/15 bg-[#101018]' : 'border border-[#DDE1E8] bg-[#E8E8EC]'
      }`}
    >
      {/* SVG Gradient definitions for connectors */}
      <svg className="absolute w-0 h-0 pointer-events-none">
        <defs>
          <linearGradient id="purpleConnectorGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={isDark ? '#8E94F2' : '#6712DC'} />
            <stop offset="100%" stopColor={isDark ? '#C4B5FD' : '#8D3CFF'} />
          </linearGradient>
        </defs>
      </svg>

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

      {/* Floating Legend Overlay */}
      <div
        className={`absolute top-3 left-3 backdrop-blur-md rounded-none p-2.5 text-[11px] font-sans shadow-lg flex flex-wrap items-center gap-4 ${
          isDark
            ? 'bg-[#181824]/95 border border-white/15 text-slate-200'
            : 'bg-white/95 border border-[#EBE6EE] text-[#1E1E24]'
        }`}
      >
        <div className="flex items-center gap-2">
          <span
            className={`w-4 h-4 rounded-none text-white text-[8px] font-bold flex items-center justify-center ${
              isDark ? 'bg-[#7B2CBF]' : 'bg-[#6712DC]'
            }`}
          >
            PK
          </span>
          <span className={`font-medium ${isDark ? 'text-slate-200' : 'text-[#1E1E24]'}`}>Primary Key</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`w-4 h-4 rounded-none text-white text-[8px] font-bold flex items-center justify-center ${
              isDark ? 'bg-[#9D4EDD]' : 'bg-[#8D3CFF]'
            }`}
          >
            FK
          </span>
          <span className={`font-medium ${isDark ? 'text-slate-200' : 'text-[#1E1E24]'}`}>Foreign Key</span>
        </div>
        <div className={`flex items-center gap-1.5 text-[10px] font-mono ${isDark ? 'text-slate-400' : 'text-[#8E8E98]'}`}>
          <span className={`w-4 h-0.5 ${isDark ? 'bg-[#8E94F2]' : 'bg-[#6712DC]'}`} />
          <span>Relationships</span>
        </div>
        {schema && (
          <div className={`text-[10px] font-mono ${isDark ? 'text-slate-500' : 'text-[#ABABAB]'}`}>
            {schema.tables.length}T · {schema.foreign_keys?.length || 0}FK
          </div>
        )}
      </div>
    </div>
  );
};
