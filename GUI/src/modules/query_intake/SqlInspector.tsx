// src/modules/m1/SqlInspector.tsx
import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Copy, Check, Code2 } from 'lucide-react';
import { useQueryStore } from '../../store/useQueryStore';
import { useAppStore } from '../../store/useAppStore';
import { EmptyState } from '../../shared/EmptyState';

export const SqlInspector: React.FC = () => {
  const lastResponse = useQueryStore((s) => s.lastResponse);
  const targetDialect = useAppStore((s) => s.targetDialect);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';
  const [copied, setCopied] = useState(false);

  const sql = lastResponse?.generated_sql || '';

  const handleCopy = () => {
    if (!sql) return;
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="flex flex-col h-full overflow-hidden shadow-lg transition-all duration-300 bento-card rounded-none"
    >
      {/* Header */}
      <div
        className={`min-h-10 h-auto py-1.5 px-3 border-b flex flex-wrap gap-2 items-center justify-between shrink-0 transition-colors rounded-none ${
          isDark
            ? 'border-[var(--border-main)] bg-[var(--bg-card-header)]'
            : 'border-[var(--border-subtle)] bg-[var(--bg-card-header)]'
        }`}
      >
        <div className="flex flex-wrap items-center gap-2 shrink-0 min-w-0">
          <Code2 className={`w-4 h-4 shrink-0 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`} />
          <span className="text-xs font-semibold text-[var(--text-main)] whitespace-nowrap">
            Generated SQL
          </span>
          <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-none whitespace-nowrap shrink-0 ${
            isDark
              ? 'bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border-main)]'
              : 'bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border-subtle)]'
          }`}>
            {targetDialect} Dialect
          </span>
        </div>
        {sql && (
          <button
            onClick={handleCopy}
            className={`flex items-center gap-1 text-xs px-2 py-1 rounded-none transition-colors cursor-pointer shrink-0 whitespace-nowrap ${
              isDark
                ? 'text-[var(--text-muted)] hover:text-[var(--text-main)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)] border border-[var(--border-main)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text-main)] bg-white hover:bg-[var(--bg-hover)] border border-[var(--border-subtle)]'
            }`}
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-[var(--success)]" />
                <span className="text-[var(--success)] font-medium">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Editor Body */}
      <div className={`flex-1 relative ${isDark ? 'bg-[var(--bg-card)]' : 'bg-[var(--bg-card)]'}`}>
        {sql ? (
          <Editor
            height="100%"
            language="sql"
            theme={isDark ? 'vs-dark' : 'light'}
            value={sql}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 13,
              fontFamily: "'JetBrains Mono', monospace",
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              padding: { top: 12, bottom: 12 },
              renderLineHighlight: 'none',
            }}
          />
        ) : (
          <EmptyState
            icon={<Code2 className="w-6 h-6" />}
            title="Awaiting Model Generation"
            description="Generated SQL query AST and dialect-converted statement will appear here."
          />
        )}
      </div>
    </div>
  );
};
