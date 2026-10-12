// src/modules/m1/QueryIntakePage.tsx
import React, { useEffect } from 'react';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';
import { HistorySidebar } from './HistorySidebar';
import { NLQueryInput } from './NLQueryInput';
import { SqlInspector } from './SqlInspector';
import { ResultPanel } from './ResultPanel';
import { useAppStore } from '../../store/useAppStore';
import { useQueryStore } from '../../store/useQueryStore';
import { getHistory } from '../../api/queryApi';

export const QueryIntakePage: React.FC = () => {
  const userId = useAppStore((s) => s.userId);
  const theme = useAppStore((s) => s.theme);
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
        className="flex-1 flex flex-col p-4 gap-3 overflow-hidden transition-colors bg-[var(--bg-app)]"
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

            <PanelResizeHandle className="w-2 hover:bg-[var(--accent-glow)] transition-colors cursor-col-resize flex items-center justify-center">
              <div className="w-0.5 h-6 rounded-full bg-[var(--border-main)]" />
            </PanelResizeHandle>

            {/* Right Panel: Result Table / Status */}
            <Panel defaultSize={50} minSize={30}>
              <ResultPanel />
            </Panel>
          </PanelGroup>
        </div>
      </main>
    </div>
  );
};
