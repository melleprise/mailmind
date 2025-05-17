import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { api, getEmailById } from '../services/api'; // Assuming your API functions are centralized

// Re-define types here or import from a types file
interface AISuggestion {
  id: string;
  type: string;
  title: string;
  content: string;
  status: string;
  created_at: string;
  processing_time: number;
}

interface EmailSummary {
  id: number;
  subject: string;
  from_address: string;
  from_name?: string;
  received_at?: string;
  sent_at?: string;
  is_read: boolean;
  has_attachments: boolean;
  ai_processed: boolean;
  // Add other summary fields shown in the list
}

interface EmailDetail extends EmailSummary {
  body_html?: string;
  body_text?: string;
  attachments?: any[]; // Define attachment type properly later
  to_contacts?: { id: number; name: string; email: string; }[];
  cc_contacts?: { id: number; name: string; email: string; }[];
  suggestions?: AISuggestion[];
  ai_processed_at?: string;
}

// NEU: Interface für Entwürfe
interface DraftContent {
  subject: string;
  body: string;
}

interface EmailState {
  emails: EmailSummary[];
  selectedEmail: EmailDetail | null;
  loading: boolean;
  error: string | null;
  fetchEmails: (folderName?: string, limit?: number, offset?: number) => Promise<void>;
  fetchEmail: (id: number) => Promise<void>;
  setSelectedEmail: (email: EmailDetail | null) => void;
  clearSelectedEmail: () => void;
  setEmail: (email: EmailDetail) => void; // Might be used to update state after action
  fetchCounter: number;
  incrementFetchCounter: () => void;
  emailActions: { [emailId: number]: string | null };
  drafts: { [emailId: number]: DraftContent }; // NEU: State für Entwürfe
  setEmailAction: (emailId: number, action: string | null) => void;
  clearAllEmailActions: () => void;
  // NEU: Aktionen für Entwürfe
  setDraftSubject: (emailId: number, subject: string) => void;
  setDraftBody: (emailId: number, body: string) => void;
  clearDraft: (emailId: number) => void;
  removeEmail: (id: number) => void;
}

const LOCAL_STORAGE_KEY = 'mailmind_email_actions_and_drafts'; // Key angepasst

export const useEmailStore = create<EmailState>()(
  devtools(
    persist(
      (set, get) => ({
        emails: [],
        selectedEmail: null,
        loading: false,
        error: null,
        fetchCounter: 0,
        emailActions: {}, 
        drafts: {}, // Initialer leerer State für Entwürfe

        fetchEmails: async (folderName = 'INBOX', limit = 20, offset = 0) => {
          set({ loading: true, error: null });
          try {
            // Assume api.getEmails exists and fetches a list
            const response = await api.get(`/emails/?folder_name=${folderName}&limit=${limit}&offset=${offset}`);
            // Assuming the API returns { results: EmailSummary[], count: number }
            set({ emails: response.data.results, loading: false });
          } catch (error: any) {
            console.error("Failed to fetch emails:", error);
            set({ error: 'Failed to load emails.', loading: false });
          }
        },

        fetchEmail: async (id: number) => {
          const currentState = get();
          // 1. Check if the requested email is ALREADY selected and loaded.
          if (currentState.selectedEmail?.id === id) {
            console.log(`[emailStore] Email ${id} is already selected. No fetch needed.`);
            // Ensure loading is false if we bail out here
            if (currentState.loading) set({ loading: false });
            return;
          }
          
          // 2. Check if we are ALREADY loading something else (prevent concurrent fetches)
          //    This might be too restrictive depending on UX, but let's try it.
          if (currentState.loading) {
               console.log(`[emailStore] Skipping fetch for ${id} because another fetch is in progress.`);
               return;
          }

          // 3. If not already selected and not loading, proceed to fetch.
          console.log(`[emailStore] Fetching new email with ID: ${id}`);
          set({ loading: true, error: null, selectedEmail: null }); // Clear old email, set loading
          try {
            const emailData = await getEmailById(id);
            console.log(`[emailStore] Fetched email data for ID ${id}:`, JSON.stringify(emailData.suggestions)); // Log suggestions specifically
            console.log(`[emailStore] AI Processed flag: ${emailData.ai_processed}`);
            
            // Set the fetched data
            set({ selectedEmail: emailData, loading: false }); 
            console.log(`[emailStore] State updated for ID ${id}.`);
            get().incrementFetchCounter();
          } catch (error: any) {
            console.error(`[emailStore] Error fetching email ${id}:`, error);
            // Set error, clear loading, keep selectedEmail null (as fetch failed)
            set({ error: `Failed to fetch email ${id}`, loading: false, selectedEmail: null });
          }
        },

        setSelectedEmail: (email) => {
          set({ selectedEmail: email });
        },

        clearSelectedEmail: () => {
          set({ selectedEmail: null });
        },
        
        setEmail: (email) => { 
          // Simple implementation: Update selected email directly
          // More complex: Find and update in the emails list as well
          if (get().selectedEmail?.id === email.id) {
              set({ selectedEmail: email });
          }
          // Update list (optional, might cause re-renders)
          // set(state => ({ emails: state.emails.map(e => e.id === email.id ? { ...e, ...email } : e) }));
        },
        
        incrementFetchCounter: () => set((state) => ({ fetchCounter: state.fetchCounter + 1 })),

        setEmailAction: (emailId, action) => {
          console.log(`[emailStore] Setting action for email ${emailId} to: ${action}`);
          // Wenn die Aktion entfernt wird (ReplyView geschlossen), lösche auch den Entwurf
          if (action === null) {
            get().clearDraft(emailId); 
          }
          set((state) => ({
            emailActions: {
              ...state.emailActions,
              [emailId]: action,
            },
          }));
        },

        clearAllEmailActions: () => {
           console.log('[emailStore] Clearing all email actions and drafts.');
           set({ emailActions: {}, drafts: {} }); // Auch Entwürfe leeren
        },

        // --- NEUE Draft Aktionen ---
        setDraftSubject: (emailId, subject) => {
            set((state) => ({
                drafts: {
                    ...state.drafts,
                    [emailId]: {
                        ...(state.drafts[emailId] || { subject: '', body: '' }), // Existing body or default
                        subject: subject,
                    },
                },
            }));
        },

        setDraftBody: (emailId, body) => {
            set((state) => ({
                drafts: {
                    ...state.drafts,
                    [emailId]: {
                        ...(state.drafts[emailId] || { subject: '', body: '' }), // Existing subject or default
                        body: body,
                    },
                },
            }));
        },

        clearDraft: (emailId) => {
            set((state) => {
                const newDrafts = { ...state.drafts };
                delete newDrafts[emailId];
                return { drafts: newDrafts };
            });
        },
        // --- Ende Draft Aktionen ---

        /**
         * Entfernt eine E-Mail sofort aus der Liste (z.B. nach Sofort-Löschen im UI).
         */
        removeEmail: (id: number) => {
          set((state) => ({ emails: state.emails.filter(e => e.id !== id) }));
        },

      }),
      {
        name: LOCAL_STORAGE_KEY, // Aktualisierter Key
        // Jetzt emailActions UND drafts persistieren
        partialize: (state) => ({ 
            emailActions: state.emailActions, 
            drafts: state.drafts 
        }), 
      }
    ),
    { name: 'email-store' }
  )
); 