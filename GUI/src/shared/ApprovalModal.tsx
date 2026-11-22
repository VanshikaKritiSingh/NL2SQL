// src/shared/ApprovalModal.tsx — Functional Human Approval Gate Popup
import React, { useEffect, useCallback } from 'react';
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
  const databaseProfile = useAppStore((s) => s.databaseProfile);
  const isDark = theme === 'dark';

  // Escape key handler
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    if (isOpen && payload) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, payload, handleKeyDown]);

  if (!isOpen || !payload) return null;

  const modalTitleId = 'approval-modal-title';

  return createPortal(
    <div className="modal-overlay bg-black/80 backdrop-blur-md animate-fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={modalTitleId}
        className="w-full max-w-5xl h-[min(88vh,calc(100vh-48px))] max-h-[calc(100vh-48px)] rounded-[var(--radius-panel)] shadow-2xl flex flex-col overflow-hidden transition-colors duration-200 my-auto bg-[var(--bg-panel)] border border-[var(--border-hairline)] text-[var(--text-body)]"
      >
        {/* Header */}
        <div
          className="h-14 px-5 border-b flex items-center justify-between shrink-0 bg-[var(--bg-panel-alt)] border-[var(--border-subtle)]"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-[var(--radius-control)] flex items-center justify-center bg-[var(--danger-bg)] text-[var(--danger)] border border-[var(--danger)]/30">
              <ShieldAlert className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id={modalTitleId} className="text-sm font-bold tracking-tight text-[var(--text-heading)]">
                  Human Approval Gate: Pending Mutation
                </h2>
                <RiskBadge level={payload.risk_tier} />
              </div>
              <p className="text-[10px] text-[var(--text-recessive)] font-mono">
                Query ID: {payload.query_id} · Target: {databaseProfile && databaseProfile !== '__none__' ? `${databaseProfile} (${payload.target_dialect.toUpperCase()})` : payload.target_dialect.toUpperCase()}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onViewERDiagram && (
              <button
                onClick={onViewERDiagram}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-[var(--radius-control)] border font-medium cursor-pointer transition-colors duration-200 bg-[var(--bg-panel)] border-[var(--border-subtle)] text-[var(--accent-primary)] hover:bg-[var(--bg-ghost)]"
                title="Inspect Impacted ER Schema Graph"
              >
                <Database className="w-3.5 h-3.5" aria-hidden="true" />
                <span>View Schema ER</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-[var(--radius-control)] transition-colors duration-200 cursor-pointer text-[var(--text-recessive)] hover:text-[var(--text-heading)] hover:bg-[var(--bg-ghost)]"
              title="Close Review Gate"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Content Workspace */}
        <div
          className="flex-1 min-h-0 p-4 overflow-y-auto space-y-3 bg-[var(--bg-canvas)]"
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
