// src/modules/query_intake/QueryIntakePage.tsx
import React, { useEffect } from 'react';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';
import { HistorySidebar } from './HistorySidebar';
import { NLQueryInput } from './NLQueryInput';
import { SqlInspector } from './SqlInspector';
import { ResultPanel } from './ResultPanel';
import { ERDiagramView } from './ERDiagramView';
import { useAppStore } from '../../store/useAppStore';
import { useQueryStore } from '../../store/useQueryStore';
import { getHistory } from '../../api/queryApi';

export const QueryIntakePage: React.FC = () => {
  const userId = useAppStore((s) => s.userId);
  const theme = useAppStore((s) => s.theme);
  const rightPanelTab = useAppStore((s) => s.rightPanelTab);
  const setHistory = useQueryStore((s) => s.setHistory);
  const isDark = theme === 'dark';

  // Load history on mount or user change
  useEffect(() => {
    getHistory(userId).then(setHistory).catch(() => {});
  }, [userId, setHistory]);

  return (
    <div className="flex h-full w-full overflow-hidden">
      {/* Collapsible History Sidebar */}
      <HistorySidebar />

      {/* Main Workspace Area */}
      <main
        className={`flex-1 flex flex-col p-4 gap-3 overflow-hidden transition-colors duration-200 ${
          isDark ? 'bg-[var(--bg-app)]' : 'bg-white'
        }`}
      >
        {/* Natural Language Query Intake Box */}
        <NLQueryInput />

        {/* Resizable Split Panels: Left = Monaco SQL Inspector, Right = Execution Result */}
        <div className="flex-1 min-h-0">
          <PanelGroup direction="horizontal">
            {/* Left Panel: Monaco SQL Inspector */}
            <Panel defaultSize={50} minSize={30}>
              <SqlInspector />
            </Panel>

            <PanelResizeHandle className={`w-2 transition-colors duration-200 cursor-col-resize flex items-center justify-center rounded-[var(--radius-control)] ${
              isDark ? 'hover:bg-[var(--accent-primary)]/20' : 'hover:bg-[var(--bg-hover)]'
            }`}>
              <div className={`w-0.5 h-8 rounded-[var(--radius-control)] ${isDark ? 'bg-[var(--border-main)]' : 'bg-[var(--border-main)]'}`} />
            </PanelResizeHandle>

            {/* Right Panel: Result Table / Status OR ER Diagram */}
            <Panel defaultSize={50} minSize={30}>
              {rightPanelTab === 'er_diagram' ? <ERDiagramView /> : <ResultPanel />}
            </Panel>
          </PanelGroup>
        </div>
      </main>
    </div>
  );
};
