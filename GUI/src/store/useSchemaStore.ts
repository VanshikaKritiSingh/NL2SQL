// src/store/useSchemaStore.ts — Centralized live schema state for ER Diagram Visualizer
import { create } from 'zustand';
import type { SchemaInfo } from '../types/schema';

interface SchemaState {
  /** The current schema used by the ER Diagram */
  schema: SchemaInfo | null;
  /** Monotonically increasing counter — bump to force ER diagram refresh */
  schemaVersion: number;
  /** Whether a schema fetch is in progress */
  isFetching: boolean;
  /** Error message from last fetch attempt */
  fetchError: string | null;
  /** Timestamp of last successful fetch */
  lastFetchedAt: number | null;

  setSchema: (schema: SchemaInfo | null) => void;
  setFetching: (fetching: boolean) => void;
  setFetchError: (error: string | null) => void;
  /** Bump version to signal that schema should be refetched (e.g. after CREATE TABLE, INSERT, ALTER) */
  bumpSchemaVersion: () => void;
  /** Full update: set schema + clear error + mark timestamp */
  updateSchema: (schema: SchemaInfo) => void;
}

export const useSchemaStore = create<SchemaState>((set) => ({
  schema: null,
  schemaVersion: 0,
  isFetching: false,
  fetchError: null,
  lastFetchedAt: null,

  setSchema: (schema) => set({ schema }),
  setFetching: (fetching) => set({ isFetching: fetching }),
  setFetchError: (error) => set({ fetchError: error }),
  bumpSchemaVersion: () =>
    set((state) => ({ schemaVersion: state.schemaVersion + 1 })),
  updateSchema: (schema) =>
    set({
      schema,
      fetchError: null,
      lastFetchedAt: Date.now(),
    }),
}));
