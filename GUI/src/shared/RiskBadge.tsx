// src/shared/RiskBadge.tsx
import React from 'react';
import { ShieldAlert, ShieldCheck, AlertTriangle } from 'lucide-react';
import type { RiskTier } from '../types/approval';

interface RiskBadgeProps {
  level: RiskTier | string;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, className = '' }) => {
  const norm = (level || 'low').toLowerCase();

  const config: Record<string, { bg: string; text: string; border: string; Icon: typeof ShieldCheck; label: string }> = {
    low: {
      bg: 'bg-[var(--success)]/15',
      text: 'text-[var(--success)]',
      border: 'border-[var(--success)]/30',
      Icon: ShieldCheck,
      label: 'Low Risk',
    },
    medium: {
      bg: 'bg-[var(--warning)]/15',
      text: 'text-[var(--warning)]',
      border: 'border-[var(--warning)]/30',
      Icon: AlertTriangle,
      label: 'Medium Risk',
    },
    high: {
      bg: 'bg-[var(--danger)]/15',
      text: 'text-[var(--danger)]',
      border: 'border-[var(--danger)]/30',
      Icon: ShieldAlert,
      label: 'High Risk',
    },
    critical: {
      bg: 'bg-[var(--danger)]/20',
      text: 'text-[var(--danger)]',
      border: 'border-[var(--danger)]/40',
      Icon: ShieldAlert,
      label: 'Critical Risk',
    },
  };

  const { bg, text, border, Icon, label } = config[norm] || config.low;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[var(--radius-pill)] text-xs uppercase tracking-wider font-semibold border ${bg} ${text} ${border} ${className}`}
    >
      <Icon className="w-3 h-3" aria-hidden="true" />
      {label}
    </span>
  );
};
