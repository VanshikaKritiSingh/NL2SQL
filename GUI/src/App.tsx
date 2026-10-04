// src/App.tsx
import React, { useEffect } from 'react';
import { TopBar } from './shared/TopBar';
import { StatusBar } from './shared/StatusBar';
import { QueryIntakePage } from './modules/m1/QueryIntakePage';
import { ApprovalGatePage } from './modules/m14/ApprovalGatePage';
import { useAppStore } from './store/useAppStore';
import { useQueryStore } from './store/useQueryStore';
import { useWebSocket } from './hooks/useWebSocket';
import { MOCK_UPDATE_APPROVAL } from './mock/mockData';

export default function App() {
  const currentView = useAppStore((s) => s.currentView);
  const setCurrentView = useAppStore((s) => s.setCurrentView);
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const clearResults = useQueryStore((s) => s.clearResults);
  const setHistory = useQueryStore((s) => s.setHistory);

  // Initialize live WebSocket pipeline streaming
  useWebSocket();

  // Keep HTML document theme class synchronized
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
  }, [theme]);

  // Bind desktop native application menu actions (File / View / Help)
  useEffect(() => {
    if (typeof window !== 'undefined' && window.electronAPI?.onMenuAction) {
      const unsubscribe = window.electronAPI.onMenuAction((action: string) => {
        if (action === 'menu-new-query') {
          clearResults();
          setCurrentView('query');
        } else if (action === 'menu-clear-history') {
          setHistory([]);
        } else if (action === 'menu-view-query') {
          setCurrentView('query');
        } else if (action === 'menu-view-approval') {
          setApprovalPayload(MOCK_UPDATE_APPROVAL);
          setCurrentView('approval');
        } else if (action === 'menu-toggle-theme') {
          toggleTheme();
        }
      });
      return unsubscribe;
    }
  }, [clearResults, setCurrentView, setHistory, setApprovalPayload, toggleTheme]);

  const isDark = theme === 'dark';

  return (
    <div
      className={`h-screen w-screen flex flex-col overflow-hidden transition-colors ${
        isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-100 text-slate-800'
      }`}
    >
      {/* Global Top Bar */}
      <TopBar />

      {/* Main View Router */}
      <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
        {currentView === 'query' ? <QueryIntakePage /> : <ApprovalGatePage />}
      </main>

      {/* Cross-Cutting Observability Status Bar */}
      <StatusBar />
    </div>
  );
}
