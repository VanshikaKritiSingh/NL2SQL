// src/types/pipeline.ts
export type PipelineStageStatus = 'pending' | 'started' | 'completed' | 'skipped' | 'error';

export interface PipelineStageEvent {
  query_id: string;
  stage_number: number;
  stage_name: string;
  status: PipelineStageStatus;
  message?: string | null;
  data?: Record<string, any> | null;
}

export const PIPELINE_STAGES: Record<number, string> = {
  1: 'Natural Language Intake',
  2: 'Rate Limiter & Budget Check',
  3: 'Audit & Telemetry Logger',
  4: 'Semantic Query Cache',
  5: 'Schema Linker & Relationship Graph',
  6: 'SQL Generator',
  7: 'Query Sanitizer & AST Parser',
  8: 'Dialect Transpiler & Normalizer',
  9: 'Static Validator & Rule Checker',
  10: 'Execution Cost Estimator',
  11: 'Concurrency & Deadlock Analyzer',
  12: 'Safety Execution Router',
  13: 'Sandbox Execution & Replica',
  14: 'Human Approval Gate',
  15: 'Transaction Wrapper & Checkpoint',
  16: 'Database Dispatcher & Formatter',
};
