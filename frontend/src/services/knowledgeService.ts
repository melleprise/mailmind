import { api } from './api'; // Use named import for the configured axios instance
import { AxiosResponse } from 'axios';

// Interface for the KnowledgeField object returned by the API
export interface KnowledgeField {
    id: number;
    user: number; // Assuming user ID is returned, adjust if it's an object or just PrimaryKeyRelatedField
    key: string;
    value: string;
    created_at: string; // ISO date string
    updated_at: string; // ISO date string
}

// Interface for the payload when creating or updating a KnowledgeField
// Note: Backend might only allow updating 'value'
export interface KnowledgeFieldPayload {
    key: string;
    value: string;
}

const API_BASE_URL = 'core/knowledge-fields/'; // Update path to include 'core/'

const knowledgeService = {
    /**
     * Fetch all knowledge fields for the current user.
     */
    list: async (): Promise<KnowledgeField[]> => {
        try {
            const response: AxiosResponse<KnowledgeField[]> = await api.get(API_BASE_URL);
            return response.data;
        } catch (error) {
            console.error("Error listing knowledge fields:", error);
            throw error; // Re-throw to be handled by the calling component
        }
    },

    /**
     * Retrieve a specific knowledge field by its ID.
     * (May not be needed by the current KnowledgeSettings component)
     */
    get: async (id: number): Promise<KnowledgeField> => {
        try {
            const response: AxiosResponse<KnowledgeField> = await api.get(`${API_BASE_URL}${id}/`);
            return response.data;
        } catch (error) {
            console.error(`Error retrieving knowledge field ${id}:`, error);
            throw error;
        }
    },

    /**
     * Create a new knowledge field.
     */
    create: async (data: KnowledgeFieldPayload): Promise<KnowledgeField> => {
        try {
            const response: AxiosResponse<KnowledgeField> = await api.post(API_BASE_URL, data);
            return response.data;
        } catch (error) {
            console.error("Error creating knowledge field:", error);
            throw error;
        }
    },

    /**
     * Update an existing knowledge field (likely only the value).
     * The backend API might expect only the 'value' field in the payload.
     * If the key is also updatable, adjust the payload and API endpoint/method accordingly.
     */
    update: async (id: number, data: Partial<KnowledgeFieldPayload>): Promise<KnowledgeField> => {
        // Assuming PATCH is used for partial updates, and only 'value' is typically updated.
        // If PUT is used, the full payload might be required. Adjust as needed.
        // The backend might enforce that 'key' cannot be changed.
        try {
            // Send only the 'value' if that's what the backend expects for updates
            const payload: Partial<KnowledgeFieldPayload> = { value: data.value };
             // Use PATCH for partial update, PUT might require full object or behave differently
            const response: AxiosResponse<KnowledgeField> = await api.patch(`${API_BASE_URL}${id}/`, payload);
            return response.data;
        } catch (error) {
            console.error(`Error updating knowledge field ${id}:`, error);
            throw error;
        }
    },

    /**
     * Delete a knowledge field by its ID.
     */
    delete: async (id: number): Promise<void> => {
        try {
            await api.delete(`${API_BASE_URL}${id}/`);
        } catch (error) {
            console.error(`Error deleting knowledge field ${id}:`, error);
            throw error;
        }
    },
};

export default knowledgeService; 