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
  softL?: string;
  softD?: string;
}

export const ACCENT_PALETTES: AccentColor[] = [
  {
    id: 'blue',
    name: 'Blue',
    hex: '#2F81F7',
    darkPrimary: '#2F81F7',
    darkSecondary: '#2F81F7',
    darkHover: '#388BFD',
    darkGlow: 'rgba(47, 129, 247, 0.25)',
    lightPrimary: '#0969DA',
    lightSecondary: '#0969DA',
    lightHover: '#0860CA',
    lightGlow: 'rgba(9, 105, 218, 0.15)',
    softL: '#DDF4FF',
    softD: 'rgba(47, 129, 247, 0.14)',
  },
  {
    id: 'green',
    name: 'Green',
    hex: '#3FB950',
    darkPrimary: '#3FB950',
    darkSecondary: '#3FB950',
    darkHover: '#56D364',
    darkGlow: 'rgba(63, 185, 80, 0.25)',
    lightPrimary: '#1A7F37',
    lightSecondary: '#1A7F37',
    lightHover: '#116329',
    lightGlow: 'rgba(26, 127, 55, 0.15)',
    softL: '#DAFBE1',
    softD: 'rgba(63, 185, 80, 0.14)',
  },
  {
    id: 'terracotta',
    name: 'Terracotta',
    hex: '#E07A5F',
    darkPrimary: '#E07A5F',
    darkSecondary: '#E07A5F',
    darkHover: '#F48C71',
    darkGlow: 'rgba(224, 122, 95, 0.25)',
    lightPrimary: '#B84D2B',
    lightSecondary: '#B84D2B',
    lightHover: '#983E20',
    lightGlow: 'rgba(184, 77, 43, 0.15)',
    softL: '#FDECE6',
    softD: 'rgba(224, 122, 95, 0.14)',
  },
  {
    id: 'indigo',
    name: 'Indigo',
    hex: '#818CF8',
    darkPrimary: '#818CF8',
    darkSecondary: '#818CF8',
    darkHover: '#9FA8FF',
    darkGlow: 'rgba(129, 140, 248, 0.25)',
    lightPrimary: '#4F46E5',
    lightSecondary: '#4F46E5',
    lightHover: '#4338CA',
    lightGlow: 'rgba(79, 70, 229, 0.15)',
    softL: '#EEF2FF',
    softD: 'rgba(129, 140, 248, 0.14)',
  },
  {
    id: 'amber',
    name: 'Amber',
    hex: '#D29922',
    darkPrimary: '#D29922',
    darkSecondary: '#D29922',
    darkHover: '#E3B341',
    darkGlow: 'rgba(210, 153, 34, 0.25)',
    lightPrimary: '#9A6700',
    lightSecondary: '#9A6700',
    lightHover: '#7D5300',
    lightGlow: 'rgba(154, 103, 0, 0.15)',
    softL: '#FFF8C5',
    softD: 'rgba(210, 153, 34, 0.14)',
  },
  {
    id: 'slate',
    name: 'Slate',
    hex: '#8B949E',
    darkPrimary: '#8B949E',
    darkSecondary: '#8B949E',
    darkHover: '#A1AAB4',
    darkGlow: 'rgba(139, 148, 158, 0.25)',
    lightPrimary: '#24292F',
    lightSecondary: '#24292F',
    lightHover: '#1B1F24',
    lightGlow: 'rgba(36, 41, 47, 0.15)',
    softL: '#EAEEF2',
    softD: 'rgba(139, 148, 158, 0.16)',
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
  return 'blue';
};

export const applyAccentTokensToDocument = (accentId: string, currentTheme: AppTheme) => {
  if (typeof document === 'undefined') return;
  const palette = ACCENT_PALETTES.find((p) => p.id === accentId) || ACCENT_PALETTES[0];
  const root = document.documentElement;
  const isDark = currentTheme === 'dark';
  const primary = isDark ? palette.darkPrimary : palette.lightPrimary;
  const soft = isDark ? (palette.softD || 'rgba(47, 129, 247, 0.14)') : (palette.softL || '#DDF4FF');

  root.style.setProperty('--accent', primary);
  root.style.setProperty('--accent-primary', primary);
  root.style.setProperty('--accent-secondary', primary);
  root.style.setProperty('--accent-soft', soft);
  root.style.setProperty('--accent-hover', isDark ? palette.darkHover : palette.lightHover);
  root.style.setProperty('--accent-violet-glow', palette.darkGlow);
  root.style.setProperty('--border-focus', primary);
  root.style.setProperty('--btn-primary-bg', primary);
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
