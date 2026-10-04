// src/api/approvalApi.ts
import { apiFetch } from './client';
import type { ApprovalRequest, ApprovalResponse } from '../types/approval';
import { handleMockApproval } from '../mock/mockService';

export async function submitApproval(queryId: string, request: ApprovalRequest): Promise<ApprovalResponse> {
  try {
    return await apiFetch<ApprovalResponse>(`/approval/${encodeURIComponent(queryId)}`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  } catch (error) {
    return handleMockApproval(queryId, request);
  }
}
