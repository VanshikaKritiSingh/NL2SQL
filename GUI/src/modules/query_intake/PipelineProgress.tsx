// src/modules/m1/PipelineProgress.tsx
import React from 'react';
import { Check, Loader2, X } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';
import { useAppStore } from '../../store/useAppStore';

export const PipelineProgress: React.FC = () => {
  const stages = usePipelineStore((s) => s.stages);
  const currentStageNumber = usePipelineStore((s) => s.currentStageNumber);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  // If all are pending, don't show the bar
  const hasActivity = stages.some((s) => s.status !== 'pending');
  if (!hasActivity) return null;

  return (
    <div
      className={`border rounded-xl p-3 shadow-md transition-colors ${
        isDark ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-semibold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
          Live Pipeline Execution (16 Stages)
        </span>
        <span className="text-[11px] font-mono text-indigo-500 font-medium">
          Stage {currentStageNumber || 1} of 16
        </span>
      </div>

      {/* Stage Circles Row */}
      <div className="grid grid-cols-16 gap-1 items-center">
        {stages.map((stage) => {
          const isCurrent = stage.stage_number === currentStageNumber && stage.status === 'started';
          const isDone = stage.status === 'completed';
          const isError = stage.status === 'error';

          return (
            <div
              key={stage.stage_number}
              className="flex flex-col items-center group relative cursor-pointer"
              title={`Stage ${stage.stage_number}: ${stage.stage_name} (${stage.status})`}
            >
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold transition-all ${
                  isDone
                    ? 'bg-emerald-600 text-white'
                    : isCurrent
                    ? 'bg-indigo-600 text-white ring-2 ring-indigo-400 animate-pulse'
                    : isError
                    ? 'bg-rose-600 text-white'
                    : isDark
                    ? 'bg-slate-800 text-slate-500 border border-slate-700'
                    : 'bg-slate-100 text-slate-400 border border-slate-300'
                }`}
              >
                {isDone ? (
                  <Check className="w-3 h-3" />
                ) : isCurrent ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : isError ? (
                  <X className="w-3 h-3" />
                ) : (
                  stage.stage_number
                )}
              </div>
              <span
                className={`text-[9px] mt-1 font-mono hidden md:block ${
                  isDark ? 'text-slate-500' : 'text-slate-400'
                }`}
              >
                {stage.stage_number}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
