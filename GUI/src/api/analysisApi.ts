// src/api/analysisApi.ts
import { apiFetch } from './client';
import type { CostEstimate, SecurityCheck, DiffData } from '../types/approval';
import { MOCK_ALTER_APPROVAL } from '../mock/mockData';

export async function getExplain(queryId: string): Promise<CostEstimate> {
  try {
    return await apiFetch<CostEstimate>(`/explain/${encodeURIComponent(queryId)}`);
  } catch (error) {
    return MOCK_ALTER_APPROVAL.cost_estimate;
  }
}

export async function getSecurityCheck(queryId: string): Promise<SecurityCheck> {
  try {
    return await apiFetch<SecurityCheck>(`/security-check/${encodeURIComponent(queryId)}`);
  } catch (error) {
    return MOCK_ALTER_APPROVAL.security_check;
  }
}

export async function getDiff(queryId: string): Promise<DiffData> {
  try {
    return await apiFetch<DiffData>(`/diff/${encodeURIComponent(queryId)}`);
  } catch (error) {
    return MOCK_ALTER_APPROVAL.diff_data;
  }
}
