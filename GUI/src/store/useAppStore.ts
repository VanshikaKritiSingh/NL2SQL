// src/store/useAppStore.ts
import { create } from 'zustand';
import type { TargetDialect } from '../types/query';

export type AppTheme = 'dark' | 'light';

export interface AccentColor {
  id: string;
  name: string;
  hex: string;
  darkPrimary: string;
  darkSecondary: string;
  darkHover: string;
  darkGlow: string;
  lightPrimary: string;
  lightSecondary: string;
  lightHover: string;
  lightGlow: string;
}

export const ACCENT_PALETTES: AccentColor[] = [
  {
    id: 'violet',
    name: 'Violet',
    hex: '#8b5cf6',
    darkPrimary: '#c4b5fd',
    darkSecondary: '#a78bfa',
    darkHover: '#ddd6fe',
    darkGlow: 'rgba(124, 58, 237, 0.35)',
    lightPrimary: '#6d28d9',
    lightSecondary: '#7c3aed',
    lightHover: '#5b21b6',
    lightGlow: 'rgba(109, 40, 217, 0.15)',
  },
  {
    id: 'cyan',
    name: 'Cyan',
    hex: '#06b6d4',
    darkPrimary: '#67e8f9',
    darkSecondary: '#22d3ee',
    darkHover: '#a5f3fc',
    darkGlow: 'rgba(6, 182, 212, 0.35)',
    lightPrimary: '#0e7490',
    lightSecondary: '#0891b2',
    lightHover: '#155e75',
    lightGlow: 'rgba(14, 116, 144, 0.15)',
  },
  {
    id: 'emerald',
    name: 'Emerald',
    hex: '#10b981',
    darkPrimary: '#6ee7b7',
    darkSecondary: '#34d399',
    darkHover: '#a7f3d0',
    darkGlow: 'rgba(16, 185, 129, 0.35)',
    lightPrimary: '#047857',
    lightSecondary: '#059669',
    lightHover: '#065f46',
    lightGlow: 'rgba(4, 120, 87, 0.15)',
  },
  {
    id: 'amber',
    name: 'Amber',
    hex: '#f59e0b',
    darkPrimary: '#fcd34d',
    darkSecondary: '#fbbf24',
    darkHover: '#fde68a',
    darkGlow: 'rgba(245, 158, 11, 0.35)',
    lightPrimary: '#b45309',
    lightSecondary: '#d97706',
    lightHover: '#92400e',
    lightGlow: 'rgba(180, 83, 9, 0.15)',
  },
  {
    id: 'rose',
    name: 'Rose',
    hex: '#f43f5e',
    darkPrimary: '#fda4af',
    darkSecondary: '#fb7185',
    darkHover: '#fecdd3',
    darkGlow: 'rgba(244, 63, 94, 0.35)',
    lightPrimary: '#be123c',
    lightSecondary: '#e11d48',
    lightHover: '#9f1239',
    lightGlow: 'rgba(190, 18, 60, 0.15)',
  },
  {
    id: 'silver',
    name: 'Silver',
    hex: '#94a3b8',
    darkPrimary: '#f1f5f9',
    darkSecondary: '#cbd5e1',
    darkHover: '#ffffff',
    darkGlow: 'rgba(148, 163, 184, 0.35)',
    lightPrimary: '#1e293b',
    lightSecondary: '#334155',
    lightHover: '#0f172a',
    lightGlow: 'rgba(30, 41, 59, 0.15)',
  },
];

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
  rightPanelTab: 'results' | 'er_diagram';
  setRightPanelTab: (tab: 'results' | 'er_diagram') => void;
  toggleRightPanelTab: () => void;
  theme: AppTheme;
  setTheme: (theme: AppTheme) => void;
  toggleTheme: () => void;
  accentColor: string;
  setAccentColor: (accentId: string) => void;
}

const getStoredUserId = (): string => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('nl2sql_user_id');
    if (saved && saved.trim()) return saved.trim();
  }
  return 'default_user';
};

const getStoredTheme = (): AppTheme => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('nl2sql_theme');
    if (saved === 'light' || saved === 'dark') return saved;
  }
  return 'dark';
};

const getStoredAccent = (): string => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('nl2sql_accent');
    if (saved && ACCENT_PALETTES.some((p) => p.id === saved)) return saved;
  }
  return 'violet';
};

export const applyAccentTokensToDocument = (accentId: string, currentTheme: AppTheme) => {
  if (typeof document === 'undefined') return;
  const palette = ACCENT_PALETTES.find((p) => p.id === accentId) || ACCENT_PALETTES[0];
  const root = document.documentElement;
  if (currentTheme === 'dark') {
    root.style.setProperty('--accent-primary', palette.darkPrimary);
    root.style.setProperty('--accent-secondary', palette.darkSecondary);
    root.style.setProperty('--accent-hover', palette.darkHover);
    root.style.setProperty('--accent-violet-glow', palette.darkGlow);
    root.style.setProperty('--border-focus', palette.darkPrimary);
  } else {
    root.style.setProperty('--accent-primary', palette.lightPrimary);
    root.style.setProperty('--accent-secondary', palette.lightSecondary);
    root.style.setProperty('--accent-hover', palette.lightHover);
    root.style.setProperty('--accent-violet-glow', palette.lightGlow);
    root.style.setProperty('--border-focus', palette.lightPrimary);
  }
};

export const useAppStore = create<AppState>((set, get) => ({
  userId: getStoredUserId(),
  setUserId: (id) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('nl2sql_user_id', id);
    }
    set({ userId: id });
  },
  targetDialect: 'auto',
  setTargetDialect: (dialect) => set({ targetDialect: dialect }),
  databaseProfile: '__none__',
  setDatabaseProfile: (profile) => set({ databaseProfile: profile }),
  isDbConnected: false,
  setIsDbConnected: (connected) => set({ isDbConnected: connected }),
  connectedEngine: null,
  setConnectedEngine: (engine) => set({ connectedEngine: engine }),
  availableDatabases: [],
  setAvailableDatabases: (dbs) => set({ availableDatabases: dbs }),
  selectedModel: 'auto',
  setSelectedModel: (model) => set({ selectedModel: model }),
  thinkingEnabled: false,
  setThinkingEnabled: (enabled) => set({ thinkingEnabled: enabled }),
  currentView: 'query',
  setCurrentView: (view) => set({ currentView: view }),
  rightPanelTab: 'results',
  setRightPanelTab: (tab) => set({ rightPanelTab: tab }),
  toggleRightPanelTab: () => set((state) => ({
    rightPanelTab: state.rightPanelTab === 'er_diagram' ? 'results' : 'er_diagram',
  })),
  theme: getStoredTheme(),
  setTheme: (theme) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('nl2sql_theme', theme);
      document.documentElement.setAttribute('data-theme', theme);
      if (theme === 'dark') {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      } else {
        document.documentElement.classList.add('light');
        document.documentElement.classList.remove('dark');
      }
    }
    applyAccentTokensToDocument(get().accentColor, theme);
    set({ theme });
  },
  toggleTheme: () => {
    const nextTheme: AppTheme = get().theme === 'dark' ? 'light' : 'dark';
    get().setTheme(nextTheme);
  },
  accentColor: getStoredAccent(),
  setAccentColor: (accentId) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('nl2sql_accent', accentId);
    }
    applyAccentTokensToDocument(accentId, get().theme);
    set({ accentColor: accentId });
  },
}));
