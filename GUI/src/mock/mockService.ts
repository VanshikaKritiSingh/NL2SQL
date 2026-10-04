import { QueryRequest, QueryResponse, HistoryItem } from '../types/query';
import { ApprovalPayload, ApprovalRequest, ApprovalResponse } from '../types/approval';
import { SchemaInfo } from '../types/schema';
import { PIPELINE_STAGES, PipelineStageEvent } from '../types/pipeline';
import {
  MOCK_SCHEMA,
  MOCK_SELECT_RESPONSE,
  MOCK_UPDATE_APPROVAL,
  MOCK_ALTER_APPROVAL,
} from './mockData';

let historyStore: HistoryItem[] = [];

export async function simulatePipelineProgress(
  queryId: string,
  requiresApproval: boolean,
  onEvent: (event: PipelineStageEvent) => void
): Promise<void> {
  const stageKeys = Object.keys(PIPELINE_STAGES)
    .map((k) => parseInt(k, 10))
    .sort((a, b) => a - b);

  const totalStages = requiresApproval ? 14 : 16;

  for (let i = 0; i < totalStages; i++) {
    const stageNum = stageKeys[i];
    const stageName = PIPELINE_STAGES[stageNum];

    // Emit stage started
    onEvent({
      query_id: queryId,
      stage_number: stageNum,
      stage_name: stageName,
      status: 'started',
      message: `Running ${stageName}...`,
    });

    // Simulate realistic sub-second latency
    await new Promise((resolve) => setTimeout(resolve, 80));

    // Emit stage completed
    onEvent({
      query_id: queryId,
      stage_number: stageNum,
      stage_name: stageName,
      status: 'completed',
      message: `Completed ${stageName}`,
    });
  }
}

export function processMockQuery(req: QueryRequest): QueryResponse {
  const queryLower = req.query_text.toLowerCase();

  let response: QueryResponse;
  let isMutating = false;

  if (queryLower.includes('add') || queryLower.includes('column') || queryLower.includes('alter') || queryLower.includes('table')) {
    // DDL Alter Flow
    const payload: ApprovalPayload = {
      ...MOCK_ALTER_APPROVAL,
      query_id: `q_alter_${Date.now()}`,
      target_dialect: req.target_dialect,
    };
    response = {
      query_id: payload.query_id,
      status: 'approval_required',
      generated_sql: payload.generated_sql,
      result_data: null,
      approval_payload: payload,
      error_message: null,
      cache_hit: false,
    };
    isMutating = true;
  } else if (
    queryLower.includes('update') ||
    queryLower.includes('increase') ||
    queryLower.includes('price') ||
    queryLower.includes('delete') ||
    queryLower.includes('modify')
  ) {
    // DML Update Flow
    const payload: ApprovalPayload = {
      ...MOCK_UPDATE_APPROVAL,
      query_id: `q_update_${Date.now()}`,
      target_dialect: req.target_dialect,
    };
    response = {
      query_id: payload.query_id,
      status: 'approval_required',
      generated_sql: payload.generated_sql,
      result_data: null,
      approval_payload: payload,
      error_message: null,
      cache_hit: false,
    };
    isMutating = true;
  } else {
    // Read-only SELECT Flow
    response = {
      ...MOCK_SELECT_RESPONSE,
      query_id: `q_select_${Date.now()}`,
    };
  }

  // Save to history
  historyStore.unshift({
    query_id: response.query_id,
    query_text: req.query_text,
    generated_sql: response.generated_sql,
    target_dialect: req.target_dialect,
    status: response.status,
    timestamp: new Date().toISOString(),
    is_mutating: isMutating,
  });

  return response;
}

export function getMockHistory(_userId: string): HistoryItem[] {
  if (historyStore.length === 0) {
    return [
      {
        query_id: 'q_init_001',
        query_text: 'Show me all orders from last month',
        generated_sql: 'SELECT * FROM orders WHERE order_date >= DATE_SUB(NOW(), INTERVAL 1 MONTH);',
        target_dialect: 'mysql',
        status: 'completed',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        is_mutating: false,
      },
    ];
  }
  return historyStore;
}

export function getMockSchema(dialect: string = 'mysql'): SchemaInfo {
  return {
    ...MOCK_SCHEMA,
    dialect,
  };
}

export function handleMockApproval(queryId: string, request: ApprovalRequest): ApprovalResponse {
  const item = historyStore.find((h) => h.query_id === queryId);
  if (item) {
    item.status = request.decision === 'approve' ? 'completed' : 'error';
  }

  if (request.decision === 'approve') {
    return {
      query_id: queryId,
      status: 'approved_executing',
      message: `Query ${queryId} approved: Dolt CAS Commit checkpoint logged and dispatched to target DBMS.`,
    };
  } else {
    return {
      query_id: queryId,
      status: 'rejected_retrying',
      message: `Query ${queryId} rejected. Feedback routed back to SQL model prompt retry gate: "${request.feedback || 'User rejected change'}".`,
    };
  }
}
