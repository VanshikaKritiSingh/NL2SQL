// src/modules/m14/ApprovalActions.tsx
import React, { useState } from 'react';
import { CheckCircle2, XCircle, ArrowLeft } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { useQueryStore } from '../../store/useQueryStore';
import { useSchemaStore } from '../../store/useSchemaStore';
import { submitApproval } from '../../api/approvalApi';
import { LoadingSpinner } from '../../shared/LoadingSpinner';
import { RiskBadge } from '../../shared/RiskBadge';
import type { RiskTier } from '../../types/approval';

interface ApprovalActionsProps {
  queryId: string;
  riskTier: RiskTier;
}

export const ApprovalActions: React.FC<ApprovalActionsProps> = ({ queryId, riskTier }) => {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRejectBox, setShowRejectBox] = useState(false);
  const [settledResult, setSettledResult] = useState<{ type: 'approved' | 'rejected'; message: string } | null>(null);

  const userId = useAppStore((s) => s.userId);
  const setCurrentView = useAppStore((s) => s.setCurrentView);
  const theme = useAppStore((s) => s.theme);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const bumpSchemaVersion = useSchemaStore((s) => s.bumpSchemaVersion);

  const isDark = theme === 'dark';

  const handleDecision = async (decision: 'approve' | 'reject') => {
    setIsSubmitting(true);
    try {
      const res = await submitApproval(queryId, {
        query_id: queryId,
        decision,
        feedback: feedback.trim() || null,
        user_id: userId,
      });

      if (decision === 'approve') {
        const msg = res.message || 'Approved! Mutation committed to transaction checkpoint and dispatched to connected database.';
        const hasDbmsError = msg.includes('DBMS execution error') || msg.includes('DBMS execution failed') || res.status === 'error';

        if (hasDbmsError) {
          setSettledResult({
            type: 'rejected',
            message: msg,
          });

          const currentResp = useQueryStore.getState().lastResponse;
          if (currentResp) {
            useQueryStore.getState().setLastResponse({
              ...currentResp,
              status: 'error',
              error_message: msg,
              result_data: {
                columns: ['status', 'action', 'details'],
                rows: [
                  {
                    status: 'DBMS_ERROR',
                    action: 'EXECUTION_FAILED',
                    details: msg,
                  },
                ],
                row_count: 1,
              },
            });
          }
        } else {
          setSettledResult({
            type: 'approved',
            message: msg,
          });

          const currentResp = useQueryStore.getState().lastResponse;
          if (currentResp) {
            useQueryStore.getState().setLastResponse({
              ...currentResp,
              status: 'completed',
              result_data: {
                columns: ['status', 'action', 'details'],
                rows: [
                  {
                    status: 'COMMITTED',
                    action: 'DBMS_EXECUTION_SUCCESS',
                    details: msg,
                  },
                ],
                row_count: 1,
              },
            });
          }
          // Refresh ER diagram after approval commits mutation
          bumpSchemaVersion();
        }
      } else {
        const msg = `Rejected! Feedback saved: "${feedback.trim() || 'Manual reject'}" and routed back for query adjustment.`;
        setSettledResult({
          type: 'rejected',
          message: msg,
        });

        const currentResp = useQueryStore.getState().lastResponse;
        if (currentResp) {
          useQueryStore.getState().setLastResponse({
            ...currentResp,
            status: 'error',
            error_message: `Statement rejected by human reviewer. Feedback: ${feedback.trim() || 'No feedback'}`,
          });
        }
      }
    } catch {
      alert('Failed to submit approval decision.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFinish = () => {
    setApprovalPayload(null);
    setCurrentView('query');
  };

  if (settledResult) {
    return (
      <div
        className={`p-4 border-t transition-colors ${
          settledResult.type === 'approved'
            ? isDark
              ? 'bg-emerald-950/80 border-emerald-800 text-emerald-200'
              : 'bg-emerald-50 border-emerald-200 text-emerald-800'
            : isDark
            ? 'bg-rose-950/80 border-rose-800 text-rose-200'
            : 'bg-rose-50 border-rose-200 text-rose-800'
        }`}
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-xs font-semibold">
            {settledResult.type === 'approved' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : (
              <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
            )}
            <span>{settledResult.message}</span>
          </div>
          <button
            onClick={handleFinish}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-none text-xs font-semibold transition-all cursor-pointer shadow ${
              isDark
                ? 'bg-[var(--accent-primary)] hover:bg-[var(--accent-hover)] text-white ambient-glow-btn'
                : 'bg-[#111111] hover:bg-black text-white'
            }`}
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Query Intake</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`p-4 shrink-0 shadow-2xl border-t transition-colors duration-300 ${
        isDark
          ? 'bg-[var(--bg-header)]/90 backdrop-blur-xl border-[var(--border-main)]'
          : 'bg-white border-[var(--border-main)]'
      }`}
    >
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left: Operational Context Reminder */}
        <div className="flex items-center gap-3">
          <RiskBadge level={riskTier} />
          <span className="text-xs font-mono hidden sm:inline text-[var(--text-muted)]">
            Approval commits transaction to Dolt CAS checkpoint and dispatches to primary database.
          </span>
        </div>

        {/* Center/Right: Action Buttons */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          {showRejectBox ? (
            <div className="flex items-center gap-2 w-full md:w-96">
              <input
                type="text"
                placeholder="Feedback for model retry (e.g. 'Add active status filter')..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                className={`flex-1 rounded-none px-3 py-2 text-xs border focus:outline-none focus:ring-2 font-sans ${
                  isDark
                    ? 'bg-[var(--bg-input)] text-[var(--text-main)] placeholder-[var(--text-muted)] border-[var(--border-main)] focus:border-rose-500 focus:ring-rose-500/20'
                    : 'bg-[#F4F6F9] text-[var(--text-main)] placeholder-[var(--text-muted)] border-[var(--border-subtle)] focus:border-rose-500 focus:ring-rose-500/10'
                }`}
              />
              <button
                onClick={() => handleDecision('reject')}
                disabled={isSubmitting}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-none text-xs font-semibold shadow transition-all cursor-pointer whitespace-nowrap"
              >
                {isSubmitting ? <LoadingSpinner size="sm" /> : 'Confirm Reject'}
              </button>
              <button
                onClick={() => setShowRejectBox(false)}
                className="px-2 py-2 text-xs text-[var(--text-muted)] hover:text-[var(--text-main)] cursor-pointer"
              >
                Cancel
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={() => setShowRejectBox(true)}
                disabled={isSubmitting}
                className={`flex items-center gap-1.5 px-4 py-2.5 rounded-none text-xs font-semibold transition-all cursor-pointer border ${
                  isDark
                    ? 'bg-[var(--bg-card)] hover:bg-rose-500/10 hover:border-rose-500/40 text-[var(--text-muted)] hover:text-rose-400 border-[var(--border-main)]'
                    : 'bg-[#F4F6F9] hover:bg-rose-50 hover:border-rose-200 text-[var(--text-main)] hover:text-rose-600 border-[var(--border-subtle)]'
                }`}
              >
                <XCircle className="w-4 h-4 text-rose-500" />
                <span>Reject with Feedback</span>
              </button>

              {/* Primary CTA button */}
              <button
                onClick={() => handleDecision('approve')}
                disabled={isSubmitting}
                className={`flex items-center gap-2 px-6 py-2.5 rounded-none text-xs font-bold transition-all cursor-pointer disabled:opacity-50 ${
                  isDark
                    ? 'bg-gradient-to-r from-[#8E94F2] to-[#B48EBA] hover:opacity-95 text-white ambient-glow-btn'
                    : 'bg-[#111111] hover:bg-black text-white shadow-lg shadow-black/10'
                }`}
              >
                {isSubmitting ? (
                  <>
                    <LoadingSpinner size="sm" />
                    <span>Committing & Dispatching...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Approve & Execute</span>
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
