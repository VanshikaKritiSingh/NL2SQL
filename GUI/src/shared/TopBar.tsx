// src/shared/TopBar.tsx
import React, { useState } from 'react';
import { Database, User, ShieldAlert, Sparkles, Sun, Moon, Check, Edit2, PlayCircle, Cpu } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { useQueryStore } from '../store/useQueryStore';
import { usePipelineStore } from '../store/usePipelineStore';
import { DialectSelector } from './DialectSelector';
import { MOCK_UPDATE_APPROVAL } from '../mock/mockData';

export const TopBar: React.FC = () => {
  const userId = useAppStore((s) => s.userId);
  const setUserId = useAppStore((s) => s.setUserId);
  const currentView = useAppStore((s) => s.currentView);
  const setCurrentView = useAppStore((s) => s.setCurrentView);
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const wsConnected = usePipelineStore((s) => s.wsConnected);
  const approvalPayload = useQueryStore((s) => s.approvalPayload);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);

  const [isEditingUser, setIsEditingUser] = useState(false);
  const [tempUserName, setTempUserName] = useState(userId);

  const handleUserSave = () => {
    const trimmed = tempUserName.trim();
    if (trimmed) {
      setUserId(trimmed);
    } else {
      setTempUserName(userId);
    }
    setIsEditingUser(false);
  };

  const handleOpenApprovalGate = () => {
    if (!approvalPayload) {
      setApprovalPayload(MOCK_UPDATE_APPROVAL);
    }
    setCurrentView('approval');
  };

  const isDark = theme === 'dark';

  return (
    <header
      className={`h-14 border-b px-4 flex items-center justify-between shrink-0 transition-colors ${
        isDark
          ? 'border-slate-800 bg-slate-900/95 text-slate-100'
          : 'border-slate-200 bg-white/95 text-slate-800 shadow-xs'
      }`}
    >
      {/* Brand & Subtitle */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-md shadow-indigo-500/20">
          <Database className="w-4 h-4 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm tracking-tight">NL2SQL Studio</span>
          </div>
          <p className={`text-[11px] font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Natural Language SQL Workspace & Schema Safety Gate
          </p>
        </div>
      </div>

      {/* Center Nav: Function Tabs */}
      <div
        className={`flex items-center gap-1 p-1 rounded-lg border text-xs ${
          isDark ? 'bg-slate-800/80 border-slate-700/60' : 'bg-slate-100 border-slate-200'
        }`}
      >
        <button
          onClick={() => setCurrentView('query')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all cursor-pointer ${
            currentView === 'query'
              ? 'bg-indigo-600 text-white shadow'
              : isDark
              ? 'text-slate-400 hover:text-slate-200'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          title="Natural Language Query Intake & SQL Inspector"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Query Intake</span>
        </button>

        <button
          onClick={() => setCurrentView('stepper')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all cursor-pointer ${
            currentView === 'stepper'
              ? 'bg-cyan-600 text-white shadow'
              : isDark
              ? 'text-slate-400 hover:text-slate-200'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          title="Interactive CLEF + Qwen LoRA + Transpiler Pipeline Stepper"
        >
          <PlayCircle className="w-3.5 h-3.5" />
          <span>Pipeline Stepper</span>
        </button>

        <button
          onClick={handleOpenApprovalGate}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all cursor-pointer ${
            currentView === 'approval'
              ? 'bg-rose-600 text-white shadow'
              : isDark
              ? 'text-slate-400 hover:text-slate-200'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          title="Interactive ER Visualizer & Human Approval Gate for Mutating Statements"
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Approval Gate</span>
        </button>

        <button
          onClick={() => setCurrentView('finetune')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all cursor-pointer ${
            currentView === 'finetune'
              ? 'bg-purple-600 text-white shadow'
              : isDark
              ? 'text-slate-400 hover:text-slate-200'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          title="Qwen2.5-Coder QLoRA Fine-Tuning & Spider Benchmark Studio"
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>Fine-Tuning Studio</span>
        </button>
      </div>

      {/* Right Controls: DBMS Dialect, User Profile, Theme Switcher, Engine Status */}
      <div className="flex items-center gap-2.5">
        {/* Dialect Selector */}
        <DialectSelector />

        {/* User Name Input / Profile (Fully Editable) */}
        <div
          className={`flex items-center gap-1.5 border rounded-lg px-2.5 py-1 text-xs transition-all ${
            isDark
              ? 'bg-slate-800/90 border-slate-700/80 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500/50'
              : 'bg-slate-100 border-slate-300 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500/50'
          }`}
        >
          <User className={`w-3.5 h-3.5 ${isDark ? 'text-slate-400' : 'text-slate-500'}`} />
          <span className={`text-[11px] font-medium ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>User:</span>
          {isEditingUser ? (
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={tempUserName}
                autoFocus
                onChange={(e) => setTempUserName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleUserSave();
                  if (e.key === 'Escape') {
                    setTempUserName(userId);
                    setIsEditingUser(false);
                  }
                }}
                onBlur={handleUserSave}
                className={`w-28 bg-transparent font-mono text-xs focus:outline-none select-text ${
                  isDark ? 'text-indigo-300' : 'text-indigo-700'
                }`}
                placeholder="Enter user name..."
              />
              <button
                type="button"
                onClick={handleUserSave}
                className="text-emerald-400 hover:text-emerald-300 p-0.5 cursor-pointer"
                title="Save user name"
              >
                <Check className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <div
              onClick={() => {
                setTempUserName(userId);
                setIsEditingUser(true);
              }}
              className="flex items-center gap-1 cursor-pointer group"
              title="Click to edit user name"
            >
              <span
                className={`font-mono text-xs max-w-[120px] truncate ${
                  isDark ? 'text-slate-200 group-hover:text-indigo-300' : 'text-slate-800 group-hover:text-indigo-600'
                }`}
              >
                {userId}
              </span>
              <Edit2 className="w-2.5 h-2.5 text-slate-500 group-hover:text-indigo-400 opacity-60 group-hover:opacity-100 transition-opacity" />
            </div>
          )}
        </div>

        {/* Theme Toggle Button (Light / Dark) */}
        <button
          onClick={toggleTheme}
          className={`p-1.5 rounded-lg border transition-all cursor-pointer ${
            isDark
              ? 'bg-slate-800/90 border-slate-700/80 text-amber-400 hover:bg-slate-700 hover:text-amber-300'
              : 'bg-slate-100 border-slate-300 text-indigo-600 hover:bg-slate-200 hover:text-indigo-700'
          }`}
          title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          aria-label="Toggle theme"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Engine Status Indicator */}
        <div
          className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[11px] ${
            isDark ? 'bg-slate-800/40 border-slate-700/40' : 'bg-slate-100 border-slate-200'
          }`}
          title={wsConnected ? 'WebSocket live stream connected' : 'Client Simulation Engine active'}
        >
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-emerald-500'}`} />
          <span className={`font-mono text-[10px] ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            {wsConnected ? 'LIVE WS' : 'SIMULATION'}
          </span>
        </div>
      </div>
    </header>
  );
};
