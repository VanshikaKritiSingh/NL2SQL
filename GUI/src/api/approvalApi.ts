// src/api/approvalApi.ts
import { apiFetch } from './client';
import type { ApprovalRequest, ApprovalResponse } from '../types/approval';
import { handleMockApproval } from '../mock/mockService';

const USE_MOCK_FALLBACK = (import.meta as any).env?.DEV && (import.meta as any).env?.VITE_USE_MOCK === 'true';

export async function submitApproval(queryId: string, request: ApprovalRequest): Promise<ApprovalResponse> {
  try {
    return await apiFetch<ApprovalResponse>(`/approval/${encodeURIComponent(queryId)}`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  } catch (error) {
    if (USE_MOCK_FALLBACK) {
      console.warn('[NL2SQL API] Approval request failed. Falling back to mock service (VITE_USE_MOCK=true):', error);
      return handleMockApproval(queryId, request);
    }
    console.error('[NL2SQL API] Approval request failed:', error);
    throw error;
  }
}
