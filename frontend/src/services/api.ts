import axios, { AxiosRequestHeaders, AxiosResponse } from 'axios';
// Attempt to import from the library directly or a common config location
// Assuming queryClient is initialized elsewhere and exported, 
// and queryKeys might be defined in a central place.
// If these paths are wrong, further investigation is needed.
import { QueryClient } from '@tanstack/react-query'; // Assuming library usage for QueryClient type
// Keep queryClient and queryKeys imports commented until location is confirmed
// import { queryClient } from '../lib/react-query'; // Original problematic import
// import { queryKeys } from '../lib/query-keys'; // Original problematic import
import { queryClient } from '../lib/queryClient'; // Corrected import path
import { queryKeys } from '../lib/queryKeys'; // Corrected import path
// import { logger } from '../lib/logger'; // Assuming logger is correct -> Error: logger not found

// Import shared types
import { PromptTemplate as SharedPromptTemplate, AvailableApiModel } from '../lib/types'; // Import shared types

// Define constants
const EMAILS_PAGE_SIZE = 30; // Default page size for email fetching

// Typdefinitionen
declare const process: {
  env: {
    REACT_APP_API_URL?: string;
  };
};

interface AxiosInstance {
  get: <T = any>(url: string, config?: any) => Promise<{ data: T }>;
  post: <T = any>(url: string, data?: any, config?: any) => Promise<{ data: T }>;
  put: <T = any>(url: string, data?: any, config?: any) => Promise<{ data: T }>;
  patch: <T = any>(url: string, data?: any, config?: any) => Promise<{ data: T }>;
  delete: <T = any>(url: string, config?: any) => Promise<{ data: T }>;
  defaults: {
    headers: {
      common: {
        [key: string]: string;
      };
    };
  };
  interceptors: {
    response: {
      use: (onFulfilled: (response: any) => any, onRejected: (error: any) => any) => void;
    };
    request: {
      use: (onFulfilled: (config: any) => any, onRejected: (error: any) => any) => void;
    };
  };
}

interface AxiosStatic {
  create: (config: any) => AxiosInstance;
}

// Basic interfaces for type safety
export interface EmailAccount {
  id: number;
  name: string;
  email: string;
  provider: string;
}

interface Email {
  id: number;
  subject: string;
  from_address: string;
  to_addresses: string[];
  content: string;
  read: boolean;
  flagged: boolean;
  received_at: string;
  preview?: string;
}

interface Suggestion {
  id: string;
  email_id: number;
  type: string;
  content: string;
}

interface Contact {
  id: number;
  email: string;
  name: string;
}

// Use import.meta.env for Vite environment variables
// Append /api/v1/ to the base URL
const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';

// Rename the axios instance to avoid conflict
const apiClient = axios.create({
  baseURL: API_BASE_URL, // Use the updated base URL
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include auth token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers['Authorization'] = `Token ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Export the configured client as 'api'
export { apiClient as api };

// Typdefinition für Test-Daten
interface EmailAccountTestData {
  email: string;
  imap_server: string;
  imap_port: number;
  imap_use_ssl: boolean;
  username: string;
  password: string;
}

// Define the response structure for suggested settings *before* using it
interface SuggestSettingsResponse {
  status: string; // e.g., 'success' or 'error'
  settings: AccountSettings | null; // Settings object or null if not found/error
  message?: string; // Optional message from backend
}

// E-Mail-Konto-Endpoints - Add /core/ prefix
export const emailAccounts = {
  list: () => apiClient.get<EmailAccount[]>('/core/email-accounts/'),
  create: (data: Partial<EmailAccount>) => apiClient.post<EmailAccount>('/core/email-accounts/', data),
  update: (id: number, data: Partial<EmailAccount>) => apiClient.put<EmailAccount>(`/core/email-accounts/${id}/`, data),
  delete: (id: number) => apiClient.delete(`/core/email-accounts/${id}/`),
  // Keep testConnection under /auth/ for now, as it might not require full account setup
  testConnection: (data: EmailAccountTestData) => 
    apiClient.post<{ status: string; message: string; errors?: any }>('/auth/email-accounts/test-connection/', data),
  sync: (id: number) => apiClient.post(`/core/email-accounts/${id}/sync/`),
  // Neuer Endpunkt zum Abrufen der Ordnerstruktur - Korrigierter Typ!
  getFolders: (id: number) => apiClient.get<{ folders: string[] }>(`/email-accounts/${id}/folders/`), 
  // Add function to suggest settings based on email domain
  // Use the SuggestSettingsResponse interface defined above
  suggestSettings: (email: string): Promise<AxiosResponse<SuggestSettingsResponse>> => 
    apiClient.post<SuggestSettingsResponse>('/core/email-accounts/suggest-settings/', { email }),
};

// Define AccountSettings interface if not already globally available
// Ensure this matches the expected backend response structure for suggested settings
interface AccountSettings {
  imap_server: string;
  imap_port: number;
  imap_use_ssl: boolean;
  smtp_server: string;
  smtp_port: number;
  smtp_use_tls: boolean;
}

// E-Mail-Endpoints
export const emails = {
  list: () => apiClient.get<Email[]>('/core/emails/'),
  get: (id: number) => apiClient.get<Email>(`/core/emails/${id}/`),
  markRead: (id: number) => apiClient.post(`/core/emails/${id}/mark-read/`),
  flag: (id: number) => apiClient.post(`/core/emails/${id}/flag/`),
  unflag: (id: number) => apiClient.post(`/core/emails/${id}/unflag/`),
};

// Interface for the paginated response
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Interface für die Ordnerstruktur (passend zum FolderSerializer)
export interface FolderItem {
  name: string;
  full_path: string;
  delimiter: string;
  flags: string[];
  children?: FolderItem[]; // Optional, da rekursiv
}

// --- API Functions ---

/**
 * Fetches the list of prompt templates.
 */
export const getPrompts = async (): Promise<SharedPromptTemplate[]> => {
  try {
    const response = await apiClient.get<SharedPromptTemplate[]>('/prompts/templates/'); // Corrected endpoint
    return response.data;
  } catch (error) {
    console.error('Error fetching prompt templates:', error);
    // Consider how to handle errors - throw or return empty array?
    throw error; 
  }
};

/**
 * Fetches a list of emails with pagination and optional filtering.
 * RENAMED from fetchEmails to getEmails
 */
export const getEmails = async ({
  limit = EMAILS_PAGE_SIZE, // Use the constant defined in Dashboard.tsx or define here
  page = 1, // Default to page 1 instead of offset 0
  folderName = 'INBOX',
}: {
  limit?: number;
  page?: number; // Changed from offset to page
  folderName?: string | null;
}): Promise<PaginatedResponse<EmailListItem>> => {
  try {
    // Use page and page_size (from limit) as parameters
    const params: Record<string, any> = { limit, page };
    if (folderName) {
      params.folder_name = folderName;
    }
    // Correctly passes params
    const response = await apiClient.get<PaginatedResponse<EmailListItem> | EmailListItem[]>('/core/emails/', { // Allow array response type
      params: params
    });
    // Backend should return correct structure, no wrapping needed
    console.log('[api.ts] getEmails (formerly fetchEmails) raw response:', response);
    
    // Check if backend returned a flat array instead of the expected paginated structure
    if (Array.isArray(response.data)) {
        console.warn('[api.ts] getEmails received a flat array. Wrapping into PaginatedResponse. Backend endpoint /core/emails/ might need fixing.');
        // Wrap the array into the PaginatedResponse structure
        return {
            count: response.data.length, // Estimate count based on returned items
            next: null, // Cannot determine pagination links from flat array
            previous: null,
            results: response.data as EmailListItem[] // Type assertion needed here
        };
    } else if (response.data && typeof response.data === 'object' && 'results' in response.data) {
         // If it's the expected structure, return it directly
        return response.data as PaginatedResponse<EmailListItem>;
    } else {
        // Handle unexpected structure
        console.error('[api.ts] getEmails received unexpected data structure:', response.data);
        // Return a default empty paginated response to avoid breaking callers
        return { count: 0, next: null, previous: null, results: [] };
    }
    
  } catch (error) {
    console.error('Error fetching emails:', error);
    throw error; 
  }
};

// --- DEPRECATED EMAIL LIST FUNCTION --- 
// Keeping the old function just in case, renamed to avoid conflicts
export const getEmails_DEPRECATED = async (limit = 10, offset = 0): Promise<PaginatedEmailsResponse> => {
  console.warn('[api.ts] DEPRECATED function getEmails_DEPRECATED called. Use getEmails instead.');
  try {
    // This version incorrectly omits params
    const response = await apiClient.get<any>('/core/emails/'); // Use 'any' as response might be array
    console.log('[api.ts] getEmails_DEPRECATED raw response data:', response.data);
    
    // REMOVED incorrect wrapping logic
    // Check if the response is already paginated
    // if (response.data && typeof response.data === 'object' && 'results' in response.data && 'count' in response.data) {
    //   console.log('[api.ts] getEmails_DEPRECATED received paginated structure as expected.');
    //   return response.data as PaginatedEmailsResponse; 
    // } else if (Array.isArray(response.data)) {
    //   // If backend incorrectly returned just an array, wrap it (problematic)
    //   console.warn('[api.ts] getEmails_DEPRECATED received direct array instead of paginated structure. Attempting to wrap it (THIS IS LIKELY WRONG).');
    //   return {
    //     count: response.data.length, 
    //     next: null, // Cannot determine next/previous from flat array
    //     previous: null,
    //     results: response.data as EmailListItem[],
    //   };
    // } else {
    //   console.error('[api.ts] getEmails_DEPRECATED received unexpected data structure:', response.data);
    //   throw new Error('Unexpected response structure from emails endpoint.');
    // }
    // Instead of wrapping, now we assume the old function is broken if it doesn't get a paginated response
    if (response.data && typeof response.data === 'object' && 'results' in response.data && 'count' in response.data) {
      return response.data as PaginatedEmailsResponse;
    } else {
       console.error('[api.ts] getEmails_DEPRECATED received non-paginated data. Backend needs fixing or call signature is wrong.');
       // Return a default empty paginated response to avoid breaking callers expecting the structure
       return { count: 0, next: null, previous: null, results: [] };
    }

  } catch (error) {
    console.error('Error fetching emails with getEmails_DEPRECATED:', error);
    throw error;
  }
};
// --- END DEPRECATED --- 

/**
 * Fetches the details for a single email.
 */
export const getEmailById = async (emailId: number): Promise<EmailDetailData> => {
  try {
    const response = await apiClient.get<EmailDetailData>(`/core/emails/${emailId}/`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching email ${emailId}:`, error);
    throw error;
  }
};

/**
 * Marks an email as read.
 */
export const markEmailRead = async (emailId: number): Promise<void> => {
  try {
    await apiClient.post(`/core/emails/${emailId}/mark-read/`);
  } catch (error) {
    console.error(`Error marking email ${emailId} as read:`, error);
    throw error;
  }
};

/**
 * Toggles the flagged status of an email.
 */
export const toggleEmailFlag = async (emailId: number): Promise<{ status: string; is_flagged: boolean }> => {
  try {
    const response = await apiClient.post<{ status: string; is_flagged: boolean }>(`/core/emails/${emailId}/flag/`);
    return response.data;
  } catch (error) {
    console.error(`Error toggling flag for email ${emailId}:`, error);
    throw error;
  }
};

// KI-Vorschläge-Endpoints
export const suggestions = {
  list: () => apiClient.get<Suggestion[]>('/core/suggestions/'),
  get: (id: string) => apiClient.get<Suggestion>(`/core/suggestions/${id}/`),
  accept: (id: string) => apiClient.post(`/core/suggestions/${id}/accept/`),
  reject: (id: string) => apiClient.post(`/core/suggestions/${id}/reject/`),
};

// Kontakt-Endpoints
export const contacts = {
  list: (params?: { search?: string }) => apiClient.get<Contact[]>('/core/contacts/', { params }),
  get: (id: number) => apiClient.get<Contact>(`/core/contacts/${id}/`),
};

// API Credential Endpoints
interface ApiCredentialStatusResponse {
    exists: boolean; // This might be implicitly true if status is 200, false if 404
    provider: string;
    api_key_set: boolean; // Add this field, expect it from backend on GET
}

interface ApiCredentialCreateUpdateResponse {
    // Assuming backend returns this on successful POST/PUT
    // Adjust based on actual backend response structure
    id?: number; // Or string if UUID
    provider: string;
    api_key_set: boolean; // Should always be true after successful save/update
    message?: string; // Optional success message from backend
}

export const apiCredentials = {
  // GET /api/v1/core/api-credentials/{provider}/
  // Returns 200 OK with { provider, api_key_set } if entry exists
  // Returns 404 Not Found if no entry exists for the user/provider
  getStatus: (provider: string): Promise<AxiosResponse<ApiCredentialStatusResponse>> =>
    apiClient.get(`/core/api-credentials/${provider}/`),

  // POST /api/v1/core/api-credentials/
  // Body: { provider: string, api_key: string }
  // Returns 201 Created with { id?, provider, api_key_set, message? } on success
  create: (provider: string, apiKey: string): Promise<AxiosResponse<ApiCredentialCreateUpdateResponse>> =>
    apiClient.post(`/core/api-credentials/`, { provider: provider, api_key: apiKey }),

  // PUT /api/v1/core/api-credentials/{provider}/
  // Body: { api_key: string }
  // Returns 200 OK with { id?, provider, api_key_set, message? } on success
  update: (provider: string, apiKey: string): Promise<AxiosResponse<ApiCredentialCreateUpdateResponse>> =>
    apiClient.put(`/core/api-credentials/${provider}/`, { api_key: apiKey }),

  // DELETE /api/v1/core/api-credentials/{provider}/
  // Returns 204 No Content on success
  delete: (provider: string): Promise<AxiosResponse<void>> =>
    apiClient.delete(`/core/api-credentials/${provider}/`),

  // NEU: Endpunkt zum Abrufen verfügbarer Modelle - Korrigiert
  getModels: (provider: string) => apiClient.get(`/core/ai/available-models/${provider}/`),

  // Funktion zum Starten des Checks (verwendet die neue URL)
  check: (provider: string) => apiClient.post(`/core/credentials/${provider}/check/`)
};

// Interceptor für Fehlerbehandlung
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Check if the error is a 401 and the original request was NOT to an auth endpoint
    const originalRequestUrl = error.config.url as string || '';
    const isAuthRequest = originalRequestUrl.includes('/auth/login') || 
                          originalRequestUrl.includes('/auth/register') ||
                          originalRequestUrl.includes('/auth/verify-email'); // Add other auth paths if needed

    if (error.response?.status === 401 && !isAuthRequest) {
      // Unauthorized on a non-auth request (likely expired token)
      console.warn('Unauthorized request to non-auth endpoint, logging out.');
      localStorage.removeItem('token');
      // Use react-router navigation if available, otherwise fallback
      // This assumes you might have access to navigate outside of components, which is tricky.
      // A simpler approach might be needed depending on setup, or handle this in AuthContext.
      // For now, keep the simple redirect but only for non-auth 401s.
      window.location.href = '/login';
    }
    // For all other errors (including 401 on auth pages), just reject the promise
    return Promise.reject(error);
  }
);

export interface LoginData {
  email: string;
  password: string;
}

export interface RegisterData extends LoginData {
  confirmPassword: string;
}

export interface AuthResponse {
  token: string;
  user: {
    email: string;
    // Add other user properties as needed
  };
}

// Define the User interface returned by the backend
interface UserData {
  pk: number; // Assuming the backend uses 'pk'
  email: string;
  first_name?: string;
  last_name?: string;
  // Add other fields returned by your user endpoint
}

// Auth-Endpoints
export const authApi = {
  login: async (data: LoginData): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/login/', data);
    return response.data;
  },

  register: async (data: Omit<RegisterData, 'confirmPassword'>): Promise<AuthResponse> => {
    // Ensure only necessary fields are sent if confirmPassword is frontend-only
    const { email, password } = data;
    const response = await apiClient.post<AuthResponse>('/auth/register/', { email, password });
    return response.data;
  },

  verifyEmail: async (token: string): Promise<{ message: string }> => {
    // Send GET request to the verification endpoint with the token
    const response = await apiClient.get<{ message: string }>(`/auth/verify-email/${token}/`);
    return response.data;
  },

  // Function to get current user data using the token
  getCurrentUser: async (): Promise<UserData> => {
    const response = await apiClient.get<UserData>('/auth/user/'); // Assuming this is your user detail endpoint
    return response.data;
  },

  /**
   * Resends the verification email for a given email address.
   */
  resendVerificationEmail: async (email: string): Promise<{ message: string }> => {
    try {
      const response = await apiClient.post<{ message: string }>('/core/resend-verification/', { email });
      return response.data;
    } catch (error) {
      console.error(`Error resending verification email for ${email}:`, error);
      throw error; // Rethrow to be caught by the component
    }
  },

  // Add other auth related functions if needed, e.g., password reset
};

// --- Type Definitions (align with backend serializers) ---

// Consolidated EmailListItem based on previous usage and common list needs
export interface EmailListItem {
  id: number;
  subject: string;
  short_summary: string | null; // Useful for previews
  from_address: string;
  from_name: string; // Useful for display
  to_addresses: string[];
  cc_addresses: string[];
  bcc_addresses: string[];
  received_at: string; // Prefer received_at for sorting/display?
  sent_at: string | null;
  is_read: boolean;
  is_flagged: boolean;
  has_attachments: boolean;
  attachments: {
    id: number;
    filename: string;
    content_type: string;
    size: number;
    file: string; // URL to file
    content_id: string | null;
  }[];
  body_text?: string; // Optional for preview generation if needed
  ai_processed?: boolean;
  ai_processed_at?: string | null;
  account?: number; // Include if available/needed
}

// Ensure PaginatedResponse uses the consolidated EmailListItem
export interface PaginatedEmailsResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: EmailListItem[]; // Uses the single definition above
}

// Remove potentially conflicting/duplicate EmailListItem definition later in the file if it exists
// (The apply model should handle removing the duplicate definitions based on context)

// Ensure getEmailDetail extends the correct EmailListItem
export interface EmailDetailData extends EmailListItem { 
  medium_summary: string | null;
  to_contacts: { id: number; name: string; email: string; }[];
  cc_contacts: { id: number; name: string; email: string; }[];
  bcc_contacts: { id: number; name: string; email: string; }[];
  body_html: string;
  is_replied: boolean; // Added based on serializer
  attachments: {
    id: number;
    filename: string;
    content_type: string;
    size: number;
    file: string; // URL to file
    content_id: string | null; 
  }[];
  suggestions?: AISuggestion[]; 
  markdown_body?: string | null; // NEUES FELD (optional)
}

// Update getEmailDetail to expect EmailDetailData
export const getEmailDetail = async (emailId: number): Promise<EmailDetailData> => {
    try {
        const response = await apiClient.get<EmailDetailData>(`/core/emails/${emailId}/`);
        console.log(`[api.ts] getEmailDetail response data for ID ${emailId}:`, response.data);
        // Add validation if necessary
        return response.data;
    } catch (error) {
        console.error(`Error fetching email detail for ${emailId}:`, error);
        if (axios.isAxiosError(error) && error.response) {
             console.error(`[api.ts] getEmailDetail error response data for ID ${emailId}:`, error.response.data);
        }
        throw error;
    }
};

// Add the new function to regenerate suggestions
export const regenerateEmailSuggestions = async (id: number): Promise<void> => {
  try {
    // Make POST request to the custom action endpoint
    await apiClient.post(`/core/emails/${id}/generate-suggestions/`);
    // No specific data needed in response body based on backend implementation (202 Accepted)
  } catch (error) {
    console.error(`Error triggering suggestion regeneration for email ${id}:`, error);
    // Re-throw the error to be caught by the calling component
    throw error;
  }
};

// Function to get the CSRF token from cookies
function getCookie(name: string): string | null {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Add a request interceptor to include the CSRF token
apiClient.interceptors.request.use(config => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken && config.headers) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  // Ensure Authorization header is set if token exists (for Django Rest Framework TokenAuthentication)
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers['Authorization'] = `Token ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

// Modify regenerateSuggestions for the ASYNC flow (returns 202 Accepted)
export const regenerateSuggestions = async (emailId: number): Promise<void> => {
  try {
    // The backend view now returns 202 Accepted with { status: '...' }
    // We don't need to explicitly type or use the response body here.
    await apiClient.post(`/core/emails/${emailId}/generate-suggestions/`);
    console.log(`[api] ASYNC Suggestion regeneration trigger successful for ${emailId}.`);
    // No return value needed, promise resolves on success (2xx status)
    } catch (error) {
    console.error(`[api] Error triggering ASYNC suggestion regeneration for ${emailId}:`, error);
    // Re-throw the error so the calling component (Dashboard) can handle it
        throw error;
    }
};

// Function to archive an email (Example - adjust API endpoint/method if different)
export const archiveEmail = async (emailId: number): Promise<void> => {
    try {
        // Placeholder: Replace with actual API call, e.g., PATCH to set is_archived=true
        // or move to a specific folder
        await apiClient.patch(`/core/emails/${emailId}/`, { is_archived: true }); // Example patch
        console.log(`Email ${emailId} marked for archive (adjust API call)`);
    } catch (error) {
        console.error(`Error archiving email ${emailId}:`, error);
        throw error;
    }
};

// --- Update existing AI Suggestion --- 
export const updateAiSuggestion = async (
  suggestionId: string, data: Partial<AISuggestion>
): Promise<AISuggestion> => {
    console.log(`[api] Updating AI suggestion ${suggestionId} with data:`, data);
    const url = `/suggestions/${suggestionId}/`; // Ensure this matches backend URL pattern for detail view
    try {
        const response = await apiClient.patch<AISuggestion>(url, data);
        console.log(`[api] Update for suggestion ${suggestionId} successful:`, response.data);
        return response.data;
    } catch (error) {
        console.error(`[api] Error updating suggestion ${suggestionId}:`, error);
        throw error;
    }
};

// NEUE FUNKTION für direktes Refine von Text
export const refineTextDirectly = async (
  customPrompt: string,
  currentSubject: string,
  currentBody: string,
  // NEU: Optionaler Parameter für reine Korrektur
  is_pure_correction: boolean = false 
): Promise<{ refined_subject: string; refined_body: string }> => { 
  try {
    console.log(`[api.ts] refineTextDirectly called. Pure Correction: ${is_pure_correction}`);
    const payload = {
      custom_prompt: customPrompt,
      current_subject: currentSubject,
      current_body: currentBody,
      is_pure_correction: is_pure_correction // Sende das Flag mit
    };
    // Verwende den korrekten Endpunkt (angenommen /refine-text/ existiert)
    const response = await apiClient.post<{ refined_subject: string; refined_body: string }>('/ai/refine-text/', payload);
    console.log("[api.ts] refineTextDirectly response:", response.data);
    return response.data;
  } catch (error) {
    console.error('Error refining text directly:', error);
    // Re-throw oder spezifischere Fehlerbehandlung
    throw error;
  }
};

// Interface for the snippet correction response from the backend
interface CorrectedSnippetResponse {
    corrected_snippet: string;
}

// Type guard to check if the response is a snippet correction
export function isCorrectedSnippetResponse(response: any): response is CorrectedSnippetResponse {
    return typeof response === 'object' && response !== null && 'corrected_snippet' in response;
}

// Modify the function to accept optional selected_text and handle different responses
export const correctSuggestionField = async (
    suggestionId: string,
    field: 'subject' | 'body' | 'both',
    selected_text?: string // Optional selected text
): Promise<AISuggestion | CorrectedSnippetResponse> => { // Return type can be either
    try {
        const requestData: { field: string; selected_text?: string } = { field };
        if (selected_text) {
            requestData.selected_text = selected_text;
        }
        // Korrigierte URL: /suggestions/${suggestionId}/correct-text/ statt /ai-suggestions/${suggestionId}/correct-text/.
        const response = await apiClient.post<AISuggestion | CorrectedSnippetResponse>(
            `/suggestions/${suggestionId}/correct-text/`, // KORREKTE URL!
            requestData // Send the data object
        );
        
        // Log based on what was requested
        if (selected_text) {
             console.log(`[api] Snippet correction request for suggestion ${suggestionId} successful.`);
        } else {
             console.log(`[api] Full field correction request for suggestion ${suggestionId} (field: ${field}) successful.`);
        }
        
        return response.data; // Return the data (either full object or snippet object)
    } catch (error) {
        console.error(`[api] Error requesting correction for suggestion ${suggestionId} (field: ${field}, selected: ${!!selected_text}):`, error);
        throw error;
    }
};

// NEW: Function to trigger AI refinement for a suggestion
export const refineSuggestion = async (
    suggestionId: string,
    field: string,
    customPrompt: string,
    selectedText?: string
): Promise<AISuggestion> => {
    // Korrigierte URL: /ai-suggestions/... statt /core/ai-suggestions/...
    const url = `/ai-suggestions/${suggestionId}/refine`; // Corrected: Removed trailing slash
    const data = {
        field: field,
        custom_prompt: customPrompt,
        selected_text: selectedText,
    };
    console.log(`[api] Requesting refinement for suggestion ${suggestionId} with data:`, data);
    try {
        // Adjust the expected response type for the API call
        const response = await apiClient.post<AISuggestion>(
            url,
            data
        );
        console.log(`[api] Refinement request for suggestion ${suggestionId} successful.`);
        return response.data;
    } catch (error) {
        console.error(`[api] Error requesting refinement for suggestion ${suggestionId}:`, error);
        throw error;
    }
};

// Typdefinition für einen einzelnen AI-Vorschlag (basierend auf AISuggestionSerializer)
export interface AISuggestion {
  id: string; // In Django oft UUID, daher string
  type: string;
  title: string;
  content: string;
  status: string;
  created_at: string;
  processing_time: number;
  intent_summary: string | null;
  suggested_subject: string | null;
  // Füge hier weitere Felder hinzu, falls sie vom Backend gesendet werden
}

// --- NEUE FUNKTION: API Key Check (verwendet die neue URL) ---
/**
 * Initiates the backend check for a specific provider's API key.
 * Backend fetches the key from the DB.
 */
export const checkApiKey = async (provider: string): Promise<void> => {
  try {
    // Use the correct endpoint based on core/urls.py
    await apiClient.post(`/core/credentials/${provider}/check/`); 
  } catch (error) {
    console.error(`Error checking API key for ${provider}:`, error);
    // Rethrow or handle as needed by the caller
    throw error; 
  }
};
// --- ENDE NEUE FUNKTION ---

// Interface for PromptTemplate
interface PromptTemplate {
  name: string;
  description: string;
  template: string;
  provider: string;
  model_name: string;
  is_active: boolean;
  // Add other fields if needed (created_at, updated_at)
}

// Define the type for the API response
export interface AvailableModelsResponse {
  models: AvailableApiModel[];
}

// --- BEGIN: AI Request Log Types ---
export interface AIRequestLog {
  id: number;
  timestamp: string; // ISO string format
  user_email: string | null;
  provider: string;
  model_name: string;
  is_success: boolean;
  triggering_source: string | null;
  duration_ms: number | null;
}

export interface AIRequestLogDetail extends AIRequestLog {
  prompt_text: string;
  raw_response_text: string;
  status_code: number;
  error_message: string | null;
  // Include all fields from the Django model
}
// --- END: AI Request Log Types ---

// --- BEGIN: AI Request Log API Functions ---
export const getAiRequestLogs = async (): Promise<AIRequestLog[]> => {
  const response = await apiClient.get<AIRequestLog[]>('/core/ai-request-logs/');
  return response.data;
};

export const getAiRequestLogDetail = async (logId: number): Promise<AIRequestLogDetail> => {
  const response = await apiClient.get<AIRequestLogDetail>(`/core/ai-request-logs/${logId}/`);
  return response.data;
};
// --- END: AI Request Log API Functions ---

// --- END: Prompt Template API Functions ---

/**
 * Fetches the list of available models stored for a specific provider.
 */
export const getAvailableModels = async (provider: string): Promise<AvailableApiModel[]> => {
  try {
    // Corrected URL to match backend core/urls.py definition
    // Backend ListAPIView returns a list directly, not nested under 'models'
    const response = await apiClient.get<AvailableApiModel[]>(`/core/ai/available-models/${provider}/`); 
    return response.data; // Return the list directly
  } catch (error) {
    console.error(`[api] Error fetching available models for ${provider}:`, error);
    // Return empty array or re-throw based on how errors should be handled upstream
    return []; 
  }
};

// --- The following code was likely deleted by mistake and is being restored ---

export const correctAiSuggestion = async (
    suggestionId: string, // Keep suggestionId as parameter name passed from component
    field: 'subject' | 'body',
    selectedText?: string
): Promise<{ corrected_snippet?: string } | AISuggestion> => {
    const payload = { field, selected_text: selectedText };
    // logger.info(`Calling correctAiSuggestion for ID: ${suggestionId}, Field: ${field}, Snippet: ${!!selectedText}`);
    try {
        // Make sure the URL matches the backend router configuration
        const response = await apiClient.post<{ corrected_snippet?: string } | AISuggestion>(
            `/ai-suggestions/${suggestionId}/correct/`, // Corrected URL path segment
            payload
        );
        
        // logger.debug("Correct AI Suggestion API response:", response.data);

        // Determine return type based on response content
        if (response.data && typeof (response.data as any).corrected_snippet === 'string') {
            // logger.info(`Correction successful (Snippet) for suggestion ${suggestionId}`);
            return { corrected_snippet: (response.data as any).corrected_snippet };
        } else if (response.data && (response.data as AISuggestion).id) {
            // logger.info(`Correction successful (Full Field) for suggestion ${suggestionId}`);
            // Update the specific suggestion in the cache
            // Need the actual queryClient instance here. Placeholder for now.
            queryClient.setQueryData<AISuggestion | undefined>(
                [queryKeys.aiSuggestions, suggestionId], // Key for individual suggestion - TODO: Check if this key structure is correct
                (oldData) => oldData ? { ...oldData, ...(response.data as AISuggestion) } : (response.data as AISuggestion)
            );
            // Invalidate the list query to potentially refetch or trigger updates
            // queryClient.invalidateQueries({ queryKey: [queryKeys.aiSuggestions] });
            // Invalidate the query for the list of suggestions to ensure UI updates
            queryClient.invalidateQueries({ queryKey: [queryKeys.aiSuggestions] }); // Use the base key for the list

            return response.data as AISuggestion; // Return the full updated suggestion
        } else {
             // logger.error(`Unexpected response structure from correction API for suggestion ${suggestionId}:`, response.data);
             console.error(`Unexpected response structure from correction API for suggestion ${suggestionId}:`, response.data); // Use console.error instead
            throw new Error("Unexpected response structure from correction API.");
        }
    } catch (error: any) {
        console.error(`Error correcting AI suggestion ${suggestionId}:`, error);
        throw error;
    }
};

// --- BEGIN: Folder Suggestion API Function ---

// Define the expected JSON structure for the folder suggestion response
export interface FolderStructureSuggestion { 
    [key: string]: FolderStructureSuggestion | {}; // Recursive type: keys are strings, values are nested objects or empty objects
}

export const suggestFolderStructure = async (): Promise<FolderStructureSuggestion> => {
    try {
        const response = await apiClient.post<FolderStructureSuggestion>('/core/ai/suggest-folder-structure/');
        return response.data;
    } catch (error) {
        console.error('Error suggesting folder structure:', error);
        // Rethrow the error so the component can handle it (show message, etc.)
        throw error;
    }
};

// --- END: Folder Suggestion API Function ---

// Type for AI Request Log entries
export interface AIRequestLog {
  id: number;
  timestamp: string;
  action_name: string;
  provider: string;
  model: string;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  status_code: number;
  success: boolean;
  response_time_ms: number;
  user_id: number;
}

// Type for the result of checking API keys
export interface ApiKeyCheckResult {
  [providerId: string]: {
    name: string;
    status: 'not_configured' | 'configured_no_key' | 'valid' | 'invalid' | 'error';
    error?: string | null;
  };
}

// Check API Keys validity
export const checkApiKeys = async () => {
  const response = await apiClient.post<ApiKeyCheckResult>('/core/ai/check-api-keys/');
  // Note: This might return 400 if any key is invalid, but Axios might throw.
  // We might need error handling here or in the component to show partial success/failure.
  return response.data;
};

// --- REMOVED Combined Export - Individual exports are sufficient ---
// export const api = {
//   // ... other api functions ...
//   emailAccounts,
//   getEmails,
//   getEmailDetail,
//   apiCredentials,
//   suggestFolderStructure,
//   getAIRequestLogs,
//   checkApiKeys
// }; 

// --- NEW FUNCTION --- 
export const markEmailAsSpamAPI = async (id: number): Promise<void> => {
    try {
        const response = await apiClient.post(`/emails/${id}/mark-spam/`);
        // Check response status if needed, but typically 2xx indicates success
        if (response.status < 200 || response.status >= 300) {
            throw new Error(`Server responded with status ${response.status}`);
        }
        console.log(`API call successful: Marked email ${id} as spam.`);
        // No data expected on success, return void
    } catch (error) {
        console.error(`Error marking email ${id} as spam via API:`, error);
        // Re-throw the error so the calling component can handle it (e.g., show an alert)
        if (axios.isAxiosError(error) && error.response) {
             throw new Error(error.response.data.error || `Failed to mark as spam (status ${error.response.status})`);
        } else {
             throw error; // Keep original error if not Axios error
        }
    }
}; 

// --- NEU: Funktion zum Verfeinern eines E-Mail-Antwortentwurfs --- 
export interface RefineReplyPayload {
  custom_prompt: string;
  current_subject: string;
  current_body: string;
}

export interface RefineReplyResponse {
  refined_subject: string;
  refined_body: string;
}

export const refineEmailReply = async (emailId: number, payload: RefineReplyPayload): Promise<RefineReplyResponse> => {
  console.log(`[api] Requesting refinement for email ${emailId} with data:`, payload);
  const url = `/emails/${emailId}/refine-reply/`;
  try {
    const response = await apiClient.post<RefineReplyResponse>(url, payload);
    console.log(`[api] Refinement for email ${emailId} successful:`, response.data);
    return response.data;
  } catch (error) {
    console.error(`[api] Error requesting refinement for email ${emailId}:`, error);
    // Optional: Detailliertere Fehlerbehandlung basierend auf dem error-Objekt
    throw error; // Fehler weiterwerfen, damit der aufrufende Code ihn behandeln kann
  }
}; 

// Interface und Funktionen für FreelanceProviderCredential
export interface FreelanceProviderCredential {
  id: number;
  username: string;
  link_1: string;
  link_2: string;
  link_3: string;
  created_at: string;
  updated_at: string;
}

export interface FreelanceProviderCredentialInput {
  username: string;
  password: string; // Nur beim Erstellen/Aktualisieren
  link_1: string;
  link_2: string;
  link_3: string;
}

export interface FreelanceValidationResponse {
  success: boolean;
  detail: string;
}

// FreelanceProviderCredential API Service
export const freelanceCredentials = {
  // GET /api/v1/freelance/credentials/ (mapped to list in ViewSet, returns own credentials if any)
  get: async (): Promise<FreelanceProviderCredential | null> => {
    try {
      const response = await apiClient.get<FreelanceProviderCredential>('/freelance/credentials/');
      return response.data;
    } catch (error: any) {
      if (axios.isAxiosError(error) && error.response && error.response.status === 404) {
        console.info('[api.ts] Keine Freelance-Provider-Credentials gefunden.');
        return null; // Explizit null zurückgeben, wenn keine Credentials vorhanden sind
      }
      console.error('[api.ts] Fehler beim Abrufen der Freelance-Provider-Credentials:', error);
      throw error;
    }
  },
  // POST /api/v1/freelance/credentials/
  create: async (data: FreelanceProviderCredentialInput): Promise<FreelanceProviderCredential> => {
    console.log('[api.ts] Erstelle Freelance-Provider-Credentials mit Daten:', data);
    try {
      const response = await apiClient.post<FreelanceProviderCredential>('/freelance/credentials/', data);
      console.log('[api.ts] Antwort vom Erstellen der Freelance-Provider-Credentials:', response.data);
      return response.data;
    } catch (error) {
      console.error('[api.ts] Fehler beim Erstellen der Freelance-Provider-Credentials:', error);
      throw error;
    }
  },
  // PUT /api/v1/freelance/credentials/me/  <- URL geändert
  update: async (data: Partial<FreelanceProviderCredentialInput>): Promise<FreelanceProviderCredential> => {
    console.log('[api.ts] Aktualisiere Freelance-Provider-Credentials mit Daten:', data);
    try {
      // Die ID wird nicht mehr in der URL benötigt, da /me/ sich auf den request.user bezieht
      const response = await apiClient.put<FreelanceProviderCredential>('/freelance/credentials/me/', data);
      console.log('[api.ts] Antwort vom Aktualisieren der Freelance-Provider-Credentials:', response.data);
      return response.data;
    } catch (error) {
      console.error('[api.ts] Fehler beim Aktualisieren der Freelance-Provider-Credentials:', error);
      throw error;
    }
  },
  // DELETE /api/v1/freelance/credentials/me/ <- URL geändert
  delete: async (): Promise<void> => {
    console.log('[api.ts] Lösche Freelance-Provider-Credentials');
    try {
      // Die ID wird nicht mehr in der URL benötigt
      await apiClient.delete('/freelance/credentials/me/');
      console.log('[api.ts] Freelance-Provider-Credentials erfolgreich gelöscht.');
    } catch (error) {
      console.error('[api.ts] Fehler beim Löschen der Freelance-Provider-Credentials:', error);
      throw error;
    }
  },
  // POST /api/v1/freelance/credentials/validate/
  validate: async (data: FreelanceProviderCredentialInput): Promise<FreelanceValidationResponse> => {
    try {
      console.log('[api.ts] Validiere Freelance-Provider-Credentials');
      const response = await apiClient.post<FreelanceValidationResponse>('/freelance/credentials/validate/', data);
      console.log('[api.ts] Freelance-Provider-Credentials-Validierung abgeschlossen:', response.data.success);
      return response.data;
    } catch (error) {
      console.error('Fehler bei der Validierung der Freelance-Provider-Credentials:', error);
      throw error;
    }
  },
  // Prüfe, ob Credentials existieren
  exists: async (): Promise<boolean> => {
    try {
      console.log('[api.ts] Prüfe, ob Freelance-Provider-Credentials existieren');
      await apiClient.get('/freelance/credentials/');
      console.log('[api.ts] Freelance-Provider-Credentials existieren');
      return true;
    } catch (error: any) {
      if (error.response && error.response.status === 404) {
        console.log('[api.ts] Keine Freelance-Provider-Credentials gefunden');
        return false;
      }
      console.error('Fehler bei der Prüfung auf Freelance-Provider-Credentials:', error);
      throw error;
    }
  }
}; 