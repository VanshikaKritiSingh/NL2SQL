// src/shared/ApprovalModal.tsx — Functional Human Approval Gate Popup
import React from 'react';
import { createPortal } from 'react-dom';
import { X, ShieldAlert, Database } from 'lucide-react';
import { RiskBadge } from './RiskBadge';
import { SqlViewPanel } from '../modules/approval_gate/SqlViewPanel';
import { DiffPanel } from '../modules/approval_gate/DiffPanel';
import { TelemetryPanel } from '../modules/approval_gate/TelemetryPanel';
import { ApprovalActions } from '../modules/approval_gate/ApprovalActions';
import { useAppStore } from '../store/useAppStore';
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
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  if (!isOpen || !payload) return null;

  return createPortal(
    <div className="modal-overlay bg-black/80 backdrop-blur-md animate-fade-in">
      <div
        className="w-full max-w-5xl h-[min(88vh,calc(100vh-48px))] max-h-[calc(100vh-48px)] rounded-none shadow-2xl flex flex-col overflow-hidden transition-all duration-300 my-auto"
        style={{
          backgroundColor: isDark ? '#14141D' : '#FFFFFF',
          border: isDark ? '1px solid rgba(255,255,255,0.18)' : '1px solid #DDE1E8',
        }}
      >
        {/* Header */}
        <div
          className={`h-14 px-5 border-b flex items-center justify-between shrink-0 ${
            isDark
              ? 'bg-[#181822] border-[var(--border-main)]'
              : 'bg-[#F4F6F9] border-[var(--border-subtle)]'
          }`}
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-none flex items-center justify-center bg-rose-500/10 text-rose-500 border border-rose-500/30">
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
                className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-none border font-medium cursor-pointer transition-colors ${
                  isDark
                    ? 'bg-[var(--bg-card)] border-[var(--border-main)] text-[var(--accent-primary)] hover:bg-[var(--bg-hover)]'
                    : 'bg-white border-[var(--border-subtle)] text-[#111111] hover:bg-[#EDF0F7]'
                }`}
                title="Inspect Impacted ER Schema Graph"
              >
                <Database className="w-3.5 h-3.5" />
                <span>View Schema ER</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-none transition-colors cursor-pointer text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)]"
              title="Close Review Gate"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Workspace */}
        <div
          className={`flex-1 min-h-0 p-4 overflow-y-auto space-y-3 ${
            isDark ? 'bg-[var(--bg-app)]' : 'bg-white'
          }`}
        >
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
    </div>,
    document.body
  );
};
