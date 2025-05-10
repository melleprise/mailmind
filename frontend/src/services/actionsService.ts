import axiosInstance from '@/lib/axiosInstance';
import { queryClient } from '../lib/queryClient';
import { queryKeys } from '../lib/queryKeys';

// Typen
interface PromptTemplateSimple {
  id: number;
  name: string;
  description: string;
}

export interface AIAction {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
  prompts: PromptTemplateSimple[];
}

export type AIActionCreateData = Omit<AIAction, 'id' | 'created_at' | 'updated_at' | 'prompts'> & {
  prompt_ids: number[];
};

export type AIActionUpdateData = Partial<AIActionCreateData>;

// Service-Funktionen

/**
 * Ruft alle AI Actions ab.
 */
export const getAIActions = async (): Promise<AIAction[]> => {
  const response = await axiosInstance.get<AIAction[]>('/actions/');
  return response.data;
};

/**
 * Erstellt eine neue AI Action.
 */
export const createAIAction = async (data: AIActionCreateData): Promise<AIAction> => {
  const response = await axiosInstance.post<AIAction>('/actions/', data);
  // Invalidate cache nach Erstellung
  queryClient.invalidateQueries({ queryKey: queryKeys.aiActions });
  return response.data;
};

/**
 * Aktualisiert eine bestehende AI Action.
 */
export const updateAIAction = async (id: number, data: AIActionUpdateData): Promise<AIAction> => {
  const response = await axiosInstance.put<AIAction>(`/actions/${id}/`, data);
  // Invalidate cache nach Update
  queryClient.invalidateQueries({ queryKey: queryKeys.aiActions });
  queryClient.invalidateQueries({ queryKey: queryKeys.aiAction(id) });
  return response.data;
};

/**
 * Löscht eine AI Action.
 */
export const deleteAIAction = async (id: number): Promise<void> => {
  await axiosInstance.delete(`/actions/${id}/`);
  // Invalidate cache nach Löschung
  queryClient.invalidateQueries({ queryKey: queryKeys.aiActions });
  queryClient.invalidateQueries({ queryKey: queryKeys.aiAction(id) });
};

/**
 * Startet die Ausführung einer AI Action.
 */
export const runAIAction = async (id: number): Promise<{ status: string; action: string }> => {
  const response = await axiosInstance.post<{ status: string; action: string }>(`/actions/${id}/run/`);
  return response.data;
}; 