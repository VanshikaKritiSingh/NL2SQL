// src/modules/m14/SqlViewPanel.tsx
import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Copy, Check, Code2 } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';

interface SqlViewPanelProps {
  sql: string;
  dialect: string;
}

export const SqlViewPanel: React.FC<SqlViewPanelProps> = ({ sql, dialect }) => {
  const [copied, setCopied] = useState(false);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const handleCopy = () => {
    if (!sql) return;
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="bento-card overflow-hidden shadow-lg flex flex-col h-48 transition-all duration-300 rounded-none"
      style={{
        backgroundColor: isDark ? 'var(--bg-card)' : 'var(--bg-card)',
        border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid var(--border-subtle)',
      }}
    >
      <div
        className={`h-9 px-3 border-b flex items-center justify-between shrink-0 transition-colors rounded-none ${
          isDark
            ? 'border-[var(--border-main)] bg-[var(--bg-card-header)]'
            : 'border-[var(--border-subtle)] bg-[var(--bg-card-header)]'
        }`}
      >
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-rose-500" />
          <span className="text-xs font-semibold text-[var(--text-main)]">
            Pending Statement for Review
          </span>
          <span
            className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-none ${
              isDark
                ? 'bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border-main)]'
                : 'bg-white text-[var(--text-muted)] border border-[var(--border-subtle)]'
            }`}
          >
            {dialect}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-none transition-colors cursor-pointer ${
            isDark
              ? 'text-[var(--text-muted)] hover:text-[var(--text-main)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)] border border-[var(--border-main)]'
              : 'text-[var(--text-muted)] hover:text-[var(--text-main)] bg-white hover:bg-[var(--bg-hover)] border border-[var(--border-subtle)]'
          }`}
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-500" />
              <span className="text-emerald-500">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      <div className="flex-1 relative">
        <Editor
          height="100%"
          language="sql"
          theme={isDark ? 'vs-dark' : 'light'}
          value={sql}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            padding: { top: 8, bottom: 8 },
            renderLineHighlight: 'none',
          }}
        />
      </div>
    </div>
  );
};
