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
      className={`flex flex-col h-full border rounded-xl overflow-hidden shadow-lg transition-colors ${
        isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}
    >
      {/* Header */}
      <div
        className={`h-10 px-3 border-b flex items-center justify-between shrink-0 transition-colors ${
          isDark ? 'border-slate-800 bg-slate-900' : 'border-slate-200 bg-slate-50'
        }`}
      >
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-indigo-500" />
          <span className={`text-xs font-semibold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
            Generated SQL
          </span>
          <span
            className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
              isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-200 text-slate-600'
            }`}
          >
            {targetDialect} Dialect
          </span>
        </div>
        {sql && (
          <button
            onClick={handleCopy}
            className={`flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors cursor-pointer ${
              isDark
                ? 'text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700'
                : 'text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-300'
            }`}
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-emerald-500">Copied</span>
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
      <div className="flex-1 relative">
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
