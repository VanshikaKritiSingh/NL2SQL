// src/modules/m14/TelemetryPanel.tsx
import React from 'react';
import { Calculator, ShieldAlert, AlertTriangle, CheckCircle2, Lock, Tag } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import type { CostEstimate, SecurityCheck } from '../../types/approval';

interface TelemetryPanelProps {
  costEstimate: CostEstimate;
  securityCheck: SecurityCheck;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ costEstimate, securityCheck }) => {
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {/* EXPLAIN Cost Estimator Card */}
      <div
        className={`border rounded-xl p-3 shadow-lg flex flex-col justify-between transition-colors ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold">
              <Calculator className="w-4 h-4 text-indigo-500" />
              <span className={isDark ? 'text-slate-200' : 'text-slate-800'}>Execution Cost Estimate (EXPLAIN)</span>
            </div>
            <span
              className={`text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded ${
                costEstimate.scan_type === 'index_only'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : costEstimate.scan_type === 'index_scan'
                  ? 'bg-blue-950 text-blue-400 border border-blue-800'
                  : 'bg-rose-950 text-rose-400 border border-rose-800'
              }`}
            >
              {costEstimate.scan_type}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs font-mono my-2">
            <div
              className={`p-2 rounded-lg border ${
                isDark ? 'bg-slate-800/60 border-slate-700/50' : 'bg-slate-50 border-slate-200'
              }`}
            >
              <span className={`text-[10px] block ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Estimated Rows:
              </span>
              <span className={`text-sm font-bold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                {costEstimate.estimated_rows.toLocaleString()}
              </span>
            </div>
            <div
              className={`p-2 rounded-lg border ${
                isDark ? 'bg-slate-800/60 border-slate-700/50' : 'bg-slate-50 border-slate-200'
              }`}
            >
              <span className={`text-[10px] block ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Relative Cost Units:
              </span>
              <span className={`text-sm font-bold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                {costEstimate.estimated_cost.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {costEstimate.warnings.length > 0 && (
          <div className="mt-2 space-y-1">
            {costEstimate.warnings.map((w, i) => (
              <div
                key={i}
                className="flex items-center gap-1.5 text-[11px] text-amber-500 bg-amber-500/10 border border-amber-500/30 p-1.5 rounded"
              >
                <AlertTriangle className="w-3 h-3 text-amber-500 shrink-0" />
                <span>{w}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Security & Concurrency Guardrail Card */}
      <div
        className={`border rounded-xl p-3 shadow-lg flex flex-col justify-between transition-colors ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold">
              <ShieldAlert className="w-4 h-4 text-rose-500" />
              <span className={isDark ? 'text-slate-200' : 'text-slate-800'}>Concurrency & Deadlock Analyzer</span>
            </div>
            <span
              className={`text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded ${
                securityCheck.deadlock_risk === 'none' || securityCheck.deadlock_risk === 'low'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : 'bg-rose-950 text-rose-400 border border-rose-800 animate-pulse'
              }`}
            >
              Deadlock: {securityCheck.deadlock_risk}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs font-mono my-2">
            <div
              className={`p-2 rounded-lg border flex items-center justify-between ${
                isDark ? 'bg-slate-800/60 border-slate-700/50' : 'bg-slate-50 border-slate-200'
              }`}
            >
              <div>
                <span className={`text-[10px] block ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  Lock Granularity:
                </span>
                <span className={`text-xs font-bold uppercase ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                  {securityCheck.lock_level} LOCK
                </span>
              </div>
              <Lock className={`w-4 h-4 ${isDark ? 'text-slate-500' : 'text-slate-400'}`} />
            </div>
            <div
              className={`p-2 rounded-lg border flex items-center justify-between ${
                isDark ? 'bg-slate-800/60 border-slate-700/50' : 'bg-slate-50 border-slate-200'
              }`}
            >
              <div>
                <span className={`text-[10px] block ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  Role Privileges:
                </span>
                <span className="text-xs font-bold text-emerald-500">AUTHORIZED</span>
              </div>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
          </div>
        </div>

        {securityCheck.flags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {securityCheck.flags.map((flag, i) => (
              <span
                key={i}
                className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border ${
                  isDark ? 'bg-slate-800 text-slate-300 border-slate-700' : 'bg-slate-100 text-slate-700 border-slate-300'
                }`}
              >
                <Tag className="w-2.5 h-2.5 text-slate-400" />
                {flag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
