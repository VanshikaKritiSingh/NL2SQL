// src/shared/DialectSelector.tsx
import React from 'react';
import { Database } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import type { TargetDialect } from '../types/query';

const DIALECTS: { id: TargetDialect; label: string }[] = [
  { id: 'mysql', label: 'MySQL' },
  { id: 'postgres', label: 'PostgreSQL' },
  { id: 'oracle', label: 'Oracle' },
  { id: 'sqlserver', label: 'SQL Server' },
  { id: 'access', label: 'MS Access' },
];

export const DialectSelector: React.FC = () => {
  const targetDialect = useAppStore((s) => s.targetDialect);
  const setTargetDialect = useAppStore((s) => s.setTargetDialect);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  return (
    <div
      className={`flex items-center gap-1.5 border rounded-lg px-2.5 py-1 text-xs transition-colors ${
        isDark ? 'bg-slate-800/90 border-slate-700/80' : 'bg-slate-100 border-slate-300'
      }`}
    >
      <Database className="w-3.5 h-3.5 text-indigo-500" />
      <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>DBMS:</span>
      <select
        value={targetDialect}
        onChange={(e) => setTargetDialect(e.target.value as TargetDialect)}
        className={`bg-transparent font-medium focus:outline-none cursor-pointer pr-1 ${
          isDark ? 'text-slate-200' : 'text-slate-800'
        }`}
      >
        {DIALECTS.map((d) => (
          <option
            key={d.id}
            value={d.id}
            className={isDark ? 'bg-slate-900 text-slate-200' : 'bg-white text-slate-800'}
          >
            {d.label}
          </option>
        ))}
      </select>
    </div>
  );
};
