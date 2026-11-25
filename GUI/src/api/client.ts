// src/api/client.ts
const API_BASE = '/api';

export function getApiToken(): string | null {
  if (typeof window === 'undefined') return null;
  return (
    (window as any).__NL2SQL_API_TOKEN__ ||
    (window as any).electronAPI?.token ||
    localStorage.getItem('NL2SQL_API_TOKEN') ||
    (import.meta as any).env?.VITE_NL2SQL_API_TOKEN ||
    null
  );
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = getApiToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options?.headers as Record<string, string>),
  };

  const res = await fetch(url, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const errorText = await res.text().catch(() => 'Unknown error');
    throw new Error(`API ${res.status}: ${errorText}`);
  }
  return res.json();
}

export function getWsUrl(userId: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = window.location.host;
  return `${proto}://${host}/ws/${userId}`;
}
