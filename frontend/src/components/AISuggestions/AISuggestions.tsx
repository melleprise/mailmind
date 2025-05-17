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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
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
import { AISuggestion, moveEmailToTrash } from '../../services/api';
import { useEmailStore } from '../../stores/emailStore';
// --- Import der neuen View-Komponenten ---
import { ActionButtonsView } from './ActionButtonsView';
import { ReplyMailView } from './ReplyMailView';

export interface AISuggestionsProps {
  selectedEmailId: number | null;
  currentEmailDetail: any;
  loading: boolean;
  error: string | null;
  onArchive: (id: number) => void;
  onRefreshSuggestions: (id: number) => void;
  onExpandRequest: () => void;
  isExpanded: boolean;
  onUpdateSuggestion: (id: number, data: any) => void;
  onDeleteEmail?: (id: number) => void;
}

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
  onDeleteEmail,
}) => {
  // --- Store-Zugriff bleibt hier für die Hauptlogik ---
  const emailActions = useEmailStore((state) => state.emailActions);
  const setEmailAction = useEmailStore((state) => state.setEmailAction);
  const removeEmail = useEmailStore.getState().removeEmail;

  // Immer ReplyMailView anzeigen, solange eine Email ausgewählt ist
  const currentAction = selectedEmailId ? (emailActions[selectedEmailId] === undefined ? null : emailActions[selectedEmailId]) : null;

  const handleInternalRefresh = () => {
    if (selectedEmailId) {
      console.log("[AISuggestions Comp] Internal refresh triggered.");
      onRefreshSuggestions(selectedEmailId);
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
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  const handleDelete = (emailId: number) => {
    console.log('[Delete] Dialog öffnen für EmailId:', emailId);
    setPendingDeleteId(emailId);
    setDeleteDialogOpen(true);
    // Kein Panel-Toggle oder handleClickContainer!
  };

  const handleConfirmDelete = () => {
    console.log('[Delete] Löschen bestätigen für EmailId:', pendingDeleteId);
    if (!pendingDeleteId) return;
    // Dialog sofort schließen und E-Mail aus UI entfernen
    setDeleteDialogOpen(false);
    setEmailAction(pendingDeleteId, null);
    // E-Mail sofort aus der Liste entfernen
    if (pendingDeleteId) {
      removeEmail(pendingDeleteId);
      if (onDeleteEmail) onDeleteEmail(pendingDeleteId);
    }
    const deleteId = pendingDeleteId;
    setPendingDeleteId(null);
    // API-Call asynchron im Hintergrund, UI wartet nicht
    setTimeout(() => {
      moveEmailToTrash(deleteId).catch((error) => {
        // Fehler nur loggen
        console.error('[Delete] Fehler beim Löschen im Hintergrund:', error);
      });
    }, 0);
  };

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false);
    setPendingDeleteId(null);
  };

  // Tastatur-Handler für Dialog
  const handleDialogKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleConfirmDelete();
    } else if (e.key === 'Backspace') {
      e.preventDefault();
      handleCancelDelete();
    }
  };

  const handleClickContainer = (event: React.MouseEvent<HTMLElement>) => {
    if (deleteDialogOpen) return; // Blockiere Toggle bei offenem Dialog
    console.log(`[AISuggestions handleClickContainer] Click detected. isExpanded: ${isExpanded}`);
    if (!isExpanded) {
      onExpandRequest();
      event.stopPropagation();
    }
  };

  return (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
      position: 'relative', // Für Overlay
    }}>
      {/* Overlay blockiert alle Klicks, solange Dialog offen */}
      {deleteDialogOpen && (
        <Box sx={{
          position: 'absolute',
          zIndex: 2000,
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          bgcolor: 'rgba(0,0,0,0.01)', // fast unsichtbar, blockiert aber alle Events
          pointerEvents: 'none', // Blockiert keine Klicks auf den Dialog selbst
        }} />
      )}
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
        {/* Loading State entfernt, da Spinner nur noch in ReplyMailView */}
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
                  onExpandRequest={deleteDialogOpen ? () => {} : onExpandRequest}
                  onDelete={handleDelete}
                  deleteDialogOpen={deleteDialogOpen}
                />
              </Box>
            </Slide>

            {/* Reply View - Slides in from right */}
            <Slide direction="left" in={currentAction === 'reply'} mountOnEnter unmountOnExit>
              <Box sx={{ position: 'absolute', width: '100%', height: '100%' }}>
                <ReplyMailView
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
      <Dialog open={deleteDialogOpen} onClose={handleCancelDelete} maxWidth="xs" fullWidth onKeyDown={handleDialogKeyDown}>
        <DialogTitle sx={{ textAlign: 'center', fontWeight: 600, fontSize: '1.3rem' }}>E-Mail löschen</DialogTitle>
        <DialogContent sx={{ py: 4, px: 3, textAlign: 'center' }}>
          <Typography sx={{ fontSize: '1.1rem', mb: 1.5 }}>
            Möchtest du diese E-Mail wirklich in den Papierkorb verschieben?
          </Typography>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'center', gap: 2, pb: 3 }}>
          <Button onClick={handleCancelDelete} color="primary" size="large" variant="outlined">Abbrechen</Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained" size="large" autoFocus>Löschen</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

// --- Ensure the component is exported correctly if the filename changed ---
// export default AISuggestions; // Use named export as before 