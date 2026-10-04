// src/shared/RiskBadge.tsx
import React from 'react';
import type { RiskTier } from '../types/approval';

interface RiskBadgeProps {
  level: RiskTier | string;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, className = '' }) => {
  const norm = (level || 'low').toLowerCase();

  const styles = {
    low: 'bg-emerald-950/80 text-emerald-400 border-emerald-800',
    medium: 'bg-amber-950/80 text-amber-400 border-amber-800',
    high: 'bg-rose-950/80 text-rose-400 border-rose-800',
    critical: 'bg-red-950 text-red-400 border-red-700 animate-pulse font-bold',
  }[norm] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs uppercase tracking-wider font-semibold border ${styles} ${className}`}
    >
      {norm} Risk
    </span>
  );
};
