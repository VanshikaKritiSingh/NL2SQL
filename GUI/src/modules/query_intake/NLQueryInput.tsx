// src/modules/query_intake/NLQueryInput.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Send, X, Database, Eye, Brain, BrainCircuit } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { useQueryStore } from '../../store/useQueryStore';
import { usePipelineStore } from '../../store/usePipelineStore';
import { submitQuery } from '../../api/queryApi';
import { apiFetch } from '../../api/client';
import { LoadingSpinner } from '../../shared/LoadingSpinner';

interface ModelDetail {
  name: string;
  family: string;
  parameter_size: string;
  supports_thinking: boolean;
}

export const NLQueryInput: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [databases, setDatabases] = useState<string[]>([]);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [modelDetails, setModelDetails] = useState<ModelDetail[]>([]);
  const [isOllamaOnline, setIsOllamaOnline] = useState<boolean>(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const userId = useAppStore((s) => s.userId);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const databaseProfile = useAppStore((s) => s.databaseProfile);
  const setDatabaseProfile = useAppStore((s) => s.setDatabaseProfile);
  const isDbConnected = useAppStore((s) => s.isDbConnected);
  const setIsDbConnected = useAppStore((s) => s.setIsDbConnected);
  const connectedEngine = useAppStore((s) => s.connectedEngine);
  const setConnectedEngine = useAppStore((s) => s.setConnectedEngine);
  const availableDatabases = useAppStore((s) => s.availableDatabases);
  const setAvailableDatabases = useAppStore((s) => s.setAvailableDatabases);
  const selectedModel = useAppStore((s) => s.selectedModel);
  const setSelectedModel = useAppStore((s) => s.setSelectedModel);
  const thinkingEnabled = useAppStore((s) => s.thinkingEnabled);
  const setThinkingEnabled = useAppStore((s) => s.setThinkingEnabled);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const isSubmitting = useQueryStore((s) => s.isSubmitting);
  const setSubmitting = useQueryStore((s) => s.setSubmitting);
  const setLastResponse = useQueryStore((s) => s.setLastResponse);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const addToHistory = useQueryStore((s) => s.addToHistory);
  const startPipeline = usePipelineStore((s) => s.startPipeline);

  // Does the currently selected model support thinking?
  const currentModelDetail = modelDetails.find((d) => d.name === selectedModel);
  const modelSupportsThinking = currentModelDetail?.supports_thinking ?? false;

  useEffect(() => {
    if (textareaRef.current) textareaRef.current.focus();
  }, []);

  const fetchDatabases = async () => {
    try {
      const data = await apiFetch<any>('/connections/status/' + encodeURIComponent(userId));
      const connected = Boolean(data && (data.connected || data.attached));
      setIsDbConnected(connected);
      if (connected && data.connector_type) {
        setConnectedEngine(data.connector_type);
      } else {
        setConnectedEngine(null);
      }

      if (data && Array.isArray(data.databases) && data.databases.length > 0) {
        setDatabases(data.databases);
        setAvailableDatabases(data.databases);
        if (data.database) {
          setDatabaseProfile(data.database);
        } else if (!data.databases.includes(databaseProfile)) {
          setDatabaseProfile(data.databases[0]);
        }
      } else if (data && data.database) {
        const dbs = [data.database];
        setDatabases(dbs);
        setAvailableDatabases(dbs);
        setDatabaseProfile(data.database);
      } else {
        // Fallback default sample database options so the dropdown is never blank
        const fallback = ['test', 'ecommerce_db', 'master_enterprise'];
        setDatabases(fallback);
        setAvailableDatabases(fallback);
      }
    } catch {
      const fallback = ['test', 'ecommerce_db', 'master_enterprise'];
      setDatabases(fallback);
      setAvailableDatabases(fallback);
      setIsDbConnected(false);
      setConnectedEngine(null);
    }
  };

  const handleDatabaseChange = async (newDb: string) => {
    setDatabaseProfile(newDb);
    if (isDbConnected) {
      try {
        await apiFetch('/connections/switch-database', {
          method: 'POST',
          body: JSON.stringify({ user_id: userId, database: newDb }),
        });
      } catch {
        /* ignore offline/error */
      }
    }
  };

  useEffect(() => {
    if (availableDatabases && availableDatabases.length > 0) {
      setDatabases(availableDatabases);
    }
  }, [availableDatabases]);

  const fetchModels = async () => {
    try {
      const data = await apiFetch<any>('/connections/models');
      if (data && data.online && Array.isArray(data.models) && data.models.length > 0) {
        setAvailableModels(data.models);
        setIsOllamaOnline(true);
        if (Array.isArray(data.model_details)) {
          setModelDetails(data.model_details);
        }
        if (!selectedModel || selectedModel === 'auto' || !data.models.includes(selectedModel)) {
          setSelectedModel(data.default || data.models[0]);
        }
      } else {
        setIsOllamaOnline(false);
        setAvailableModels([]);
        setModelDetails([]);
      }
    } catch {
      setIsOllamaOnline(false);
      setAvailableModels([]);
      setModelDetails([]);
    }
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
        thinking_enabled: modelSupportsThinking ? thinkingEnabled : null,
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
    <div className={`bento-card p-4 shadow-lg relative flex flex-col gap-2.5 transition-all duration-300 rounded-none ${
      isDark
        ? 'bg-[var(--bg-card)] border-[var(--border-main)]'
        : 'bg-[var(--bg-card)] border-[var(--border-subtle)]'
    }`}>
      {/* Top Header Row with DB Context Selector */}
      <div className={`flex items-center justify-between text-xs pb-2 border-b border-dashed ${
        isDark ? 'border-[var(--border-main)]' : 'border-[var(--border-subtle)]'
      }`}>
        <div className="flex items-center gap-2 flex-wrap">
          <Database className={`w-3.5 h-3.5 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[#6712DC]'}`} />
          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-[var(--text-secondary)]">Connected DB Context:</span>
            <select
              value={databaseProfile || (databases[0] ?? 'test')}
              onChange={(e) => handleDatabaseChange(e.target.value)}
              className={`text-xs rounded-none px-2 py-0.5 font-medium border cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)] transition-colors ${
                isDark
                  ? 'bg-[var(--bg-input)] border-[var(--border-main)] text-[var(--text-main)] hover:border-white/25'
                  : 'bg-white border-[var(--border-subtle)] text-[var(--text-main)] hover:border-slate-400'
              }`}
              title={
                isDbConnected
                  ? `Active database context: '${databaseProfile}' (${connectedEngine?.toUpperCase() || 'DBMS'} socket active)`
                  : `Active schema context profile: '${databaseProfile}' (Offline/Sample schema — click 'Connect DB' to attach live engine)`
              }
            >
              {(databases.length > 0 ? databases : ['test', 'ecommerce_db', 'master_enterprise']).map((db) => (
                <option
                  key={db}
                  value={db}
                  className={isDark ? 'bg-[#181824] text-white' : 'bg-white text-slate-900'}
                >
                  {db} {isDbConnected && db === databaseProfile ? `(active ${connectedEngine?.toUpperCase() || 'DB'})` : ''}
                </option>
              ))}
            </select>

            {/* Live vs Offline Status Badge */}
            <span
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[9px] font-mono tracking-tight border rounded-none select-none ${
                isDbConnected
                  ? isDark
                    ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400'
                    : 'bg-emerald-50 border-emerald-300 text-emerald-700'
                  : isDark
                  ? 'bg-amber-950/30 border-amber-500/25 text-amber-400/90'
                  : 'bg-amber-50 border-amber-200 text-amber-700'
              }`}
              title={
                isDbConnected
                  ? `Live socket attached to ${connectedEngine?.toUpperCase() || 'DBMS'} database '${databaseProfile}'`
                  : 'No live database attached. Using offline schema context. Click "Connect DB" in top bar to connect.'
              }
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isDbConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              <span>{isDbConnected ? (connectedEngine ? connectedEngine.toUpperCase() : 'LIVE') : 'OFFLINE'}</span>
            </span>
          </div>
          <span className="text-[10px] text-[var(--text-muted)]">model:</span>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className={`text-xs rounded-none px-2 py-0.5 font-medium border cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)] ${
              isDark
                ? 'bg-[var(--bg-input)] border-[var(--border-main)] text-[var(--text-main)]'
                : 'bg-white border-[var(--border-subtle)] text-[var(--text-main)]'
            }`}
            title={isOllamaOnline ? `Ollama local models active (${availableModels.length} scanned)` : 'Ollama not detected; using deterministic offline synthesizer'}
          >
            {availableModels.length > 0 ? (
              availableModels.map((m) => {
                let label = m;
                if (m === 'A2.5C0.5') label = 'A2.5C0.5 (AdaLoRA 0.5B)';
                else if (m === 'Q2.5C0.5') label = 'Q2.5C0.5 (QLoRA 0.5B)';
                return (
                  <option key={m} value={m} className="bg-[var(--bg-card)] text-[var(--text-main)]">
                    {label}
                  </option>
                );
              })
            ) : (
              <option value="offline_synthesizer" className="bg-[var(--bg-card)] text-[var(--text-main)]">
                Offline Synthesizer
              </option>
            )}
          </select>
          {/* Think / NoThink Toggle Button */}
          {modelSupportsThinking && (
            <button
              type="button"
              onClick={() => setThinkingEnabled(thinkingEnabled ? false : true)}
              className={`flex items-center gap-1 px-2 py-0.5 rounded-none text-[10px] font-semibold border transition-all cursor-pointer select-none ${
                thinkingEnabled
                  ? isDark
                    ? 'bg-purple-500/15 border-purple-500/40 text-purple-400 hover:bg-purple-500/25'
                    : 'bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100'
                  : isDark
                  ? 'bg-orange-500/15 border-orange-500/40 text-orange-400 hover:bg-orange-500/25'
                  : 'bg-orange-50 border-orange-200 text-orange-700 hover:bg-orange-100'
              }`}
              title={
                thinkingEnabled
                  ? `Thinking ON — ${selectedModel} will reason before answering (slower, uses more tokens). Click to disable.`
                  : `Thinking OFF (NoThink) — ${selectedModel} will answer directly without reasoning (faster, less tokens). Click to enable.`
              }
            >
              {thinkingEnabled ? (
                <>
                  <BrainCircuit className="w-3 h-3" />
                  <span>Think</span>
                </>
              ) : (
                <>
                  <Brain className="w-3 h-3" />
                  <span>NoThink</span>
                </>
              )}
            </button>
          )}
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
          className={`w-full rounded-none p-3.5 text-sm focus:outline-none focus:ring-2 border font-sans select-text transition-all duration-200 resize-y min-h-[96px] max-h-[360px] leading-relaxed ${
            isDark
              ? 'bg-[var(--bg-input)] text-[var(--text-main)] placeholder-[var(--text-muted)] border-[var(--border-main)] focus:border-[var(--accent-primary)] focus:ring-[var(--accent-primary)]/20'
              : 'bg-white text-[var(--text-main)] placeholder-[var(--text-muted)] border-[var(--border-subtle)] focus:border-[#111111] focus:ring-[#111111]/10'
          }`}
        />
      </div>

      <div className="flex items-center justify-between flex-wrap gap-2 pt-0.5">
        <div className="flex items-center gap-2.5 text-[11px] text-[var(--text-muted)]">
          {charCount > 0 && <span className="font-mono">{charCount} chars · {lineCount} line{lineCount > 1 ? 's' : ''}</span>}
          <span className="hidden sm:inline font-mono text-[var(--text-muted)]">
            <kbd className={`px-1.5 py-0.5 rounded-none text-[10px] ${
              isDark
                ? 'bg-[var(--bg-card-header)] text-[var(--text-main)] border border-[var(--border-main)]'
                : 'bg-[var(--bg-card-header)] text-[var(--text-main)] border border-[var(--border-subtle)]'
            }`}>Enter</kbd> to execute, <kbd className={`px-1.5 py-0.5 rounded-none text-[10px] ${
              isDark
                ? 'bg-[var(--bg-card-header)] text-[var(--text-main)] border border-[var(--border-main)]'
                : 'bg-[var(--bg-card-header)] text-[var(--text-main)] border border-[var(--border-subtle)]'
            }`}>Shift+Enter</kbd> for newline
          </span>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          {inputText && (
            <button onClick={() => setInputText('')} className="p-1.5 rounded-none transition-colors cursor-pointer flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--danger)] hover:bg-[var(--bg-hover)]" title="Clear input prompt">
              <X className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}
          <button
            onClick={() => handleSubmit()}
            disabled={!inputText.trim() || isSubmitting}
            className={`flex items-center gap-1.5 px-5 py-2.5 rounded-none text-xs font-semibold shadow-lg transition-all cursor-pointer disabled:cursor-not-allowed disabled:opacity-40 ${
              isDark
                ? 'bg-[var(--btn-primary-bg)] hover:bg-[var(--btn-primary-hover)] text-[var(--btn-primary-text)] ambient-glow-btn'
                : 'bg-[var(--btn-primary-bg)] hover:bg-[var(--btn-primary-hover)] text-[var(--btn-primary-text)] shadow-black/10'
            }`}
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
    </div>
  );
};
