// src/modules/approval_gate/ApprovalGatePage.tsx — Clean, Focused Approval Gate
import React, { useEffect, useState } from 'react';
import { ArrowLeft, ShieldAlert, Database, FileText, GitCompare } from 'lucide-react';
import { ERDiagramPanel } from './ERDiagramPanel';
import { SqlViewPanel } from './SqlViewPanel';
import { DiffPanel } from './DiffPanel';
import { TelemetryPanel } from './TelemetryPanel';
import { ApprovalActions } from './ApprovalActions';
import { useQueryStore } from '../../store/useQueryStore';
import { useAppStore } from '../../store/useAppStore';
import { getLiveSchema } from '../../api/schemaApi';
import { RiskBadge } from '../../shared/RiskBadge';
import { MOCK_UPDATE_APPROVAL } from '../../mock/mockData';
import type { SchemaInfo } from '../../types/schema';

export const ApprovalGatePage: React.FC = () => {
  const approvalPayload = useQueryStore((s) => s.approvalPayload);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const userId = useAppStore((s) => s.userId);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const setCurrentView = useAppStore((s) => s.setCurrentView);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const [schema, setSchema] = useState<SchemaInfo | null>(null);
  const [activeTab, setActiveTab] = useState<'review' | 'er_schema'>('review');

  useEffect(() => {
    if (!approvalPayload) {
      setApprovalPayload(MOCK_UPDATE_APPROVAL);
    }
  }, [approvalPayload, setApprovalPayload]);

  useEffect(() => {
    getLiveSchema(userId, targetDialect).then(setSchema).catch(() => {});
  }, [userId, targetDialect]);

  const activePayload = approvalPayload || MOCK_UPDATE_APPROVAL;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden transition-colors duration-300 bg-[var(--bg-app)] text-[var(--text-body)]">
      {/* Sub-header Banner */}
      <div className={`h-12 px-4 border-b flex items-center justify-between shrink-0 transition-colors ${
        isDark
          ? 'bg-[var(--bg-header)]/80 backdrop-blur-xl border-[var(--border-main)]'
          : 'bg-[var(--bg-header)] backdrop-blur-xl border-[var(--border-main)]'
      }`}>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentView('query')}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-[var(--radius-pill)] transition-colors duration-200 cursor-pointer text-[var(--text-muted)] hover:text-[var(--text-main)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)] border border-[var(--border-subtle)]"
          >
            <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Back to Query Intake</span>
          </button>
          <span className="text-[var(--border-subtle)]">|</span>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-500" aria-hidden="true" />
            <span className="text-xs font-semibold text-[var(--text-main)]">
              Human Approval Gate: Safety & Impact Review
            </span>
          </div>
        </div>

        {/* View Switcher & Risk Badge */}
        <div className="flex items-center gap-3">
          {/* Segmented Ghost Slider for Approval Review */}
          <div className="relative inline-flex items-center p-0.5 rounded-full bg-[var(--bg-panel-alt)] border border-[var(--border-hairline)] shadow-inner">
            <button
              onClick={() => setActiveTab('review')}
              className={`relative z-10 flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200 cursor-pointer ${
                activeTab === 'review'
                  ? 'text-[var(--text-heading)] shadow-xs bg-[var(--bg-card)] border border-[var(--border-subtle)]'
                  : 'text-[var(--text-recessive)] hover:text-[var(--text-heading)]'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Statement & Diff</span>
            </button>
            <button
              onClick={() => setActiveTab('er_schema')}
              className={`relative z-10 flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200 cursor-pointer ${
                activeTab === 'er_schema'
                  ? 'text-[var(--text-heading)] shadow-xs bg-[var(--bg-card)] border border-[var(--border-subtle)]'
                  : 'text-[var(--text-recessive)] hover:text-[var(--text-heading)]'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Impacted Schema</span>
            </button>
          </div>

          <RiskBadge level={activePayload.risk_tier} />
        </div>
      </div>

      {/* Main Approval Workspace */}
      <div className="flex-1 min-h-0 p-3 sm:p-4 overflow-y-auto">
        {activeTab === 'review' ? (
          <div className="max-w-6xl mx-auto space-y-4">
            {/* Top Grid: Statement & Diff Side-by-Side on Desktop */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <SqlViewPanel sql={activePayload.generated_sql} dialect={activePayload.target_dialect} />
              <DiffPanel diffData={activePayload.diff_data} />
            </div>

            {/* Bottom Guardrail: Real-Time Dynamic Statement Guardrail */}
            <TelemetryPanel
              costEstimate={activePayload.cost_estimate}
              securityCheck={activePayload.security_check}
              sqlOverride={activePayload.generated_sql}
              impactedTablesOverride={activePayload.impacted_tables?.map((t: any) => typeof t === 'string' ? t : t.name)}
              riskTierOverride={activePayload.risk_tier}
            />
          </div>
        ) : (
          <div className="h-full rounded-[var(--radius-panel)] border border-[var(--border-hairline)] overflow-hidden bg-[var(--bg-card)] shadow-xs">
            <ERDiagramPanel
              schema={schema}
              impactedTables={activePayload.impacted_tables}
              generatedSql={activePayload.generated_sql}
              initialScope="query"
            />
          </div>
        )}
      </div>

      {/* Bottom Approval / Reject Action Bar */}
      <ApprovalActions queryId={activePayload.query_id} riskTier={activePayload.risk_tier} />
    </div>
  );
};
