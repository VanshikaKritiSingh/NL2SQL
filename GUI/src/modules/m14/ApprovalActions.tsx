// src/modules/m14/ApprovalActions.tsx
import React, { useState } from 'react';
import { CheckCircle2, XCircle, ArrowLeft } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { useQueryStore } from '../../store/useQueryStore';
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

  const isDark = theme === 'dark';

  const handleDecision = async (decision: 'approve' | 'reject') => {
    setIsSubmitting(true);
    try {
      await submitApproval(queryId, {
        query_id: queryId,
        decision,
        feedback: feedback.trim() || null,
        user_id: userId,
      });

      if (decision === 'approve') {
        setSettledResult({
          type: 'approved',
          message: 'Approved! Changes committed to Dolt CAS transaction checkpoint and dispatched to connected database.',
        });
      } else {
        setSettledResult({
          type: 'rejected',
          message: `Rejected! Feedback saved: "${feedback.trim() || 'Manual reject'}" and routed back for query adjustment.`,
        });
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
              ? 'bg-emerald-950/90 border-emerald-800 text-emerald-200'
              : 'bg-emerald-50 border-emerald-300 text-emerald-800'
            : isDark
            ? 'bg-rose-950/90 border-rose-800 text-rose-200'
            : 'bg-rose-50 border-rose-300 text-rose-800'
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
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer shadow"
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
      className={`p-4 shrink-0 shadow-2xl border-t transition-colors ${
        isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}
    >
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left: Operational Context Reminder */}
        <div className="flex items-center gap-3">
          <RiskBadge level={riskTier} />
          <span className={`text-xs font-mono hidden sm:inline ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
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
                className={`flex-1 rounded-lg px-3 py-2 text-xs border focus:outline-none focus:ring-1 focus:ring-rose-500 font-sans ${
                  isDark
                    ? 'bg-slate-800 text-slate-100 placeholder-slate-500 border-slate-700'
                    : 'bg-slate-100 text-slate-900 placeholder-slate-400 border-slate-300'
                }`}
              />
              <button
                onClick={() => handleDecision('reject')}
                disabled={isSubmitting}
                className="px-3 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow transition-all cursor-pointer whitespace-nowrap"
              >
                {isSubmitting ? <LoadingSpinner size="sm" /> : 'Confirm Reject'}
              </button>
              <button
                onClick={() => setShowRejectBox(false)}
                className={`px-2 py-2 text-xs cursor-pointer ${
                  isDark ? 'text-slate-400 hover:text-slate-200' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Cancel
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={() => setShowRejectBox(true)}
                disabled={isSubmitting}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer border ${
                  isDark
                    ? 'bg-slate-800 hover:bg-rose-950/80 hover:border-rose-700 text-slate-300 hover:text-rose-300 border-slate-700'
                    : 'bg-slate-100 hover:bg-rose-50 hover:border-rose-300 text-slate-700 hover:text-rose-700 border-slate-300'
                }`}
              >
                <XCircle className="w-4 h-4 text-rose-500" />
                <span>Reject with Feedback</span>
              </button>

              <button
                onClick={() => handleDecision('approve')}
                disabled={isSubmitting}
                className="flex items-center gap-1.5 px-6 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/30 transition-all cursor-pointer disabled:opacity-50"
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
