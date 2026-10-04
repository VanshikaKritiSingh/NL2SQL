// src/hooks/useWebSocket.ts
import { useEffect, useRef, useCallback } from 'react';
import { getWsUrl } from '../api/client';
import { usePipelineStore } from '../store/usePipelineStore';
import { useQueryStore } from '../store/useQueryStore';
import { useAppStore } from '../store/useAppStore';
import type { PipelineStageEvent } from '../types/pipeline';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const userId = useAppStore((s) => s.userId);
  const setWsConnected = usePipelineStore((s) => s.setWsConnected);
  const updateStage = usePipelineStore((s) => s.updateStage);
  const setApprovalPayload = useQueryStore((s) => s.setApprovalPayload);
  const setCurrentView = useAppStore((s) => s.setCurrentView);

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const ws = new WebSocket(getWsUrl(userId));
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data: PipelineStageEvent = JSON.parse(event.data);
          if (data.stage_number !== undefined) {
            updateStage(data);

            // Auto-trigger Approval Gate view if Stage 14 requires approval
            if (data.stage_number === 14 && data.status === 'started' && data.data?.approval_payload) {
              setApprovalPayload(data.data.approval_payload);
              setCurrentView('approval');
            }
          }
        } catch {
          // ignore malformed payloads
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setWsConnected(false);
    }
  }, [userId, setWsConnected, updateStage, setApprovalPayload, setCurrentView]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return wsRef;
}
