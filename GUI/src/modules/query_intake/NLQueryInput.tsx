// src/modules/query_intake/NLQueryInput.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Send, X, Database, Eye, Brain, BrainCircuit } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { useQueryStore } from '../../store/useQueryStore';
import { usePipelineStore } from '../../store/usePipelineStore';
import { useSchemaStore } from '../../store/useSchemaStore';
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
  const bumpSchemaVersion = useSchemaStore((s) => s.bumpSchemaVersion);
  const schemaVersion = useSchemaStore((s) => s.schemaVersion);

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

      if (connected && data && Array.isArray(data.databases) && data.databases.length > 0) {
        setDatabases(data.databases);
        setAvailableDatabases(data.databases);
        if (databaseProfile !== '__none__') {
          if (data.database) {
            setDatabaseProfile(data.database);
          } else if (!data.databases.includes(databaseProfile)) {
            setDatabaseProfile(data.databases[0]);
          }
        }
      } else if (connected && data && data.database) {
        const dbs = [data.database];
        setDatabases(dbs);
        setAvailableDatabases(dbs);
        if (databaseProfile !== '__none__') {
          setDatabaseProfile(data.database);
        }
      } else {
        // Disconnected: clear all database contexts and revert to clean state
        setDatabases([]);
        setAvailableDatabases([]);
        setDatabaseProfile('__none__');
      }
    } catch {
      setDatabases([]);
      setAvailableDatabases([]);
      setIsDbConnected(false);
      setConnectedEngine(null);
      setDatabaseProfile('__none__');
    }
  };

  const handleDatabaseChange = async (newDb: string) => {
    setDatabaseProfile(newDb);
    try {
      await apiFetch('/connections/switch-database', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, database: newDb }),
      });
    } catch {
      /* ignore offline/error */
    }
    bumpSchemaVersion();
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
  }, [userId, schemaVersion]);

  const handleSubmit = async (textToSubmit?: string) => {
    const q = (textToSubmit || inputText).trim();
    if (!q || isSubmitting) return;

    setSubmitting(true);
    try {
      const res = await submitQuery({
        user_id: userId,
        query_text: q,
        target_dialect: targetDialect,
        database_profile: databaseProfile === '__none__' ? '' : databaseProfile,
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
        database_profile: res.database_profile || (databaseProfile === '__none__' ? '(None / New Database)' : databaseProfile),
        selected_dialect: res.selected_dialect,
        dialect_reason: res.dialect_reason,
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
    <form
      onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
      className="shrink-0 border-t border-[var(--border-hairline)] bg-[var(--bg-panel)] px-3.5 py-2.5"
    >
      {/* Context strip */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <Database className="w-3.5 h-3.5 text-[var(--text-recessive)] shrink-0" aria-hidden="true" />

        <select
          value={databaseProfile || '__none__'}
          onChange={(e) => handleDatabaseChange(e.target.value)}
          className="h-[26px] px-2 rounded-[6px] border border-[var(--border-hairline)] bg-[var(--bg-canvas)] text-[var(--text-main)] font-mono text-[11.5px] cursor-pointer focus:outline-2 focus:outline-[var(--accent-primary)] focus:outline-offset-[-1px] max-w-[280px]"
          title={
            databaseProfile === '__none__'
              ? 'No database context — scratchpad mode for creating new databases or tables.'
              : isDbConnected
              ? `Active database context: '${databaseProfile}' (${connectedEngine?.toUpperCase() || 'DBMS'} socket active)`
              : `Schema context: '${databaseProfile}' (offline / sample schema — connect a live engine to introspect)`
          }
        >
          <option value="__none__">(no context) new db / scratch</option>
          {databases.map((db) => (
            <option key={db} value={db}>
              {db}{isDbConnected && db === databaseProfile ? ` (active ${connectedEngine?.toUpperCase() || 'DB'})` : ''}
            </option>
          ))}
        </select>

        <span
          className={`inline-flex items-center gap-1 px-1.5 py-[1px] rounded-[4px] font-mono text-[10px] border ${
            databaseProfile === '__none__'
              ? 'border-[var(--warning)]/40 bg-[var(--warning-soft)] text-[var(--warning)]'
              : isDbConnected
              ? 'border-[var(--success)]/40 bg-[var(--success-soft)] text-[var(--success)]'
              : 'border-[var(--warning)]/30 bg-[var(--warning-soft)] text-[var(--warning)]'
          }`}
          title={
            databaseProfile === '__none__'
              ? 'No schema context attached — ideal for architecture/DDL authoring.'
              : isDbConnected
              ? `Live socket attached to ${connectedEngine?.toUpperCase() || 'DBMS'}: '${databaseProfile}'`
              : 'No live database attached — using offline schema context.'
          }
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              databaseProfile !== '__none__' && isDbConnected ? 'bg-[var(--success)]' : 'bg-[var(--warning)]'
            }`}
          />
          {databaseProfile === '__none__'
            ? 'SCRATCH'
            : isDbConnected
            ? (connectedEngine ? connectedEngine.toUpperCase() : 'LIVE')
            : 'OFFLINE'}
        </span>

        <div className="flex-1" />

        <span className="hidden md:inline-flex items-center gap-1 font-mono text-[10.5px] text-[var(--text-recessive)]">
          <Eye className="w-3 h-3 text-[var(--success)]" aria-hidden="true" />
          dry-run preview
        </span>
      </div>

      {/* Composer box */}
      <div className="flex items-end gap-2 bg-[var(--bg-canvas)] border border-[var(--border-hairline)] rounded-[6px] px-3 py-1.5 focus-within:border-[var(--accent-primary)] focus-within:outline focus-within:outline-1 focus-within:outline-[var(--accent-primary)] transition-colors">
        <textarea
          ref={textareaRef}
          rows={1}
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
            const el = e.target as HTMLTextAreaElement;
            el.style.height = 'auto';
            el.style.height = Math.min(el.scrollHeight, 180) + 'px';
          }}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question in natural language...  (Shift+Enter for newline)"
          className="flex-1 bg-transparent border-0 outline-none resize-none min-h-[26px] max-h-[180px] py-1 text-[13.5px] leading-[1.5] text-[var(--text-main)] placeholder-[var(--text-recessive)] font-sans select-text"
        />

        <div className="flex items-center gap-2 shrink-0 pb-[1px]">
          <span className="hidden lg:inline font-mono text-[10.5px] text-[var(--text-recessive)] whitespace-nowrap">
            Enter ↵
          </span>
          {inputText && (
            <button
              type="button"
              onClick={() => setInputText('')}
              className="p-1 rounded-[4px] text-[var(--text-recessive)] hover:text-[var(--danger)] hover:bg-[var(--bg-hover)] cursor-pointer transition-colors"
              title="Clear prompt"
            >
              <X className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          )}
          <button
            type="submit"
            disabled={!inputText.trim() || isSubmitting}
            className="h-8 px-3.5 rounded-[6px] border border-[var(--accent-primary)] bg-[var(--accent-primary)] text-white text-[12.5px] font-semibold cursor-pointer disabled:cursor-not-allowed disabled:opacity-40 inline-flex items-center gap-1.5 hover:brightness-110 transition-all whitespace-nowrap"
          >
            {isSubmitting ? (
              <>
                <LoadingSpinner size="sm" aria-hidden="true" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Generate &amp; Execute</span>
              </>
            )}
          </button>
        </div>
      </div>

      {charCount > 0 && (
        <div className="mt-1 font-mono text-[10.5px] text-[var(--text-recessive)]">
          {charCount} chars · {lineCount} line{lineCount !== 1 ? 's' : ''}
        </div>
      )}
    </form>
  );
};
