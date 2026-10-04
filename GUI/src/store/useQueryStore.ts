// src/store/useQueryStore.ts
import { create } from 'zustand';
import type { HistoryItem, QueryResponse } from '../types/query';
import type { ApprovalPayload } from '../types/approval';

interface QueryState {
  currentQueryId: string | null;
  currentQueryText: string;
  isSubmitting: boolean;
  lastResponse: QueryResponse | null;
  approvalPayload: ApprovalPayload | null;
  history: HistoryItem[];
  historySidebarOpen: boolean;

  setCurrentQueryText: (text: string) => void;
  setSubmitting: (submitting: boolean) => void;
  setLastResponse: (response: QueryResponse | null) => void;
  setApprovalPayload: (payload: ApprovalPayload | null) => void;
  setHistory: (items: HistoryItem[]) => void;
  addToHistory: (item: HistoryItem) => void;
  toggleHistorySidebar: () => void;
  clearResults: () => void;
}

export const useQueryStore = create<QueryState>((set) => ({
  currentQueryId: null,
  currentQueryText: '',
  isSubmitting: false,
  lastResponse: null,
  approvalPayload: null,
  history: [],
  historySidebarOpen: true,

  setCurrentQueryText: (text) => set({ currentQueryText: text }),
  setSubmitting: (submitting) => set({ isSubmitting: submitting }),
  setLastResponse: (response) =>
    set({
      lastResponse: response,
      currentQueryId: response ? response.query_id : null,
      isSubmitting: false,
    }),
  setApprovalPayload: (payload) => set({ approvalPayload: payload }),
  setHistory: (items) => set({ history: items }),
  addToHistory: (item) =>
    set((state) => ({ history: [item, ...state.history.filter((h) => h.query_id !== item.query_id)] })),
  toggleHistorySidebar: () =>
    set((state) => ({ historySidebarOpen: !state.historySidebarOpen })),
  clearResults: () =>
    set({ lastResponse: null, approvalPayload: null, currentQueryId: null }),
}));
