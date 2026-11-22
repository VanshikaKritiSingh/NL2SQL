// src/api/queryApi.ts
import { apiFetch } from './client';
import type { QueryRequest, QueryResponse, HistoryItem } from '../types/query';
import { processMockQuery, getMockHistory, simulatePipelineProgress } from '../mock/mockService';
import { usePipelineStore } from '../store/usePipelineStore';

// In development or when explicitly enabled, allow fallback if mock is desired;
// otherwise rethrow so backend failures surface immediately.
const USE_MOCK_FALLBACK = (import.meta as any).env?.DEV && (import.meta as any).env?.VITE_USE_MOCK === 'true';

export async function submitQuery(request: QueryRequest): Promise<QueryResponse> {
  const { startPipeline, updateStage } = usePipelineStore.getState();

  try {
    const response = await apiFetch<QueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return response;
  } catch (error) {
    if (USE_MOCK_FALLBACK) {
      console.warn('[NL2SQL API] Backend request failed. Falling back to mock service (VITE_USE_MOCK=true):', error);
      // Standalone fallback: execute via mock service and simulate WebSocket pipeline
      const mockResponse = processMockQuery(request);
      startPipeline(mockResponse.query_id);

      const requiresApproval = mockResponse.status === 'approval_required';

      // Run async pipeline simulation in background
      simulatePipelineProgress(
        mockResponse.query_id,
        requiresApproval,
        (event) => {
          updateStage(event);
        }
      );

      return mockResponse;
    }
    console.error('[NL2SQL API] Query submission failed:', error);
    throw error;
  }
}

export async function getHistory(userId: string): Promise<HistoryItem[]> {
  try {
    return await apiFetch<HistoryItem[]>(`/query/history/${encodeURIComponent(userId)}`);
  } catch (error) {
    if (USE_MOCK_FALLBACK) {
      console.warn('[NL2SQL API] History fetch failed. Falling back to mock history (VITE_USE_MOCK=true):', error);
      return getMockHistory(userId);
    }
    console.error('[NL2SQL API] History fetch failed:', error);
    throw error;
  }
}

export async function deleteHistoryItemApi(userId: string, queryId: string): Promise<void> {
  try {
    await apiFetch(`/query/history/${encodeURIComponent(userId)}/${encodeURIComponent(queryId)}`, {
      method: 'DELETE',
    });
  } catch (error) {
    // Fallback: handled client-side in Zustand store
  }
}

export async function clearHistoryApi(userId: string): Promise<void> {
  try {
    await apiFetch(`/query/history/${encodeURIComponent(userId)}`, {
      method: 'DELETE',
    });
  } catch (error) {
    // Fallback: handled client-side in Zustand store
  }
}
