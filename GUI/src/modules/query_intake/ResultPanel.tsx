// src/modules/query_intake/ResultPanel.tsx
import React from 'react';
import { Table, AlertTriangle, ShieldAlert, Zap, Server, Database, CheckCircle, ExternalLink } from 'lucide-react';
import { useQueryStore } from '../../store/useQueryStore';
import { useAppStore } from '../../store/useAppStore';
import { EmptyState } from '../../shared/EmptyState';

export const ResultPanel: React.FC = () => {
  const lastResponse = useQueryStore((s) => s.lastResponse);
  const setCurrentView = useAppStore((s) => s.setCurrentView);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  if (!lastResponse) {
    return (
      <div
        className={`flex flex-col h-full border rounded-xl overflow-hidden shadow-lg transition-colors ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <EmptyState
          icon={<Table className="w-6 h-6" />}
          title="Sandbox Execution Results"
          description="Read-only query outputs or execution statuses will display here."
        />
      </div>
    );
  }

  // Error State
  if (lastResponse.status === 'error') {
    return (
      <div
        className={`flex flex-col h-full border rounded-xl overflow-hidden shadow-lg p-6 justify-center items-center text-center transition-colors ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-500 mb-3">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-rose-500 mb-1">Execution Blocked</h3>
        <p className="text-xs text-rose-400 max-w-md font-mono bg-rose-500/10 p-3 rounded-lg border border-rose-500/20">
          {lastResponse.error_message || 'Pipeline validator or safety gate rejected this query.'}
        </p>
      </div>
    );
  }

  // Approval Required Gate Triggered
  if (lastResponse.status === 'approval_required') {
    const payload = lastResponse.approval_payload;
    const riskTier = payload?.risk_tier || 'high';

    return (
      <div
        className={`flex flex-col h-full border rounded-xl overflow-hidden shadow-lg p-6 justify-center items-center text-center transition-colors ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-500 mb-3">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-amber-500 mb-1">
          Mutating Statement · Approval Gate Triggered
        </h3>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[11px] px-2 py-0.5 rounded font-mono font-semibold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30">
            Risk: {riskTier}
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded font-mono text-slate-400 bg-slate-800 border border-slate-700">
            Preview Sandbox Mode (No Live DB Attached)
          </span>
        </div>
        <p className={`text-xs max-w-md mb-4 leading-relaxed ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
          The static validator and blast-radius engine identified a database modification. In connected environments, live mutation requires human sign-off. You can review schema impact, diffs, and estimated cost in the Approval Gate.
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentView('approval')}
            className="flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-amber-600/20 transition-all cursor-pointer"
          >
            <span>Review in Approval Gate</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  // Completed SELECT Table Result
  const resultData = lastResponse.result_data;

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
          <Server className="w-4 h-4 text-emerald-500" />
          <span className={`text-xs font-semibold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
            Sandbox Execution Output
          </span>
          {lastResponse.cache_hit && (
            <span className="flex items-center gap-1 text-[10px] font-semibold uppercase bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 px-1.5 py-0.5 rounded">
              <Zap className="w-3 h-3" /> Cache Hit
            </span>
          )}
          <span className="text-[10px] text-slate-400 font-mono bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700">
            Preview / Dry-Run
          </span>
        </div>
        <span className={`text-xs font-mono ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
          {resultData?.row_count || 0} rows returned
        </span>
      </div>

      {/* Table Data */}
      <div className="flex-1 overflow-auto">
        {resultData && resultData.rows.length > 0 ? (
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead
              className={`sticky top-0 border-b text-[11px] ${
                isDark ? 'bg-slate-800/90 border-slate-700 text-slate-300' : 'bg-slate-100 border-slate-200 text-slate-700'
              }`}
            >
              <tr>
                {resultData.columns.map((col) => (
                  <th key={col} className="px-3 py-2 font-semibold">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-slate-800 text-slate-300' : 'divide-slate-100 text-slate-700'}`}>
              {resultData.rows.map((row, idx) => (
                <tr
                  key={idx}
                  className={`transition-colors ${
                    isDark ? 'hover:bg-slate-800/50' : 'hover:bg-slate-50'
                  }`}
                >
                  {resultData.columns.map((col) => (
                    <td key={col} className="px-3 py-2 whitespace-nowrap">
                      {row[col] !== undefined && row[col] !== null ? String(row[col]) : 'NULL'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-slate-400">
            Query produced empty result set or completed with 0 rows.
          </div>
        )}
      </div>
    </div>
  );
};
