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
        className={`p-3.5 rounded-[var(--radius-panel)] border mb-3 ${
          isDark
            ? 'bg-[var(--bg-ghost)] border-[var(--border-hairline)] text-[var(--accent-primary)]'
            : 'bg-[var(--bg-panel)] border-[var(--border-hairline)] text-[var(--accent-primary)]'
        }`}
      >
        {icon}
      </div>
      <h3 className="text-sm font-semibold mb-1 text-[var(--text-heading)]">{title}</h3>
      <p className="text-xs max-w-sm mb-4 text-[var(--text-recessive)] leading-relaxed">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
