// src/api/queryApi.ts
import { apiFetch } from './client';
import type { QueryRequest, QueryResponse, HistoryItem } from '../types/query';
import { processMockQuery, getMockHistory, simulatePipelineProgress } from '../mock/mockService';
import { usePipelineStore } from '../store/usePipelineStore';

export async function submitQuery(request: QueryRequest): Promise<QueryResponse> {
  const { startPipeline, updateStage } = usePipelineStore.getState();

  try {
    const response = await apiFetch<QueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return response;
  } catch (error) {
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
}

export async function getHistory(userId: string): Promise<HistoryItem[]> {
  try {
    return await apiFetch<HistoryItem[]>(`/query/history/${encodeURIComponent(userId)}`);
  } catch (error) {
    return getMockHistory(userId);
  }
}
