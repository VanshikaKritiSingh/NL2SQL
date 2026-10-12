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
      className="h-7 border-t px-4 flex items-center justify-between text-[11px] font-mono shrink-0 transition-colors border-[var(--border-main)] bg-[var(--bg-header)] text-[var(--text-muted)]"
    >
      <div className="flex items-center gap-2">
        <Activity className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
        <span className="font-semibold text-[var(--text-secondary)]">Pipeline:</span>
        {pipelineComplete ? (
          <span className="flex items-center gap-1 text-[var(--success)] font-semibold">
            <CheckCircle2 className="w-3 h-3" /> Execution Settled (16 Stages Evaluated)
          </span>
        ) : activeStage && activeStage.status === 'started' ? (
          <span className="flex items-center gap-1.5 text-[var(--accent-primary)] font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-primary)] animate-ping" />
            Stage {activeStage.stage_number}: {activeStage.stage_name} ({activeStage.message || 'Processing...'})
          </span>
        ) : (
          <span className="text-[var(--text-muted)]">Idle / Ready for query</span>
        )}
      </div>

      <div className="flex items-center gap-4 text-[10px] text-[var(--text-muted)]">
        <span>Transpiler: sqlglot</span>
        <span>Checkpoint: Dolt CAS</span>
        <span>Safety Router: Dual-Path Guardrail</span>
      </div>
    </footer>
  );
};
