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
    low: 'bg-[#2ECC71]/15 text-[#2ECC71] border-[#2ECC71]/30',
    medium: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    high: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
    critical: 'bg-red-500/20 text-red-400 border-red-500/40 animate-pulse font-bold',
  }[norm] || 'bg-slate-500/15 text-slate-300 border-slate-500/30';

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-none text-xs uppercase tracking-wider font-semibold border ${styles} ${className}`}
    >
      {norm} Risk
    </span>
  );
};
