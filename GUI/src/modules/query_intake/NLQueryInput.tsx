// src/modules/m1/NLQueryInput.tsx
import React, { useState } from 'react';
import { Send, Sparkles, X } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { useQueryStore } from '../../store/useQueryStore';
import { usePipelineStore } from '../../store/usePipelineStore';
import { submitQuery } from '../../api/queryApi';
import { LoadingSpinner } from '../../shared/LoadingSpinner';

const SUGGESTIONS = [
  'Show me all orders from last month',
  'Increase all product prices by 10%',
  'Add a discount_code column to orders table',
];

export const NLQueryInput: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const userId = useAppStore((s) => s.userId);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const isSubmitting = useQueryStore((s) => s.isSubmitting);
  const setSubmitting = useQueryStore((s) => s.setSubmitting);
  const setLastResponse = useQueryStore((s) => s.setLastResponse);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const addToHistory = useQueryStore((s) => s.addToHistory);
  const startPipeline = usePipelineStore((s) => s.startPipeline);

  const handleSubmit = async (textToSubmit?: string) => {
    const q = (textToSubmit || inputText).trim();
    if (!q || isSubmitting) return;

    setSubmitting(true);
    try {
      const res = await submitQuery({
        user_id: userId,
        query_text: q,
        target_dialect: targetDialect,
      });

      startPipeline(res.query_id);
      setLastResponse(res);

      // Add to query history
      addToHistory({
        query_id: res.query_id,
        query_text: q,
        generated_sql: res.generated_sql,
        target_dialect: targetDialect,
        status: res.status,
        timestamp: new Date().toLocaleTimeString(),
        is_mutating: res.status === 'approval_required',
      });

      // If approval is required, set the payload
      if (res.status === 'approval_required' && res.approval_payload) {
        setApprovalPayload(res.approval_payload);
      }
    } catch (err: any) {
      setLastResponse({
        query_id: 'err',
        status: 'error',
        generated_sql: null,
        result_data: null,
        approval_payload: null,
        error_message: err.message || 'Failed to submit query',
        cache_hit: false,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey || !e.shiftKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      className={`border rounded-xl p-3 shadow-lg relative flex flex-col gap-2.5 transition-colors ${
        isDark ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200'
      }`}
    >
      {/* Textarea Area */}
      <div className="relative">
        <textarea
          rows={3}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question in natural language... (e.g. 'Show me all orders from last month')"
          className={`w-full rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 border resize-none font-sans select-text ${
            isDark
              ? 'bg-slate-950/80 text-slate-100 placeholder-slate-500 border-slate-700/60'
              : 'bg-slate-50 text-slate-900 placeholder-slate-400 border-slate-300'
          }`}
        />
        <div className="absolute right-2.5 bottom-2.5 flex items-center gap-2">
          {inputText && (
            <button
              onClick={() => setInputText('')}
              className={`p-1 rounded transition-colors cursor-pointer ${
                isDark ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-600'
              }`}
              title="Clear input"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          <span className={`text-[10px] hidden sm:inline font-mono ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
            Press Enter ↵
          </span>
          <button
            onClick={() => handleSubmit()}
            disabled={!inputText.trim() || isSubmitting}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-md text-xs font-semibold shadow transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Running Pipeline...</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>Execute Query</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Suggestion Chips */}
      <div className="flex items-center gap-2 text-xs flex-wrap">
        <span
          className={`text-[11px] flex items-center gap-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}
        >
          <Sparkles className="w-3 h-3 text-amber-500" /> Demo queries:
        </span>
        {SUGGESTIONS.map((sug, i) => (
          <button
            key={i}
            onClick={() => {
              setInputText(sug);
              handleSubmit(sug);
            }}
            className={`px-2 py-0.5 rounded text-[11px] border transition-colors cursor-pointer ${
              isDark
                ? 'bg-slate-800 text-slate-300 hover:bg-slate-700 border-slate-700'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-300'
            }`}
          >
            {sug}
          </button>
        ))}
      </div>
    </div>
  );
};
