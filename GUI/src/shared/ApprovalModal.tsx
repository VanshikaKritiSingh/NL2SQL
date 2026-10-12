// src/shared/ApprovalModal.tsx — Functional Human Approval Gate Popup
import React from 'react';
import { X, ShieldAlert, Database, GitCompare, ExternalLink } from 'lucide-react';
import { RiskBadge } from './RiskBadge';
import { SqlViewPanel } from '../modules/approval_gate/SqlViewPanel';
import { DiffPanel } from '../modules/approval_gate/DiffPanel';
import { TelemetryPanel } from '../modules/approval_gate/TelemetryPanel';
import { ApprovalActions } from '../modules/approval_gate/ApprovalActions';
import type { ApprovalPayload } from '../types/approval';

interface ApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  payload: ApprovalPayload | null;
  onViewERDiagram?: () => void;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
  isOpen,
  onClose,
  payload,
  onViewERDiagram,
}) => {
  if (!isOpen || !payload) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-5xl h-[88vh] border rounded-2xl shadow-2xl flex flex-col overflow-hidden bg-[var(--bg-card)] border-[var(--border-main)]">
        {/* Header */}
        <div className="h-13 px-4 border-b flex items-center justify-between shrink-0 bg-[var(--bg-card-header)] border-[var(--border-subtle)]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-rose-500/10 text-rose-500 border border-rose-500/30">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold tracking-tight text-[var(--text-main)]">
                  Human Approval Gate: Pending Mutation
                </h2>
                <RiskBadge level={payload.risk_tier} />
              </div>
              <p className="text-[10px] text-[var(--text-muted)] font-mono">
                Query ID: {payload.query_id} · Target: {payload.target_dialect.toUpperCase()}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onViewERDiagram && (
              <button
                onClick={onViewERDiagram}
                className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border font-medium cursor-pointer transition-colors bg-[var(--bg-card)] border-[var(--border-subtle)] text-[var(--accent-primary)] hover:bg-[var(--bg-hover)]"
                title="Inspect Impacted ER Schema Graph"
              >
                <Database className="w-3.5 h-3.5" />
                <span>View Schema ER</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg transition-colors cursor-pointer text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)]"
              title="Close Review Gate"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Workspace */}
        <div className="flex-1 min-h-0 p-4 overflow-y-auto space-y-3 bg-[var(--bg-app)]">
          {/* Pending Statement Inspector */}
          <SqlViewPanel sql={payload.generated_sql} dialect={payload.target_dialect} />

          {/* DDL/DML Diff View */}
          <DiffPanel diffData={payload.diff_data} />

          {/* Pre-flight Telemetry (Cost Estimate + Concurrency Flags) */}
          <TelemetryPanel
            costEstimate={payload.cost_estimate}
            securityCheck={payload.security_check}
          />
        </div>

        {/* Action Bar (Approve & Execute vs Reject) */}
        <ApprovalActions queryId={payload.query_id} riskTier={payload.risk_tier} />
      </div>
    </div>
  );
};
