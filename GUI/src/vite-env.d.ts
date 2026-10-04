/// <reference types="vite/client" />

interface Window {
  electronAPI?: {
    isDesktop: boolean;
    platform: string;
    version: string;
    minimize?: () => void;
    maximize?: () => void;
    close?: () => void;
    onMenuAction?: (callback: (action: string) => void) => () => void;
  };
}
