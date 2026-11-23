// src/modules/query_intake/QueryIntakePage.tsx
import React, { useEffect } from 'react';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';
import { Table, Database } from 'lucide-react';
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
  const setRightPanelTab = useAppStore((s) => s.setRightPanelTab);
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
        className="flex-1 flex flex-col p-4 gap-3 overflow-hidden transition-colors duration-200 bg-[var(--bg-app)] text-[var(--text-body)]"
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

            {/* Right Panel: Result Table / Status OR ER Diagram with Ghost Slider */}
            <Panel defaultSize={50} minSize={30}>
              <div className="h-full flex flex-col min-h-0">
                {/* Segmented Ghost Slider Selector */}
                <div className="flex items-center justify-between pb-2 mb-0.5 shrink-0 px-0.5">
                  <div className="relative inline-flex items-center p-1 rounded-full bg-[var(--bg-panel-alt)] border border-[var(--border-hairline)] shadow-inner">
                    <button
                      onClick={() => setRightPanelTab('results')}
                      className={`relative z-10 flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-semibold transition-all duration-200 cursor-pointer ${
                        rightPanelTab === 'results'
                          ? 'text-[var(--text-heading)]'
                          : 'text-[var(--text-recessive)] hover:text-[var(--text-heading)]'
                      }`}
                    >
                      <Table className="w-3.5 h-3.5" />
                      <span>Sandbox Results</span>
                    </button>
                    <button
                      onClick={() => setRightPanelTab('er_diagram')}
                      className={`relative z-10 flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-semibold transition-all duration-200 cursor-pointer ${
                        rightPanelTab === 'er_diagram'
                          ? 'text-[var(--text-heading)]'
                          : 'text-[var(--text-recessive)] hover:text-[var(--text-heading)]'
                      }`}
                    >
                      <Database className="w-3.5 h-3.5" />
                      <span>ER Schema Diagram</span>
                    </button>
                    {/* Ghost Slider Track Indicator */}
                    <div
                      className={`absolute top-1 bottom-1 rounded-full bg-[var(--bg-card)] border border-[var(--border-subtle)] shadow-xs transition-all duration-300 pointer-events-none ${
                        rightPanelTab === 'results' ? 'left-1 w-[calc(50%-4px)]' : 'left-[50%] w-[calc(50%-4px)]'
                      }`}
                    />
                  </div>
                  <span className="text-[10px] font-mono text-[var(--text-recessive)] hidden sm:inline">
                    {rightPanelTab === 'results' ? 'Mode: Results Output' : 'Mode: Interactive Schema Graph'}
                  </span>
                </div>

                <div className="flex-1 min-h-0">
                  {rightPanelTab === 'er_diagram' ? <ERDiagramView /> : <ResultPanel />}
                </div>
              </div>
            </Panel>
          </PanelGroup>
        </div>
      </main>
    </div>
  );
};
