// src/store/useAppStore.ts
import { create } from 'zustand';
import type { TargetDialect } from '../types/query';

export type AppTheme = 'dark' | 'light';

interface AppState {
  userId: string;
  setUserId: (id: string) => void;
  targetDialect: TargetDialect;
  setTargetDialect: (dialect: TargetDialect) => void;
  databaseProfile: string;
  setDatabaseProfile: (profile: string) => void;
  isDbConnected: boolean;
  setIsDbConnected: (connected: boolean) => void;
  connectedEngine: string | null;
  setConnectedEngine: (engine: string | null) => void;
  availableDatabases: string[];
  setAvailableDatabases: (dbs: string[]) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  thinkingEnabled: boolean | null;
  setThinkingEnabled: (enabled: boolean | null) => void;
  currentView: 'query' | 'approval';
  setCurrentView: (view: 'query' | 'approval') => void;
  theme: AppTheme;
  setTheme: (theme: AppTheme) => void;
  toggleTheme: () => void;
}

const getStoredUserId = (): string => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('nl2sql_user_id');
    if (saved && saved.trim()) return saved.trim();
  }
  return 'bhuknu';
};

const getStoredTheme = (): AppTheme => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('nl2sql_theme');
    if (saved === 'light' || saved === 'dark') return saved;
  }
  return 'dark';
};

export const useAppStore = create<AppState>((set) => ({
  userId: getStoredUserId(),
  setUserId: (id) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('nl2sql_user_id', id);
    }
    set({ userId: id });
  },
  targetDialect: 'auto',
  setTargetDialect: (dialect) => set({ targetDialect: dialect }),
  databaseProfile: 'test',
  setDatabaseProfile: (profile) => set({ databaseProfile: profile }),
  isDbConnected: false,
  setIsDbConnected: (connected) => set({ isDbConnected: connected }),
  connectedEngine: null,
  setConnectedEngine: (engine) => set({ connectedEngine: engine }),
  availableDatabases: ['test', 'ecommerce_db', 'master_enterprise'],
  setAvailableDatabases: (dbs) => set({ availableDatabases: dbs }),
  selectedModel: 'auto',
  setSelectedModel: (model) => set({ selectedModel: model }),
  thinkingEnabled: false,
  setThinkingEnabled: (enabled) => set({ thinkingEnabled: enabled }),
  currentView: 'query',
  setCurrentView: (view) => set({ currentView: view }),
  theme: getStoredTheme(),
  setTheme: (theme) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('nl2sql_theme', theme);
    }
    set({ theme });
  },
  toggleTheme: () => {
    set((state) => {
      const nextTheme: AppTheme = state.theme === 'dark' ? 'light' : 'dark';
      if (typeof window !== 'undefined') {
        localStorage.setItem('nl2sql_theme', nextTheme);
      }
      return { theme: nextTheme };
    });
  },
}));
