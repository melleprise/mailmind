import { AISuggestion } from '../../services/api';
import { EmailDetailData } from '../../services/api';

// Define the type for the correcting state
export interface CorrectingState {
  [suggestionId: string]: {
    subject?: boolean;
    body?: boolean;
    both?: boolean; // Keep track of 'both' state if needed for initial setting
  };
}

// Type received from Dashboard
export interface AISuggestionsProps {
  selectedEmailId: number | null;
  // Pass the whole detail object or relevant parts
  currentEmailDetail: EmailDetailData | null;
  loading: boolean; // Loading state for email details/suggestions
  error: string | null; // Error state
  onArchive: (emailId: number) => void;
  onRefreshSuggestions: (emailId: number) => void;
  onExpandRequest: () => void;
  isExpanded: boolean;
  onUpdateSuggestion: (id: string, data: Partial<Pick<AISuggestion, 'content' | 'suggested_subject'>>) => Promise<void>;
} 