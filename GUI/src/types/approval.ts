// src/types/approval.ts
export type RiskTier = 'low' | 'medium' | 'high' | 'critical';

export interface ImpactedTable {
  name: string;
  impact_level: 'direct' | 'referenced';
  operation?: string | null;
}

export interface CostEstimate {
  estimated_rows: number;
  estimated_cost: number;
  scan_type: string;
  warnings: string[];
}

export interface SecurityCheck {
  deadlock_risk: 'none' | 'low' | 'medium' | 'high';
  lock_level: string;
  privilege_ok: boolean;
  flags: string[];
}

export interface DmlRowDiff {
  row_id: string | number;
  columns: Record<string, { before: any; after: any }>;
  change_type: 'insert' | 'update' | 'delete';
}

export interface DiffData {
  diff_type: 'ddl' | 'dml' | 'none';
  ddl_before: string | null;
  ddl_after: string | null;
  dml_rows: DmlRowDiff[] | null;
}

export interface ApprovalPayload {
  query_id: string;
  generated_sql: string;
  target_dialect: string;
  risk_tier: RiskTier;
  impacted_tables: ImpactedTable[];
  cost_estimate: CostEstimate;
  security_check: SecurityCheck;
  diff_data: DiffData;
}

export interface ApprovalRequest {
  query_id: string;
  decision: 'approve' | 'reject';
  feedback: string | null;
  user_id: string;
}

export interface ApprovalResponse {
  query_id: string;
  status: 'approved_executing' | 'rejected_retrying' | 'rejected_final';
  message: string;
}
