// src/modules/query_intake/NLQueryInput.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, X, Database, Eye } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { useQueryStore } from '../../store/useQueryStore';
import { usePipelineStore } from '../../store/usePipelineStore';
import { submitQuery } from '../../api/queryApi';
import { apiFetch } from '../../api/client';
import { LoadingSpinner } from '../../shared/LoadingSpinner';

export const NLQueryInput: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [databases, setDatabases] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const userId = useAppStore((s) => s.userId);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const databaseProfile = useAppStore((s) => s.databaseProfile);
  const setDatabaseProfile = useAppStore((s) => s.setDatabaseProfile);
  const selectedModel = useAppStore((s) => s.selectedModel);
  const setSelectedModel = useAppStore((s) => s.setSelectedModel);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const isSubmitting = useQueryStore((s) => s.isSubmitting);
  const setSubmitting = useQueryStore((s) => s.setSubmitting);
  const setLastResponse = useQueryStore((s) => s.setLastResponse);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const addToHistory = useQueryStore((s) => s.addToHistory);
  const startPipeline = usePipelineStore((s) => s.startPipeline);

  useEffect(() => {
    if (textareaRef.current) textareaRef.current.focus();
  }, []);

  const fetchDatabases = async () => {
    try {
      const data = await apiFetch<any>('/connections/status/' + encodeURIComponent(userId));
      if (data && Array.isArray(data.databases)) setDatabases(data.databases);
    } catch { /* ignore */ }
  };

  const fetchModels = async () => {
    try {
      const data = await apiFetch<any>('/connections/models');
      if (data && data.default) setSelectedModel(data.default);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchDatabases();
    fetchModels();
  }, [userId]);

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
        model_name: selectedModel,
      });

      startPipeline(res.query_id);
      setLastResponse(res);

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
    <div className="border rounded-xl p-3.5 shadow-lg relative flex flex-col gap-2.5 transition-colors bg-[var(--bg-card)] border-[var(--border-main)]">
      {/* Top Header Row with DB Context Selector */}
      <div className="flex items-center justify-between text-xs pb-1 border-b border-dashed border-[var(--border-subtle)]">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
          <span className="font-semibold text-[var(--text-secondary)]">Connected DB Context:</span>
          <select
            value={databaseProfile}
            onChange={(e) => setDatabaseProfile(e.target.value)}
            className="text-xs rounded px-2 py-0.5 font-medium border cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--accent-primary)] bg-[var(--bg-input)] border-[var(--border-subtle)] text-[var(--text-main)]"
          >
            {databases.map((db) => (
              <option key={db} value={db} className="bg-[var(--bg-card)] text-[var(--text-main)]">{db}</option>
            ))}
          </select>
          <span className="text-[10px] text-[var(--text-muted)]">model:</span>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="text-xs rounded px-2 py-0.5 font-medium border cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--accent-primary)] bg-[var(--bg-input)] border-[var(--border-subtle)] text-[var(--text-main)]"
          >
            <option value="qwen2.5-coder:7b" className="bg-[var(--bg-card)] text-[var(--text-main)]">qwen2.5-coder:7b (Top SOTA 8GB)</option>
            <option value="clef-flash:latest" className="bg-[var(--bg-card)] text-[var(--text-main)]">clef-flash:latest (Local Installed)</option>
            <option value="qwen2.5:0.5b" className="bg-[var(--bg-card)] text-[var(--text-main)]">qwen2.5:0.5b</option>
            <option value="gemma:latest" className="bg-[var(--bg-card)] text-[var(--text-main)]">gemma:latest</option>
          </select>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
          <span className="flex items-center gap-1">
            <Eye className="w-3 h-3 text-[var(--success)]" />
            <span>Dry-Run / Preview Mode</span>
          </span>
        </div>
      </div>

      <div className="relative">
        <textarea
          ref={textareaRef}
          rows={3}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question in natural language... (e.g. 'Show me all active users and their total order amounts from last quarter')"
          className="w-full rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--accent-primary)] border font-sans select-text transition-colors resize-y min-h-[96px] max-h-[360px] leading-relaxed bg-[var(--bg-input)] text-[var(--text-main)] placeholder-[var(--text-muted)] border-[var(--border-subtle)] focus:border-[var(--accent-primary)]"
        />
      </div>

      <div className="flex items-center justify-between flex-wrap gap-2 pt-0.5">
        <div className="flex items-center gap-2.5 text-[11px] text-[var(--text-muted)]">
          {charCount > 0 && <span className="font-mono">{charCount} chars · {lineCount} line{lineCount > 1 ? 's' : ''}</span>}
          <span className="hidden sm:inline font-mono text-[var(--text-muted)]">
            <kbd className="px-1 py-0.5 rounded bg-[var(--bg-card-header)] text-[var(--text-main)] border border-[var(--border-subtle)] text-[10px]">Enter</kbd> to execute, <kbd className="px-1 py-0.5 rounded bg-[var(--bg-card-header)] text-[var(--text-main)] border border-[var(--border-subtle)] text-[10px]">Shift+Enter</kbd> for newline
          </span>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          {inputText && (
            <button onClick={() => setInputText('')} className="p-1.5 rounded-md transition-colors cursor-pointer flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--danger)] hover:bg-[var(--bg-hover)]" title="Clear input prompt">
              <X className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}
          <button onClick={() => handleSubmit()} disabled={!inputText.trim() || isSubmitting} className="flex items-center gap-1.5 px-4 py-2 bg-[var(--accent-primary)] hover:opacity-90 disabled:opacity-40 text-white rounded-lg text-xs font-semibold shadow-md transition-all cursor-pointer disabled:cursor-not-allowed">
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
    </div>
  );
};