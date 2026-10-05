// src/types/query.ts
export type TargetDialect =
  | 'auto'
  | 'postgres'
  | 'mysql'
  | 'sqlite'
  | 'oracle'
  | 'sqlserver'
  | 'mariadb'
  | 'duckdb'
  | 'snowflake'
  | 'bigquery'
  | 'clickhouse'
  | 'access'
  | 'mongodb'
  | 'couchbase'
  | 'opencypher'
  | 'influxql'
  | 'timescaledb';

export interface QueryRequest {
  user_id: string;
  query_text: string;
  target_dialect: TargetDialect;
  database_profile?: string;
  dry_run_only?: boolean;
}

export interface ResultData {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
}

export interface QueryResponse {
  query_id: string;
  status: 'processing' | 'completed' | 'approval_required' | 'error' | 'rate_limited';
  generated_sql: string | null;
  result_data: ResultData | null;
  approval_payload: any | null;
  error_message: string | null;
  cache_hit: boolean;
  database_profile?: string;
  is_live_db_connected?: boolean;
  execution_mode?: string;
}

export interface HistoryItem {
  query_id: string;
  query_text: string;
  generated_sql: string | null;
  target_dialect: string;
  status: 'processing' | 'completed' | 'approval_required' | 'error' | 'rate_limited';
  timestamp: string;
  is_mutating: boolean;
  database_profile?: string;
}
