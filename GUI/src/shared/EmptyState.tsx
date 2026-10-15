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
        className={`p-3.5 rounded-none border mb-3 shadow-xs ${
          isDark
            ? 'bg-[var(--bg-card-header)] border-[var(--border-main)] text-[var(--accent-primary)]'
            : 'bg-[#F4F6F9] border-[var(--border-subtle)] text-[#111111]'
        }`}
      >
        {icon}
      </div>
      <h3 className="text-sm font-bold mb-1 text-[var(--text-main)]">{title}</h3>
      <p className="text-xs max-w-sm mb-4 text-[var(--text-muted)] leading-relaxed">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
