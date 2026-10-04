// src/store/usePipelineStore.ts
import { create } from 'zustand';
import type { PipelineStageEvent, PipelineStageStatus } from '../types/pipeline';
import { PIPELINE_STAGES } from '../types/pipeline';

export interface StageState {
  stage_number: number;
  stage_name: string;
  status: PipelineStageStatus;
  message: string | null;
}

interface PipelineState {
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
  currentQueryId: string | null;
  stages: StageState[];
  currentStageNumber: number;
  pipelineComplete: boolean;

  startPipeline: (queryId: string) => void;
  updateStage: (event: PipelineStageEvent) => void;
  resetPipeline: () => void;
}

const getInitialStages = (): StageState[] =>
  Object.entries(PIPELINE_STAGES).map(([num, name]) => ({
    stage_number: parseInt(num, 10),
    stage_name: name,
    status: 'pending',
    message: null,
  }));

export const usePipelineStore = create<PipelineState>((set) => ({
  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),
  currentQueryId: null,
  stages: getInitialStages(),
  currentStageNumber: 0,
  pipelineComplete: false,

  startPipeline: (queryId) =>
    set({
      currentQueryId: queryId,
      stages: getInitialStages(),
      currentStageNumber: 1,
      pipelineComplete: false,
    }),

  updateStage: (event) =>
    set((state) => {
      const stages = state.stages.map((s) =>
        s.stage_number === event.stage_number
          ? {
              ...s,
              status: event.status,
              message: event.message || null,
            }
          : s
      );
      return {
        stages,
        currentStageNumber: event.status === 'started' ? event.stage_number : state.currentStageNumber,
        pipelineComplete: event.stage_number === 16 && event.status === 'completed',
      };
    }),

  resetPipeline: () =>
    set({
      currentQueryId: null,
      stages: getInitialStages(),
      currentStageNumber: 0,
      pipelineComplete: false,
    }),
}));
