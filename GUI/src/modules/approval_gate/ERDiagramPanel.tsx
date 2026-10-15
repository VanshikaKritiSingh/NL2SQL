// src/modules/m14/ERDiagramPanel.tsx
import React, { useMemo } from 'react';
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

export const ERDiagramPanel: React.FC<ERDiagramPanelProps> = ({ schema, impactedTables }) => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  // Convert schema tables to React Flow nodes with auto-grid layout
  const initialNodes = useMemo(() => {
    if (!schema || !schema.tables) return [];

    const impactedMap = new Map<string, { level: 'direct' | 'referenced'; operation?: string | null }>();
    impactedTables.forEach((t) => {
      impactedMap.set(t.name.toLowerCase(), {
        level: t.impact_level,
        operation: t.operation,
      });
    });

    const cols = 2;
    const xGap = 360;
    const yGap = 300;

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
  // Adapts stroke color and label styling according to the selected theme
  const initialEdges = useMemo(() => {
    if (!schema || !schema.foreign_keys) return [];

    const impactedNames = new Set(impactedTables.map((t) => t.name.toLowerCase()));
    const edgeColor = isDark ? '#A78BFA' : '#6712DC';
    const edgeLabelColor = isDark ? '#E0E7FF' : '#6712DC';
    const edgeLabelBg = isDark ? '#1E1E2C' : '#FFFFFF';

    return schema.foreign_keys.map((fk, i) => {
      const isImpacted =
        impactedNames.has(fk.from_table.toLowerCase()) || impactedNames.has(fk.to_table.toLowerCase());

      return {
        id: `fk-${fk.from_table}-${fk.to_table}-${i}`,
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
          type: MarkerType.Arrow, // Open V-shaped arrowhead per specification
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

  // Re-key ReactFlow when schema or theme changes so fitView runs fresh on theme toggle
  const flowKey = schema ? `${schema.dialect}-${schema.tables.length}-${theme}` : `empty-${theme}`;

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
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
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

      {/* Floating Node Inspector UI / Legend Overlay */}
      <div
        className={`absolute top-3 left-3 backdrop-blur-md rounded-none p-2.5 text-[11px] font-sans shadow-lg flex items-center gap-4 ${
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
          <span>Elbow Connectors (12px bend)</span>
        </div>
      </div>
    </div>
  );
};
