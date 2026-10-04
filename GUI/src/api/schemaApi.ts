// src/api/schemaApi.ts
import { apiFetch } from './client';
import type { SchemaInfo } from '../types/schema';
import { getMockSchema } from '../mock/mockService';

export async function getSchema(dialect: string = 'mysql'): Promise<SchemaInfo> {
  try {
    return await apiFetch<SchemaInfo>(`/schema/${encodeURIComponent(dialect)}`);
  } catch (error) {
    return getMockSchema(dialect);
  }
}
