// src/shared/EmptyState.tsx
import React from 'react';
import { useAppStore } from '../store/useAppStore';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, action }) => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  return (
    <div className="flex flex-col items-center justify-center p-8 text-center h-full">
      <div
        className={`p-3 rounded-xl border mb-3 ${
          isDark ? 'bg-slate-800/60 border-slate-700/60 text-slate-400' : 'bg-slate-100 border-slate-200 text-slate-500'
        }`}
      >
        {icon}
      </div>
      <h3 className={`text-sm font-semibold mb-1 ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>{title}</h3>
      <p className={`text-xs max-w-sm mb-4 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
