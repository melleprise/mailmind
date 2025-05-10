import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  IconButton,
  TextField,
  Paper,
  CircularProgress,
  Alert,
  Tooltip,
  Chip,
  Slide,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Archive as ArchiveIcon,
  // Check as CheckIcon, // Not used currently
  // Edit as EditIcon, // Not used currently
  // Send as SendIcon, // Not used currently
  Reply as ReplyIcon,
  ForwardToInbox as ForwardToInboxIcon,
  Link as LinkIcon,
  Report as ReportIcon,
  MoveToInbox as MoveToInboxIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
// --- Removed API imports, now in hook ---
// import { AISuggestion, correctSuggestionField, isCorrectedSnippetResponse, refineSuggestion } from '../services/api';
// --- Import moved types ---
import { AISuggestionsProps, CorrectingState } from './types';
// --- Import context menu and dialog ---
import { AISuggestionContextMenu } from '../AISuggestionContextMenu';
import { PromptRefineDialog } from '../PromptRefineDialog';
// --- Import hook and utils ---
import { truncateAndClean } from './utils';
import { AISuggestion } from '../../services/api';
import { useEmailStore } from '../../stores/emailStore';
// --- Import der neuen View-Komponenten ---
import { ActionButtonsView } from './ActionButtonsView';
import { ReplyView } from './ReplyView';

export const AISuggestions: React.FC<AISuggestionsProps> = ({
  selectedEmailId,
  currentEmailDetail,
  loading,
  error,
  onArchive,
  onRefreshSuggestions,
  onExpandRequest,
  isExpanded,
  onUpdateSuggestion,
}) => {
  // --- Store-Zugriff bleibt hier für die Hauptlogik ---
  const emailActions = useEmailStore((state) => state.emailActions);
  const setEmailAction = useEmailStore((state) => state.setEmailAction);

  // Immer ReplyView anzeigen, solange eine Email ausgewählt ist
  const currentAction = selectedEmailId ? (emailActions[selectedEmailId] === undefined ? null : emailActions[selectedEmailId]) : null;

  const handleInternalRefresh = () => {
    if (selectedEmailId) {
      console.log("[AISuggestions Comp] Internal refresh triggered.");
      onRefreshSuggestions(selectedEmailId);
      // setEmailAction(selectedEmailId, null); // ENTFERNT: ReplyView bleibt offen
    }
  };

  const handleInternalArchive = () => {
    if (selectedEmailId) {
      console.log("[AISuggestions Comp] Internal archive triggered.");
      onArchive(selectedEmailId);
      setEmailAction(selectedEmailId, null);
    }
  };

  // VEREINFACHT: Klick auf Container expandiert IMMER, wenn nicht bereits expanded
  const handleClickContainer = (event: React.MouseEvent<HTMLElement>) => {
    // DEBUG LOG
    console.log(`[AISuggestions handleClickContainer] Click detected. isExpanded: ${isExpanded}`);
    if (!isExpanded) {
      console.log("[AISuggestions Comp] Clicked container while panel closed, requesting expand.");
       onExpandRequest();
      event.stopPropagation(); // Verhindere weitere Klick-Handler
    } // Kein else nötig - wenn expanded, soll der Klick normal durchgehen
  };

  return (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
    }}>
      {/* Main Content Area */}
      <Box sx={{
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        pt: 1,
        pb: 1,
        px: 1,
        gap: 1,
      }}
      // Attach onClick only to the main content area
      onClick={handleClickContainer} 
      >
        {/* Loading State entfernt, da Spinner nur noch in ReplyView */}
        {error ? (
          <Alert severity="error" sx={{ m: 1 }}>{error}</Alert>
        ) : !selectedEmailId ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', p: 2 }}>
            <Typography variant="body1" sx={{ color: 'grey.600', textAlign: 'center' }}>
              Select an email to view actions and AI suggestions
            </Typography>
          </Box>
        ) : (
          // --- NEUE ANIMATIONS-LOGIK --- 
          <Box sx={{ flexGrow: 1, position: 'relative', overflow: 'hidden' }}>
            {/* Action Buttons View - Slides out to left */}
            <Slide direction="right" in={currentAction === null} mountOnEnter unmountOnExit>
              {/* Position absolute ensures it stays in the flow during animation */}
              <Box sx={{ position: 'absolute', width: '100%', height: '100%' }}>
                <ActionButtonsView
                  selectedEmailId={selectedEmailId}
                  setEmailAction={setEmailAction}
                  isExpanded={isExpanded}
                  onExpandRequest={onExpandRequest}
                  />
              </Box>
            </Slide>

            {/* Reply View - Slides in from right */}
            <Slide direction="left" in={currentAction === 'reply'} mountOnEnter unmountOnExit>
              <Box sx={{ position: 'absolute', width: '100%', height: '100%' }}>
                <ReplyView
                  selectedEmailId={selectedEmailId}
                  currentEmailDetail={currentEmailDetail}
                  isExpanded={isExpanded}
                  onExpandRequest={onExpandRequest}
                  onUpdateSuggestion={onUpdateSuggestion}
                  loading={loading}
                  originalSender={currentEmailDetail?.from_address}
                  suggestions={currentEmailDetail?.suggestions || []}
                  setEmailAction={setEmailAction}
                  handleInternalRefresh={handleInternalRefresh}
                />
              </Box>
            </Slide>
          </Box>
          // --- ENDE NEUE ANIMATIONS-LOGIK ---
        )}
      </Box>
    </Box>
  );
};

// --- Ensure the component is exported correctly if the filename changed ---
// export default AISuggestions; // Use named export as before 