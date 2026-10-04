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
      className={`border rounded-xl overflow-hidden shadow-lg flex flex-col h-48 transition-colors ${
        isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}
    >
      <div
        className={`h-9 px-3 border-b flex items-center justify-between shrink-0 transition-colors ${
          isDark ? 'border-slate-800 bg-slate-900' : 'border-slate-200 bg-slate-50'
        }`}
      >
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-rose-500" />
          <span className={`text-xs font-semibold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
            Pending Statement for Review
          </span>
          <span
            className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
              isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-200 text-slate-600'
            }`}
          >
            {dialect}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded transition-colors cursor-pointer ${
            isDark
              ? 'text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700'
              : 'text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-300'
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
