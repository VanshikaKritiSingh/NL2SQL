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
    const xGap = 340;
    const yGap = 260;

    return schema.tables.map((tbl, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const impact = impactedMap.get(tbl.name.toLowerCase());

      return {
        id: tbl.name,
        type: 'tableNode',
        position: { x: col * xGap + 40, y: row * yGap + 40 },
        data: {
          table: tbl,
          impactLevel: impact ? impact.level : 'none',
          operation: impact?.operation || null,
        },
      };
    });
  }, [schema, impactedTables]);

  // Convert schema foreign keys to React Flow edges
  const initialEdges = useMemo(() => {
    if (!schema || !schema.foreign_keys) return [];

    const impactedNames = new Set(impactedTables.map((t) => t.name.toLowerCase()));

    return schema.foreign_keys.map((fk, i) => {
      const isImpacted =
        impactedNames.has(fk.from_table.toLowerCase()) || impactedNames.has(fk.to_table.toLowerCase());

      return {
        id: `fk-${fk.from_table}-${fk.to_table}-${i}`,
        source: fk.from_table,
        target: fk.to_table,
        type: 'smoothstep',
        animated: isImpacted,
        label: `${fk.from_column} → ${fk.to_column}`,
        labelStyle: { fill: isDark ? '#94a3b8' : '#475569', fontSize: 10, fontFamily: 'monospace' },
        labelBgStyle: { fill: isDark ? '#0f172a' : '#ffffff', fillOpacity: 0.9 },
        style: {
          stroke: isImpacted ? '#f43f5e' : '#6366f1',
          strokeWidth: isImpacted ? 2.5 : 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isImpacted ? '#f43f5e' : '#6366f1',
        },
      };
    });
  }, [schema, impactedTables, isDark]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div
      className={`w-full h-full rounded-xl overflow-hidden border relative transition-colors ${
        isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
      }`}
    >
      <ReactFlow
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
          gap={16}
          size={1}
          color={isDark ? '#334155' : '#cbd5e1'}
        />
        <Controls
          className={`border rounded-lg ${
            isDark ? 'bg-slate-900 border-slate-700 text-slate-300' : 'bg-white border-slate-300 text-slate-700'
          }`}
        />
        <MiniMap
          nodeColor={(n) => (n.data?.impactLevel === 'direct' ? '#f43f5e' : '#4f46e5')}
          maskColor={isDark ? 'rgba(15, 23, 42, 0.7)' : 'rgba(241, 245, 249, 0.7)'}
          className={`border rounded-lg ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-300'}`}
        />
      </ReactFlow>

      {/* Legend Badge Overlay */}
      <div
        className={`absolute top-3 left-3 border rounded-lg p-2.5 text-[11px] font-mono shadow-lg flex items-center gap-4 ${
          isDark ? 'bg-slate-900/95 border-slate-800' : 'bg-white/95 border-slate-300'
        }`}
      >
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-rose-500/20 border-2 border-rose-500" />
          <span className={isDark ? 'text-slate-300' : 'text-slate-700'}>Direct Write Target</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-amber-500/20 border-2 border-amber-400" />
          <span className={isDark ? 'text-slate-300' : 'text-slate-700'}>Referenced / Cascade</span>
        </div>
      </div>
    </div>
  );
};
