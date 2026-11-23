// src/types/query.ts
export type TargetDialect =
  | 'auto'
  | 'postgres'
  | 'mysql'
  | 'sqlite'
  | 'duckdb'
  | 'clickhouse'
  | 'mongodb'
  | 'opencypher'
  | 'redis'
  | 'cassandra'
  | 'custom';

export interface QueryRequest {
  user_id: string;
  query_text: string;
  target_dialect: TargetDialect;
  database_profile?: string;
  dry_run_only?: boolean;
  model_name?: string;
  thinking_enabled?: boolean | null;
}

export interface ResultData {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
}

export interface BackendCommandBlock {
  command: string;
  type: string;
  reason?: string;
}

export interface QueryResponse {
  query_id: string;
  status: 'processing' | 'completed' | 'approval_required' | 'error' | 'rate_limited' | 'refusal';
  generated_sql: string | null;
  result_data: ResultData | null;
  approval_payload: any | null;
  error_message: string | null;
  cache_hit: boolean;
  database_profile?: string;
  is_live_db_connected?: boolean;
  execution_mode?: string;
  model_name?: string;
  selected_dialect?: string;
  dialect_reason?: string;
  command_blocks?: BackendCommandBlock[];
}

export interface HistoryItem {
  query_id: string;
  query_text: string;
  generated_sql: string | null;
  target_dialect: string;
  status: 'processing' | 'completed' | 'approval_required' | 'error' | 'rate_limited' | 'refusal';
  timestamp: string;
  is_mutating: boolean;
  database_profile?: string;
  selected_dialect?: string;
  dialect_reason?: string;
  command_blocks?: BackendCommandBlock[];
}
