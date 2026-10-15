// src/modules/m14/ApprovalGatePage.tsx
import React, { useEffect, useState } from 'react';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';
import { ArrowLeft, ShieldAlert, Database } from 'lucide-react';
import { ERDiagramPanel } from './ERDiagramPanel';
import { SqlViewPanel } from './SqlViewPanel';
import { DiffPanel } from './DiffPanel';
import { TelemetryPanel } from './TelemetryPanel';
import { ApprovalActions } from './ApprovalActions';
import { useQueryStore } from '../../store/useQueryStore';
import { useAppStore } from '../../store/useAppStore';
import { getSchema } from '../../api/schemaApi';
import { RiskBadge } from '../../shared/RiskBadge';
import { MOCK_UPDATE_APPROVAL, MOCK_ALTER_APPROVAL } from '../../mock/mockData';
import type { SchemaInfo } from '../../types/schema';

export const ApprovalGatePage: React.FC = () => {
  const approvalPayload = useQueryStore((s) => s.approvalPayload);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const setCurrentView = useAppStore((s) => s.setCurrentView);
  const theme = useAppStore((s) => s.theme);
  const [schema, setSchema] = useState<SchemaInfo | null>(null);

  const isDark = theme === 'dark';

  useEffect(() => {
    if (!approvalPayload) {
      setApprovalPayload(MOCK_UPDATE_APPROVAL);
    }
  }, [approvalPayload, setApprovalPayload]);

  useEffect(() => {
    getSchema(targetDialect).then(setSchema).catch(() => {});
  }, [targetDialect]);

  const activePayload = approvalPayload || MOCK_UPDATE_APPROVAL;

  return (
    <div className={`flex-1 flex flex-col h-full overflow-hidden transition-colors duration-300 ${
      isDark ? 'bg-[var(--bg-app)]' : 'bg-white'
    }`}>
      {/* Sub-header Banner */}
      <div className={`h-12 px-4 border-b flex items-center justify-between shrink-0 transition-colors ${
        isDark
          ? 'bg-[var(--bg-header)]/80 backdrop-blur-xl border-[var(--border-main)]'
          : 'bg-white border-[var(--border-main)]'
      }`}>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentView('query')}
            className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-none transition-colors cursor-pointer ${
              isDark
                ? 'text-[var(--text-muted)] hover:text-[var(--text-main)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)] border border-[var(--border-main)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text-main)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)] border border-[var(--border-subtle)]'
            }`}
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Query Intake</span>
          </button>
          <span className="text-[var(--border-subtle)]">|</span>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-500" />
            <span className="text-xs font-semibold text-[var(--text-main)]">
              Human Approval Gate: Safety & Impact Review
            </span>
          </div>
        </div>

        {/* Demo Scenario Switcher & Risk Badge */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-xs">
            <span className="text-[11px] mr-1 hidden sm:inline text-[var(--text-muted)]">
              Review Scenario:
            </span>
            <button
              onClick={() => setApprovalPayload(MOCK_UPDATE_APPROVAL)}
              className={`px-2.5 py-1 rounded-none text-xs font-medium transition-all cursor-pointer ${
                activePayload.query_id === MOCK_UPDATE_APPROVAL.query_id
                  ? 'bg-rose-600 text-white shadow-md'
                  : isDark
                  ? 'bg-[var(--bg-card)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)] border border-[var(--border-main)]'
                  : 'bg-[var(--bg-card)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)] border border-[var(--border-subtle)]'
              }`}
            >
              Price Update (DML)
            </button>
            <button
              onClick={() => setApprovalPayload(MOCK_ALTER_APPROVAL)}
              className={`px-2.5 py-1 rounded-none text-xs font-medium transition-all cursor-pointer ${
                activePayload.query_id === MOCK_ALTER_APPROVAL.query_id
                  ? 'bg-rose-600 text-white shadow-md'
                  : isDark
                  ? 'bg-[var(--bg-card)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)] border border-[var(--border-main)]'
                  : 'bg-[var(--bg-card)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)] border border-[var(--border-subtle)]'
              }`}
            >
              Add Column (DDL)
            </button>
          </div>

          <RiskBadge level={activePayload.risk_tier} />
        </div>
      </div>

      {/* Main Resizable Split Workspace */}
      <div className="flex-1 min-h-0 p-3">
        <PanelGroup direction="horizontal">
          {/* Left Panel: React Flow ER Diagram */}
          <Panel defaultSize={48} minSize={30}>
            <div className="h-full flex flex-col">
              <div className="text-xs font-semibold mb-2 flex items-center gap-2 text-[var(--text-secondary)]">
                <Database className={`w-4 h-4 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[#6712DC]'}`} />
                <span>Impacted ER Schema Graph</span>
              </div>
              <div className="flex-1 min-h-0">
                <ERDiagramPanel schema={schema} impactedTables={activePayload.impacted_tables} />
              </div>
            </div>
          </Panel>

          <PanelResizeHandle className={`w-2 transition-colors cursor-col-resize flex items-center justify-center rounded-none ${
            isDark ? 'hover:bg-[var(--accent-primary)]/20' : 'hover:bg-[#6712DC]/10'
          }`}>
            <div className="w-0.5 h-8 rounded-none bg-[var(--border-main)]" />
          </PanelResizeHandle>

          {/* Right Panel: SQL Statement + Diff View + Pre-flight Telemetry */}
          <Panel defaultSize={52} minSize={35}>
            <div className="h-full flex flex-col gap-3 overflow-y-auto pr-1">
              <SqlViewPanel sql={activePayload.generated_sql} dialect={activePayload.target_dialect} />
              <DiffPanel diffData={activePayload.diff_data} />
              <TelemetryPanel
                costEstimate={activePayload.cost_estimate}
                securityCheck={activePayload.security_check}
              />
            </div>
          </Panel>
        </PanelGroup>
      </div>

      {/* Bottom Approval / Reject Action Bar */}
      <ApprovalActions queryId={activePayload.query_id} riskTier={activePayload.risk_tier} />
    </div>
  );
};
