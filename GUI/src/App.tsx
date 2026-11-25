// src/App.tsx
import React, { useEffect } from 'react';
import { TopBar } from './shared/TopBar';
import { StatusBar } from './shared/StatusBar';
import { QueryIntakePage } from './modules/query_intake/QueryIntakePage';
import { ApprovalGatePage } from './modules/approval_gate/ApprovalGatePage';
import { useAppStore, applyAccentTokensToDocument } from './store/useAppStore';
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

  const accentColor = useAppStore((s) => s.accentColor);

  // Initialize live WebSocket pipeline streaming
  useWebSocket();

  // Keep HTML document theme attribute, accent tokens, and meta tag synchronized
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    // Also keep legacy class for any remaining Tailwind dark: prefixes
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
    // Apply selected accent color tokens
    applyAccentTokensToDocument(accentColor, theme);

    // Sync theme-color meta tag
    const metaTheme = document.querySelector('meta[name="theme-color"]');
    if (metaTheme) {
      metaTheme.setAttribute('content', theme === 'dark' ? '#121212' : '#faf8f3');
    }
  }, [theme, accentColor]);

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
    <div className={`h-screen w-screen flex flex-col overflow-hidden transition-colors duration-200 bg-[var(--bg-canvas)] text-[var(--text-main)]`}>
      {/* Global Top Bar */}
      <TopBar />

      {/* Main View Router */}
      <main id="main-content" className="flex-1 min-h-0 flex flex-col overflow-hidden">
        {currentView === 'query' && <QueryIntakePage />}
        {currentView === 'approval' && <ApprovalGatePage />}
      </main>

      {/* Cross-Cutting Observability Status Bar */}
      <StatusBar />
    </div>
  );
}
