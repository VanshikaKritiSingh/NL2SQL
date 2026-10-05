// src/modules/query_intake/NLQueryInput.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, X, Database, Layers, Eye } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { useQueryStore } from '../../store/useQueryStore';
import { usePipelineStore } from '../../store/usePipelineStore';
import { submitQuery } from '../../api/queryApi';
import { LoadingSpinner } from '../../shared/LoadingSpinner';

const DB_PROFILES = [
  { id: 'master_enterprise', label: 'Enterprise Master (users, orders, products)' },
  { id: 'analytics_warehouse', label: 'Analytics Warehouse (events, metrics, clicks)' },
  { id: 'customer_crm', label: 'Customer CRM (accounts, leads, opportunities)' },
  { id: 'inventory_mongo', label: 'Inventory Catalog (documents, json_specs)' },
];

const SUGGESTIONS = [
  { text: 'Show total order amount and customer names from last month', tag: 'Analytics' },
  { text: 'Increase all product prices in Electronics category by 10%', tag: 'DML Update' },
  { text: 'Add a discount_code column to orders table', tag: 'DDL Alter' },
  { text: 'Find shortest friendship path between Alice and Bob', tag: 'Graph Cypher' },
  { text: 'Aggregate daily product revenue grouped by category', tag: 'Mongo MQL' },
];

export const NLQueryInput: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const userId = useAppStore((s) => s.userId);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const databaseProfile = useAppStore((s) => s.databaseProfile);
  const setDatabaseProfile = useAppStore((s) => s.setDatabaseProfile);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const isSubmitting = useQueryStore((s) => s.isSubmitting);
  const setSubmitting = useQueryStore((s) => s.setSubmitting);
  const setLastResponse = useQueryStore((s) => s.setLastResponse);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const addToHistory = useQueryStore((s) => s.addToHistory);
  const startPipeline = usePipelineStore((s) => s.startPipeline);

  // Focus textarea on initial load
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  const handleSubmit = async (textToSubmit?: string) => {
    const q = (textToSubmit || inputText).trim();
    if (!q || isSubmitting) return;

    setSubmitting(true);
    try {
      const res = await submitQuery({
        user_id: userId,
        query_text: q,
        target_dialect: targetDialect,
        database_profile: databaseProfile,
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
        database_profile: databaseProfile,
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

  const lineCount = inputText ? inputText.split('\n').length : 0;
  const charCount = inputText.length;

  return (
    <div
      className={`border rounded-xl p-3.5 shadow-lg relative flex flex-col gap-2.5 transition-colors ${
        isDark ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200'
      }`}
    >
      {/* Top Header Row with DB Context Selector */}
      <div className="flex items-center justify-between text-xs pb-1 border-b border-dashed border-slate-700/40">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-indigo-400" />
          <span className={`font-semibold ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
            Connected DB Context:
          </span>
          <select
            value={databaseProfile}
            onChange={(e) => setDatabaseProfile(e.target.value)}
            className={`text-xs rounded px-2 py-0.5 font-medium border cursor-pointer focus:outline-none focus:ring-1 focus:ring-indigo-500 ${
              isDark
                ? 'bg-slate-800 border-slate-700 text-indigo-300'
                : 'bg-slate-100 border-slate-300 text-indigo-700'
            }`}
          >
            {DB_PROFILES.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          <span className="flex items-center gap-1">
            <Eye className="w-3 h-3 text-emerald-400" />
            <span>Dry-Run / Preview Mode</span>
          </span>
        </div>
      </div>

      {/* Resizable Textarea Area */}
      <div className="relative">
        <textarea
          ref={textareaRef}
          rows={3}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question in natural language... (e.g. 'Show me all active users and their total order amounts from last quarter')"
          className={`w-full rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 border font-sans select-text transition-colors resize-y min-h-[96px] max-h-[360px] leading-relaxed ${
            isDark
              ? 'bg-slate-950/90 text-slate-100 placeholder-slate-500 border-slate-700/70 focus:border-indigo-500'
              : 'bg-slate-50 text-slate-900 placeholder-slate-400 border-slate-300 focus:border-indigo-600'
          }`}
        />
      </div>

      {/* Bottom Action Bar */}
      <div className="flex items-center justify-between flex-wrap gap-2 pt-0.5">
        <div className="flex items-center gap-2.5 text-[11px] text-slate-400">
          {charCount > 0 && (
            <span className="font-mono">
              {charCount} chars · {lineCount} line{lineCount > 1 ? 's' : ''}
            </span>
          )}
          <span className={`hidden sm:inline font-mono ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
            <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]">Enter</kbd> to execute, <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]">Shift+Enter</kbd> for newline
          </span>
        </div>

        <div className="flex items-center gap-2 ml-auto">
          {inputText && (
            <button
              onClick={() => setInputText('')}
              className={`p-1.5 rounded-md transition-colors cursor-pointer flex items-center gap-1 text-xs ${
                isDark ? 'text-slate-400 hover:text-rose-400 hover:bg-slate-800' : 'text-slate-500 hover:text-rose-600 hover:bg-slate-100'
              }`}
              title="Clear input prompt"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}

          <button
            onClick={() => handleSubmit()}
            disabled={!inputText.trim() || isSubmitting}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Running Pipeline...</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>Generate & Execute</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Suggestion Chips */}
      <div className="flex items-center gap-1.5 text-xs flex-wrap pt-1 border-t border-slate-800/40">
        <span
          className={`text-[11px] flex items-center gap-1 font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}
        >
          <Sparkles className="w-3 h-3 text-amber-500" /> Demo queries:
        </span>
        {SUGGESTIONS.map((sug, i) => (
          <button
            key={i}
            onClick={() => {
              setInputText(sug.text);
              handleSubmit(sug.text);
            }}
            className={`px-2 py-0.5 rounded text-[11px] border transition-colors cursor-pointer flex items-center gap-1 ${
              isDark
                ? 'bg-slate-800/80 text-slate-300 hover:bg-slate-700 border-slate-700'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-300'
            }`}
          >
            <span>{sug.text}</span>
            <span className="text-[9px] px-1 rounded bg-indigo-500/20 text-indigo-400 font-mono">
              {sug.tag}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
