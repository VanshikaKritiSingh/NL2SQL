// src/store/useAppStore.ts
import { create } from 'zustand';
import type { TargetDialect } from '../types/query';

export type AppTheme = 'dark' | 'light';

interface AppState {
  userId: string;
  setUserId: (id: string) => void;
  targetDialect: TargetDialect;
  setTargetDialect: (dialect: TargetDialect) => void;
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
  return 'vanshika_analyst';
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
  targetDialect: 'mysql',
  setTargetDialect: (dialect) => set({ targetDialect: dialect }),
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
