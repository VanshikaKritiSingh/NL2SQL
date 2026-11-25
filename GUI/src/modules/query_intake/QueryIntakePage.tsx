// src/modules/query_intake/QueryIntakePage.tsx — Primer IDE split workspace
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
  const rightPanelTab = useAppStore((s) => s.rightPanelTab);
  const setRightPanelTab = useAppStore((s) => s.setRightPanelTab);
  const setHistory = useQueryStore((s) => s.setHistory);

  useEffect(() => {
    getHistory(userId).then(setHistory).catch(() => {});
  }, [userId, setHistory]);

  const tabCls = (active: boolean) =>
    `relative h-full px-[10px] text-[12.5px] font-medium cursor-pointer bg-transparent border-0 border-b-2 transition-colors flex items-center gap-1.5 ${
      active
        ? 'text-[var(--text-heading)] font-semibold border-b-[var(--accent-primary)]'
        : 'text-[var(--text-recessive)] border-b-transparent hover:text-[var(--text-heading)]'
    }`;

  return (
    <div className="flex h-full w-full overflow-hidden bg-[var(--bg-canvas)]">
      <HistorySidebar />

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Split panes: SQL Inspector | Results / ER */}
        <div className="flex-1 min-h-0">
          <PanelGroup direction="horizontal">
            <Panel defaultSize={46} minSize={25}>
              <SqlInspector />
            </Panel>

            <PanelResizeHandle className="w-px bg-[var(--border-hairline)] hover:bg-[var(--accent-primary)] transition-colors cursor-col-resize relative">
              <div className="absolute inset-y-0 -left-1 -right-1" />
            </PanelResizeHandle>

            <Panel defaultSize={54} minSize={25}>
              <div className="h-full flex flex-col min-h-0 bg-[var(--bg-canvas)]">
                {/* Primer underline tab strip */}
                <div className="h-9 shrink-0 flex items-stretch border-b border-[var(--border-hairline)] bg-[var(--bg-panel)]">
                  <div className="flex items-stretch">
                    <button onClick={() => setRightPanelTab('results')} className={tabCls(rightPanelTab === 'results')}>
                      <span>Results</span>
                    </button>
                    <button onClick={() => setRightPanelTab('er_diagram')} className={tabCls(rightPanelTab === 'er_diagram')}>
                      <span>ER Schema</span>
                    </button>
                  </div>
                  <div className="flex-1" />
                  <span className="font-mono text-[11px] text-[var(--text-recessive)] self-center pr-3 hidden sm:inline">
                    {rightPanelTab === 'results' ? 'result set' : 'schema graph'}
                  </span>
                </div>

                <div className="flex-1 min-h-0 overflow-hidden">
                  {rightPanelTab === 'er_diagram' ? <ERDiagramView /> : <ResultPanel />}
                </div>
              </div>
            </Panel>
          </PanelGroup>
        </div>

        {/* Bottom prompt composer */}
        <NLQueryInput />
      </main>
    </div>
  );
};
