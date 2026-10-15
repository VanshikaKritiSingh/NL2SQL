// src/shared/StatusBar.tsx
import React from 'react';
import { Activity, CheckCircle2 } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';
import { useAppStore } from '../store/useAppStore';

export const StatusBar: React.FC = () => {
  const currentStageNumber = usePipelineStore((s) => s.currentStageNumber);
  const stages = usePipelineStore((s) => s.stages);
  const pipelineComplete = usePipelineStore((s) => s.pipelineComplete);
  const theme = useAppStore((s) => s.theme);
  const isDark = theme === 'dark';

  const activeStage = stages.find((s) => s.stage_number === currentStageNumber);

  return (
    <footer
      className={`min-h-7 h-7 border-t px-3 sm:px-5 flex items-center justify-between text-[11px] font-mono shrink-0 transition-colors duration-300 z-20 overflow-x-auto overflow-y-hidden gap-3 ${
        isDark
          ? 'border-[var(--border-main)] bg-[var(--bg-header)]/80 backdrop-blur-xl text-[var(--text-muted)]'
          : 'border-[var(--border-main)] bg-white text-[var(--text-muted)]'
      }`}
    >
      <div className="flex items-center gap-2 shrink-0 whitespace-nowrap">
        <Activity className={`w-3.5 h-3.5 shrink-0 ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`} />
        <span className="font-semibold text-[var(--text-secondary)] whitespace-nowrap">Pipeline:</span>
        {pipelineComplete ? (
          <span className="flex items-center gap-1 text-[var(--success)] font-semibold whitespace-nowrap">
            <CheckCircle2 className="w-3 h-3" /> Execution Settled (16 Stages Evaluated)
          </span>
        ) : activeStage && activeStage.status === 'started' ? (
          <span className={`flex items-center gap-1.5 font-medium whitespace-nowrap ${isDark ? 'text-[var(--accent-primary)]' : 'text-[var(--accent-primary)]'}`}>
            <span className={`w-1.5 h-1.5 rounded-none animate-ping ${isDark ? 'bg-[var(--accent-primary)]' : 'bg-[var(--accent-primary)]'}`} />
            Stage {activeStage.stage_number}: {activeStage.stage_name} ({activeStage.message || 'Processing...'})
          </span>
        ) : (
          <span className="text-[var(--text-muted)] whitespace-nowrap">Idle / Ready for query</span>
        )}
      </div>

      <div className="flex items-center gap-3 sm:gap-4 text-[10px] text-[var(--text-muted)] shrink-0 whitespace-nowrap">
        <span>Transpiler: sqlglot</span>
        <span>Checkpoint: Dolt CAS</span>
        <span>Safety Router: Dual-Path Guardrail</span>
      </div>
    </footer>
  );
};
