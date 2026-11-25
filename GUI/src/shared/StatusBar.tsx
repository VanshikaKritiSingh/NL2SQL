// src/shared/StatusBar.tsx — Primer 28px status bar
import React from 'react';
import { Activity, CheckCircle2 } from 'lucide-react';
import { usePipelineStore } from '../store/usePipelineStore';
import { useAppStore } from '../store/useAppStore';

export const StatusBar: React.FC = () => {
  const currentStageNumber = usePipelineStore((s) => s.currentStageNumber);
  const stages = usePipelineStore((s) => s.stages);
  const pipelineComplete = usePipelineStore((s) => s.pipelineComplete);
  const wsConnected = usePipelineStore((s) => s.wsConnected);
  const selectedModel = useAppStore((s) => s.selectedModel);
  const targetDialect = useAppStore((s) => s.targetDialect);

  const activeStage = stages.find((s) => s.stage_number === currentStageNumber);

  return (
    <footer className="h-7 shrink-0 border-t border-[var(--border-hairline)] bg-[var(--bg-panel)] px-3.5 flex items-center justify-between gap-3 font-mono text-[11px] text-[var(--text-recessive)] overflow-x-auto overflow-y-hidden whitespace-nowrap">
      <div className="flex items-center gap-2 shrink-0">
        <Activity className="w-3 h-3 shrink-0 text-[var(--accent-primary)]" aria-hidden="true" />
        <span className="text-[var(--text-body)]">Pipeline:</span>
        {pipelineComplete ? (
          <span className="flex items-center gap-1 text-[var(--success)] font-semibold">
            <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
            16 stages settled
          </span>
        ) : activeStage && activeStage.status === 'started' ? (
          <span className="flex items-center gap-1.5 text-[var(--accent-primary)]">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-primary)]" aria-hidden="true" />
            Stage {activeStage.stage_number}: {activeStage.stage_name}
            {activeStage.message ? ` — ${activeStage.message}` : ''}
          </span>
        ) : (
          <span>Idle</span>
        )}
      </div>

      <div className="flex items-center gap-3 sm:gap-4 shrink-0">
        <span>model: {selectedModel}</span>
        <span>dialect: {targetDialect}</span>
        <span className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-[var(--success)]' : 'bg-[var(--warning)]'}`}
            aria-hidden="true"
          />
          {wsConnected ? 'ws live' : 'ws offline'}
        </span>
      </div>
    </footer>
  );
};
