import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  Paper,
  CircularProgress,
  Alert,
  Tooltip,
  Chip,
  Slide,
  IconButton,
  FormControl,
  Select,
  MenuItem,
} from '@mui/material';
import { Refresh as RefreshIcon, ArrowBack as ArrowBackIcon, Add as AddIcon } from '@mui/icons-material';
import { AISuggestion, EmailDetailData } from '../../services/api';
import { useAISuggestionHandlers } from './useAISuggestionHandlers'; // Importiere den Hook
import { CorrectingState } from './types'; // Importiere Typen
import { useEmailStore } from '../../stores/emailStore'; // Import the store

// Definiere die Props, die diese Komponente benötigt
interface ReplyMailViewProps {
  selectedEmailId: number | null;
  suggestions: AISuggestion[];
  originalSender: string | undefined;
  currentEmailDetail: EmailDetailData | null;
  isExpanded: boolean;
  onExpandRequest: () => void;
  onUpdateSuggestion: (id: string, data: Partial<Pick<AISuggestion, 'content' | 'suggested_subject'>>) => Promise<void>;
  // Optional: Lade-/Fehlerzustände, falls relevant für UI-Elemente hier drin
  loading?: boolean; // Haupt-Ladezustand für Suggestion-Generierung
  // error?: string | null; // Fehler wird vermutlich eher im Parent behandelt
  setEmailAction: (emailId: number, action: string | null) => void;
  handleInternalRefresh: () => void;
}

export const ReplyMailView: React.FC<ReplyMailViewProps> = ({
  selectedEmailId,
  suggestions,
  originalSender,
  currentEmailDetail,
  isExpanded,
  onExpandRequest,
  onUpdateSuggestion,
  loading,
  setEmailAction,
  handleInternalRefresh,
}) => {

  // --- Get draft state and actions from the store ---
  const draft = useEmailStore((state) => 
    selectedEmailId ? (state.drafts[selectedEmailId] || { subject: '', body: '' }) : { subject: '', body: '' }
  );
  const setDraftSubject = useEmailStore((state) => state.setDraftSubject);
  const setDraftBody = useEmailStore((state) => state.setDraftBody);

  // --- Local UI states (remain local) ---
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState<number | null>(null);
  const [toRecipients, setToRecipients] = useState<string[]>([]);
  const [ccRecipients, setCcRecipients] = useState<string[]>([]);
  const [bccRecipients, setBccRecipients] = useState<string[]>([]);
  const recipientCounter = useRef(1);
  const [fromEmail, setFromEmail] = useState<string>('melleprise@gmail.com'); 
  // Local focus states - these should NOT be global
  const [isSubjectFocused, setIsSubjectFocused] = useState(false);
  const [isBodyFocused, setIsBodyFocused] = useState(false);

  // Refs remain local
  const subjectInputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  const bodyTextareaRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  // --- Lokaler State für Editorfelder ---
  const [localSubject, setLocalSubject] = useState(draft.subject);
  const [localBody, setLocalBody] = useState(draft.body);

  // Sync lokalen State bei Suggestion-Wechsel, Undo, Redo
  useEffect(() => {
    if (!selectedEmailId) return;
    setLocalSubject(draft.subject);
    setLocalBody(draft.body);
  }, [selectedEmailId, draft.subject, draft.body]);

  // Handler für Subject
  const handleLocalSubjectChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setLocalSubject(event.target.value);
  };
  const handleLocalSubjectBlur = () => {
    handleSubjectChange({ target: { value: localSubject } } as any);
  };

  // Handler für Body
  const handleLocalBodyChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setLocalBody(event.target.value);
  };
  const handleLocalBodyBlur = () => {
    handleEditChange({ target: { value: localBody } } as any);
  };

  // Effect to initialize/reset recipients when originalSender changes
  useEffect(() => {
    if (originalSender) {
        // Reset recipients when the original sender changes
        setToRecipients([originalSender]);
        setCcRecipients([]); // Reset CC
        setBccRecipients([]); // Reset BCC
        recipientCounter.current = 1; // Reset dummy counter
    } else {
        // Clear recipients if no original sender
         setToRecipients([]);
         setCcRecipients([]);
         setBccRecipients([]);
         recipientCounter.current = 1;
    }
    // Dependency: originalSender. This effect runs when the selected email context changes.
  }, [originalSender]);

  // Handler zum Hinzufügen von Empfängern
  const handleAddRecipient = (type: 'to' | 'cc' | 'bcc') => {
    const newRecipient = `dummy${recipientCounter.current++}@example.com`;
    if (type === 'to') {
      setToRecipients([...toRecipients, newRecipient]);
    } else if (type === 'cc') {
      setCcRecipients([...ccRecipients, newRecipient]);
    } else {
      setBccRecipients([...bccRecipients, newRecipient]);
    }
  };

  // Handler zum Löschen von Empfängern
  const handleDeleteRecipient = (type: 'to' | 'cc' | 'bcc', emailToDelete: string) => {
    if (type === 'to') {
      setToRecipients(toRecipients.filter(email => email !== emailToDelete));
    } else if (type === 'cc') {
      setCcRecipients(ccRecipients.filter(email => email !== emailToDelete));
    } else {
      setBccRecipients(bccRecipients.filter(email => email !== emailToDelete));
    }
  };

  // --- Focus handlers (remain local) ---
  const handleSubjectFocus = () => setIsSubjectFocused(true);
  const handleSubjectBlur = () => setIsSubjectFocused(false);
  const handleBodyFocus = () => setIsBodyFocused(true);
  const handleBodyBlur = () => {
    setIsBodyFocused(false);
    // Optional: Could trigger a save/update here if needed, but persist handles it
  };

  // --- Callback functions for the hook to update draft state (remain) ---
  const handleDraftSubjectChange = useCallback((newSubject: string) => {
      if (selectedEmailId) {
        setDraftSubject(selectedEmailId, newSubject);
      }
  }, [selectedEmailId, setDraftSubject]);

  const handleDraftBodyChange = useCallback((newBody: string) => {
      if (selectedEmailId) {
        setDraftBody(selectedEmailId, newBody);
      }
  }, [selectedEmailId, setDraftBody]);

  // --- Hook Usage (Adjusted Call) ---
  const {
      correctingStates,
      correctionError,
      isRefining,
      handleCorrectClick,
      handleRefineClick,
      customPrompt,
      setCustomPrompt,
      refineError,
      setRefineError,
      handleSubjectChange,
      handleEditChange,
  } = useAISuggestionHandlers(
      suggestions,
      selectedEmailId,
      selectedSuggestionIndex,
      draft.subject,
      draft.body,
      handleDraftSubjectChange,
      handleDraftBodyChange,
      isExpanded,
      onExpandRequest,
      onUpdateSuggestion,
      subjectInputRef,
      bodyTextareaRef
  );

  // State für Alert-Anzeige
  const [showCorrectionError, setShowCorrectionError] = useState(true);
  useEffect(() => {
    if (correctionError) {
        setShowCorrectionError(true);
    }
  }, [correctionError]);

  // --- Hybrid-Logik für Suggestion-Auswahl (localStorage + Backend) ---
  useEffect(() => {
    if (!selectedEmailId) return;
    const localKey = `selectedSuggestionIndex_${selectedEmailId}`;
    let didSet = false;
    // 1. localStorage lesen
    const localIdx = localStorage.getItem(localKey);
    if (localIdx !== null && localIdx !== '') {
      const idx = Number(localIdx);
      setSelectedSuggestionIndex(idx);
      if (suggestions[idx]) {
        setDraftSubject(selectedEmailId, suggestions[idx].title || draft.subject);
        setDraftBody(selectedEmailId, suggestions[idx].content);
      }
      didSet = true;
    }
    // 2. Backend-Draft laden
    fetch(`/api/v1/drafts/by_email/?email_id=${selectedEmailId}`, {
      headers: { 'Authorization': `Token ${localStorage.getItem('token')}` }
    })
      .then(r => {
        if (r.status === 404) {
          // Draft existiert nicht: Store leeren und Draft im Backend anlegen
          setDraftSubject(selectedEmailId, '');
          setDraftBody(selectedEmailId, '');
          fetch(`/api/v1/drafts/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Token ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ email: selectedEmailId, subject: '', body: '' })
          });
          return null;
        }
        return r.ok ? r.json() : null;
      })
      .then(data => {
        if (data) {
          // subject/body aus Backend-Draft nur übernehmen, wenn Store leer ist
          if ((draft.subject === '' || draft.subject === undefined) && data.subject) {
            setDraftSubject(selectedEmailId, data.subject);
          }
          if ((draft.body === '' || draft.body === undefined) && data.body) {
            setDraftBody(selectedEmailId, data.body);
          }
        }
        if (data && typeof data.selected_suggestion_index === 'number') {
          setSelectedSuggestionIndex(data.selected_suggestion_index);
          localStorage.setItem(localKey, String(data.selected_suggestion_index));
          if (suggestions[data.selected_suggestion_index]) {
            setDraftSubject(selectedEmailId, suggestions[data.selected_suggestion_index].title || draft.subject);
            setDraftBody(selectedEmailId, suggestions[data.selected_suggestion_index].content);
          }
          didSet = true;
        }
        // Falls weder localStorage noch Backend einen Index liefern, auf null lassen
      });
  }, [selectedEmailId, suggestions]);

  // selectedSuggestionIndex immer auf 0 setzen, wenn Suggestions existieren und noch keine Auswahl (und keine Hybrid-Initialisierung läuft)
  useEffect(() => {
    if (
      suggestions.length > 0 &&
      selectedSuggestionIndex === null &&
      (draft.subject === '' || draft.body === '' || draft.subject === undefined || draft.body === undefined)
    ) {
      setSelectedSuggestionIndex(0);
      if (selectedEmailId && suggestions[0]) {
        setDraftSubject(selectedEmailId, suggestions[0].title || '');
        setDraftBody(selectedEmailId, suggestions[0].content);
      }
    }
  }, [suggestions, selectedSuggestionIndex, selectedEmailId, setDraftSubject, setDraftBody, draft.subject, draft.body]);

  const handleLocalSelectSuggestion = (index: number) => {
    if (selectedEmailId === null) return;
    const localKey = `selectedSuggestionIndex_${selectedEmailId}`;
    if (index === selectedSuggestionIndex) {
      setSelectedSuggestionIndex(null);
      localStorage.setItem(localKey, '');
      // Backend: Draft PATCH
      fetch(`/api/v1/drafts/by_email/?email_id=${selectedEmailId}`, {
        headers: { 'Authorization': `Token ${localStorage.getItem('token')}` }
      })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data && data.id) {
            fetch(`/api/v1/drafts/${data.id}/`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${localStorage.getItem('token')}`
              },
              body: JSON.stringify({ selected_suggestion_index: null })
            });
          }
        });
    } else {
      setSelectedSuggestionIndex(index);
      localStorage.setItem(localKey, String(index));
      if (suggestions[index]) {
        setDraftSubject(selectedEmailId, suggestions[index].title || draft.subject);
        setDraftBody(selectedEmailId, suggestions[index].content);
      }
      // Backend: Draft PATCH
      fetch(`/api/v1/drafts/by_email/?email_id=${selectedEmailId}`, {
        headers: { 'Authorization': `Token ${localStorage.getItem('token')}` }
      })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data && data.id) {
            fetch(`/api/v1/drafts/${data.id}/`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${localStorage.getItem('token')}`
              },
              body: JSON.stringify({ selected_suggestion_index: index })
            });
          } else {
            // Draft existiert nicht: anlegen
            fetch(`/api/v1/drafts/`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${localStorage.getItem('token')}`
              },
              body: JSON.stringify({ email: selectedEmailId, selected_suggestion_index: index })
            });
          }
        });
    }
  };

  // Calculate button disabled state before return
  const buttonDisabled_noEmail = !selectedEmailId;
  const buttonDisabled_isRefining = isRefining;
  const buttonDisabled_promptEmpty = customPrompt.trim() === '';
  const isButtonDisabled = buttonDisabled_noEmail || buttonDisabled_isRefining || buttonDisabled_promptEmpty;
  
  // NEU: Logik für Correct-Button
  const correctButtonDisabled = !selectedEmailId || isRefining || (draft.subject.trim() === '' && draft.body.trim() === '');

  // Log button disabled calculation
  console.log(`[ReplyView Correct Button Check] Disabled: noEmail=${!selectedEmailId}, isRefining=${isRefining}, textEmpty=${(draft.subject.trim() === '' && draft.body.trim() === '')}, final=${correctButtonDisabled}`);

  // Log current state value before rendering
  console.log(`[ReplyView] Rendering. State selectedSuggestionIndex: ${selectedSuggestionIndex}`);

  // Log suggestions length before rendering chips
  console.log(`[ReplyView Chip Render] Suggestions array length: ${suggestions?.length}`);

  // --- Undo-Handler (Backend Undo) ---
  const handleUndo = useCallback(async () => {
    if (!selectedEmailId || !suggestions.length) return;
    const idx = selectedSuggestionIndex !== null ? selectedSuggestionIndex : 0;
    const suggestion = suggestions[idx];
    if (!suggestion) return;
    // Entscheide, ob Subject oder Body rückgängig gemacht werden soll
    let field: 'subject' | 'body' = 'body';
    if (isSubjectFocused) field = 'subject';
    // Sende Undo-Request an Backend
    try {
      const token = localStorage.getItem('token');
      const resp = await fetch(`/api/v1/suggestions/${suggestion.id}/undo-correction/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Token ${token}` } : {})
        },
        body: JSON.stringify({ field }),
      });
      if (resp.ok) {
        const data = await resp.json();
        // Aktualisiere Drafts im Store
        if (field === 'subject') {
          setDraftSubject(selectedEmailId, data.suggested_subject || '');
        } else {
          setDraftBody(selectedEmailId, data.content || '');
        }
        // Optional: UI-Feedback
      } else {
        // Optional: Fehlerbehandlung
        console.warn('Undo fehlgeschlagen', await resp.text());
      }
    } catch (err) {
      console.error('Undo-Request Fehler:', err);
    }
  }, [selectedEmailId, suggestions, selectedSuggestionIndex, isSubjectFocused, setDraftSubject, setDraftBody]);

  // --- Redo-Handler (Backend Redo) ---
  const handleRedo = useCallback(async () => {
    if (!selectedEmailId || !suggestions.length) return;
    const idx = selectedSuggestionIndex !== null ? selectedSuggestionIndex : 0;
    const suggestion = suggestions[idx];
    if (!suggestion) return;
    let field: 'subject' | 'body' = 'body';
    if (isSubjectFocused) field = 'subject';
    try {
      const token = localStorage.getItem('token');
      const resp = await fetch(`/api/v1/suggestions/${suggestion.id}/redo-correction/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Token ${token}` } : {})
        },
        body: JSON.stringify({ field }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (field === 'subject') {
          setDraftSubject(selectedEmailId, data.suggested_subject || '');
        } else {
          setDraftBody(selectedEmailId, data.content || '');
        }
      } else {
        console.warn('Redo fehlgeschlagen', await resp.text());
      }
    } catch (err) {
      console.error('Redo-Request Fehler:', err);
    }
  }, [selectedEmailId, suggestions, selectedSuggestionIndex, isSubjectFocused, setDraftSubject, setDraftBody]);

  // --- Global Keydown-Handler für Undo/Redo ---
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') {
        if (e.shiftKey) {
          e.preventDefault();
          handleRedo();
        } else {
          e.preventDefault();
          handleUndo();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleUndo, handleRedo]);

  // Nach einem Refresh: Wähle immer den ersten Vorschlag aus und setze Subject/Body
  useEffect(() => {
    if (!loading && suggestions.length > 0) {
      setSelectedSuggestionIndex(0);
      const suggestion = suggestions[0];
      if (selectedEmailId && suggestion) {
        setDraftSubject(selectedEmailId, suggestion.title || '');
        setDraftBody(selectedEmailId, suggestion.content || '');
      }
    }
  }, [loading, suggestions, selectedEmailId, setDraftSubject, setDraftBody]);

  // JSX aus AISuggestions.tsx extrahiert
  return (
    // Root Box der Komponente
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' /* Für absolutes Pos. */ }}>

      {/* --- Header hier eingefügt --- */}
      <Box sx={{ 
            pt: 0, // Padding oben entfernt
            pb: 0.25, // Weiter reduziertes Padding unten
            borderBottom: 1, // Fügt eine untere Linie hinzu
            borderColor: 'divider', // Verwendet die Theme-Trennfarbe
            display: 'flex', 
            justifyContent: 'space-between', // Sicherstellen, dass es space-between ist
            alignItems: 'center', 
          }}
       >
        {/* Linke Box: Back Button + Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, pl: 0 }}>
          {/* Back Button - Ruft jetzt setEmailAction aus Props auf */}
          <IconButton size="small" onClick={() => { if (selectedEmailId) setEmailAction(selectedEmailId, null); }} >
              <ArrowBackIcon fontSize="small" />
           </IconButton>
           <Typography variant="overline" sx={{ color: 'grey.500' }}>Antworten</Typography>
        </Box>

        {/* Rechte Box: From Label + Dropdown (nur sichtbar wenn isExpanded) */}
        {isExpanded && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
               <Typography variant="body1" sx={{ color: 'text.secondary', fontSize: '0.9rem', minWidth: '35px', textAlign: 'right' }}>
                  From:
                </Typography>
                <FormControl 
                  variant="standard" 
                  sx={{ minWidth: 120, maxWidth: 'fit-content' }}
                  onClick={(e) => e.stopPropagation()} 
                >
                  <Select
                    labelId="from-email-select-label-hidden"
                    id="from-email-select"
                    value={fromEmail}
                    onChange={(e) => setFromEmail(e.target.value as string)}
                    disableUnderline
                    sx={{
                      borderRadius: '16px', border: 1, borderColor: 'divider',
                      p: '2px 8px', fontSize: '0.8125rem', color: 'text.primary',
                      bgcolor: 'transparent',
                      '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
                      '& .MuiSelect-select': { paddingRight: '20px !important', paddingTop: '0px', paddingBottom: '0px' },
                      '& .MuiSvgIcon-root': { color: 'text.secondary', right: '2px' },
                      '&.Mui-focused .MuiOutlinedInput-notchedOutline': { border: 'none' },
                      '.MuiOutlinedInput-notchedOutline': { border: 'none' },
                    }}
                    MenuProps={{
                      PaperProps: {
                        sx: { bgcolor: 'background.paper', marginTop: '4px' },
                      },
                    }}
                  >
                    <MenuItem value="melleprise@gmail.com" sx={{ fontSize: '0.8125rem' }}>melleprise@gmail.com</MenuItem>
                    <MenuItem value="melle@vollmotiviert.de" sx={{ fontSize: '0.8125rem' }}>melle@vollmotiviert.de</MenuItem>
                  </Select>
                </FormControl>
            </Box>
        )}
       </Box>
       {/* --- Ende Header --- */}

      {/* Restlicher Inhalt (Editor, Chips, Refine) */}
      <Box sx={{ 
        pt: 1, // Padding oben hinzugefügt für Abstand nach der Linie
        flexGrow: 1, 
        display: 'flex', 
        flexDirection: 'column', 
        gap: 0.5 /* Reduzierter Gap */, 
        overflow: 'hidden' /* p: 1 wieder entfernt */ }}>

        {/* --- Empfänger (Original Sender, Added & Add Buttons) --- */}
        {isExpanded && (
            <Box sx={{ mb: 0.5, display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                {/* Container für alle Empfänger-Chips (nimmt Platz ein) */}
                <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    {/* --- Consolidated To Recipients Row --- */}
                    {toRecipients.length > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Typography variant="body1" sx={{ color: 'text.secondary', fontSize: '0.9rem', width: '25px' }}>
                                To:
                            </Typography>
                            {toRecipients.map(email => (
                                <Chip key={email} label={email} size="small" onDelete={() => handleDeleteRecipient('to', email)} />
                            ))}
                        </Box>
                    )}
                    {/* --- Added Cc Recipients Row --- */}
                    {ccRecipients.length > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Typography variant="body1" sx={{ color: 'text.secondary', fontSize: '0.9rem', width: '25px' }}>Cc:</Typography>
                            {ccRecipients.map(email => (
                                <Chip key={email} label={email} size="small" onDelete={() => handleDeleteRecipient('cc', email)} />
                            ))}
                        </Box>
                    )}
                    {/* --- Added Bcc Recipients Row --- */}
                    {bccRecipients.length > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Typography variant="body1" sx={{ color: 'text.secondary', fontSize: '0.9rem', width: '25px' }}>Bcc:</Typography>
                            {bccRecipients.map(email => (
                                <Chip key={email} label={email} size="small" onDelete={() => handleDeleteRecipient('bcc', email)} />
                            ))}
                        </Box>
                    )}
                </Box>

                {/* Add Buttons Container (bleibt rechts) */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
                    <Tooltip title="Add To Recipient">
                        <Chip icon={<AddIcon />} label="To" size="small" clickable onClick={() => handleAddRecipient('to')} sx={{ '& .MuiChip-icon': { marginLeft: '8px' } }}/>
                    </Tooltip>
                    <Tooltip title="Add Cc Recipient">
                        <Chip icon={<AddIcon />} label="Cc" size="small" clickable onClick={() => handleAddRecipient('cc')} sx={{ '& .MuiChip-icon': { marginLeft: '8px' } }}/>
                    </Tooltip>
                    <Tooltip title="Add Bcc Recipient">
                        <Chip icon={<AddIcon />} label="Bcc" size="small" clickable onClick={() => handleAddRecipient('bcc')} sx={{ '& .MuiChip-icon': { marginLeft: '8px' } }}/>
                    </Tooltip>
                </Box>
            </Box>
        )}

        {/* Editor */}
        <Box
          sx={{
            flexGrow: 3,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            p: 1,
            bgcolor: '#303030',
            position: 'relative',
          }}
        >
          {/* Subject Field - Use draft from store */}
          <TextField
            variant="standard"
            fullWidth
            multiline
            minRows={1}
            value={localSubject}
            inputRef={subjectInputRef}
            onChange={handleLocalSubjectChange}
            onBlur={() => handleSubjectChange({ target: { value: localSubject } } as any)}
            onFocus={handleSubjectFocus}
            placeholder="Betreff"
            sx={{
              mb: 1.5,
              '& .MuiInput-underline:before': { borderBottom: 'none' },
              '& .MuiInput-underline:hover:not(.Mui-disabled):before': { borderBottom: 'none' },
              '& .MuiInput-underline:after': { borderBottom: 'none' },
              // Remove padding from the root element
              '& .MuiInputBase-root': {
                paddingTop: 0,
                paddingBottom: 0,
              },
              '& .MuiInputBase-input': {
                color: 'primary.main',
                fontSize: '1rem',
                fontWeight: '500',
                lineHeight: 1.5,
                padding: 0, // Keep padding 0 for the input itself
                whiteSpace: 'normal',
                height: 'auto',
                overflowWrap: 'break-word',
              }
            }}
            disabled={isRefining || !selectedEmailId} // Disable if no ID or refining
          />

          {/* Body Field */}
          <TextField
            multiline
            fullWidth
            variant="outlined"
            value={localBody}
            inputRef={bodyTextareaRef}
            onChange={handleLocalBodyChange}
            onBlur={() => handleEditChange({ target: { value: localBody } } as any)}
            onFocus={handleBodyFocus}
            placeholder="Nachricht"
            sx={{
              flexGrow: 1,
              height: '100%',
              '& .MuiOutlinedInput-notchedOutline': { border: 'none' },
              '& .MuiInputBase-root': {
                  height: '100%',
                  alignItems: 'flex-start',
                  p: 0,
              },
              '& textarea': {
                  height: '100% !important',
                  overflow: 'auto !important',
                  paddingTop: '0 !important',
              }
            }}
            disabled={isRefining || !selectedEmailId} // Disable if no ID or refining
          />

          {/* --- Loading Overlay for Refine --- */}
          {isRefining && (
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0, // Added for clarity
                bottom: 0, // Added for clarity
                width: '100%',
                height: '100%',
                bgcolor: 'rgba(0, 0, 0, 0.9)', // 90% black overlay
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 2, // Ensure it is above text fields
                borderRadius: 1, // Match parent border radius
                cursor: 'progress', // Indicate loading state
              }}
              onClick={(e) => e.stopPropagation()} // Prevent clicks through
            >
              <CircularProgress color="primary" />
            </Box>
          )}
          {/* --- End Loading Overlay --- */}

          {/* Correct Text Button - Wiederhergestelltes Design und korrigierte Logik*/}
          {selectedEmailId !== null && !loading && (
            <Button
              size="small"
              variant="outlined"
              onClick={() => {
                // Logik, um zu bestimmen, ob Subject oder Body korrigiert werden soll, basierend auf Fokus
                const activeElement = document.activeElement;
                const isSubjectCurrentlyFocused = subjectInputRef.current === activeElement;
                const isBodyCurrentlyFocused = bodyTextareaRef.current === activeElement;
                
                let fieldToCorrect: 'subject' | 'body' = 'body'; // Default
                if (isSubjectCurrentlyFocused) fieldToCorrect = 'subject';
                else if (isBodyCurrentlyFocused) fieldToCorrect = 'body';

                // Snippet-Korrektur Logik (optional, falls benötigt)
                const textarea = (fieldToCorrect === 'body' ? bodyTextareaRef.current : subjectInputRef.current) as HTMLTextAreaElement | HTMLInputElement | null;
                let selectedTextVal: string | undefined = undefined;
                let selectionStartVal: number | undefined = undefined;
                let selectionEndVal: number | undefined = undefined;

                if (textarea && textarea.selectionStart !== null && textarea.selectionEnd !== null && textarea.selectionStart !== textarea.selectionEnd) {
                    selectionStartVal = textarea.selectionStart;
                    selectionEndVal = textarea.selectionEnd;
                    selectedTextVal = textarea.value.substring(selectionStartVal, selectionEndVal);
                }
                
                handleCorrectClick(fieldToCorrect, selectedTextVal, selectionStartVal, selectionEndVal);
              }}
              disabled={correctButtonDisabled || !!correctingStates[`direct_${selectedEmailId}_${isSubjectFocused ? 'subject' : 'body'}`]?.[isSubjectFocused ? 'subject' : 'body']}
              sx={{
                position: 'absolute',
                bottom: 8,
                right: 6,
                minWidth: 0,
                padding: '2px 6px',
                // Standardfarben oder Theme-Farben hier wieder einsetzen
                color: 'grey.400', 
                borderColor: 'grey.700',
                '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.08)', borderColor: 'grey.600' }
              }}
            >
              {!!correctingStates[`direct_${selectedEmailId}_${isSubjectFocused ? 'subject' : 'body'}`]?.[isSubjectFocused ? 'subject' : 'body'] ? <CircularProgress size={14} sx={{ mr: 0.5 }} /> : null}
              Correct
            </Button>
          )}
        </Box>

        {/* NEU: Container für Chips und Refresh-Button nebeneinander */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
          {/* Suggestion Chips */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'flex-start',
              alignItems: 'center',
              gap: 1,
              flexWrap: 'wrap',
              flexGrow: 1,
              mt: 0.5,
              mb: 0.5,
              overflow: 'hidden',
              minHeight: '36px',
              position: 'relative',
            }}
          >
            {(!loading && suggestions.length > 0) && suggestions.map((s: AISuggestion, index: number) => (
              <Chip
                key={s.id}
                label={s.title || s.type}
                onClick={() => handleLocalSelectSuggestion(index)}
                onMouseDown={() => console.log(`[ReplyView Chip Debug] onMouseDown detected for index: ${index}`)}
                size="small"
                variant={(index === selectedSuggestionIndex) ? "filled" : "outlined"}
                color={(index === selectedSuggestionIndex) ? "primary" : "default"}
                sx={{ cursor: 'pointer' }}
              />
            ))}
          </Box>

          {/* Spinner+Text direkt LINKS neben Refresh-Button */}
          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', minHeight: '28px', height: '28px', mr: 1 }}>
              <CircularProgress size={18} sx={{ mr: 1 }} />
              <Typography sx={{ color: 'grey.500', textAlign: 'left', fontSize: '0.95rem', lineHeight: 1, display: 'flex', alignItems: 'center', height: '18px' }}>Generating suggestions...</Typography>
            </Box>
          )}

          {/* Refresh Button */}
          <Tooltip title="Refresh Suggestions">
            <span>
            <IconButton size="small" onClick={handleInternalRefresh} disabled={!selectedEmailId || loading || isRefining}>
              <RefreshIcon fontSize="small" />
            </IconButton>
            </span>
          </Tooltip>
        </Box>

        {/* Refine Input Area */}
        <Box
          sx={{
            display: 'flex',
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            position: 'relative',
          }}
        >
          <TextField
            fullWidth
            multiline
            minRows={3}
            maxRows={8}
            placeholder="Enter custom instructions to refine..."
            variant="outlined"
            value={customPrompt}
            // onClick={(e) => e.stopPropagation()} // PROPAGATION WIRD HIER NICHT GESTOPPT
            onChange={(e) => setCustomPrompt(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                e.preventDefault();
                const keydown_isDisabled_isRefining = isRefining;
                const keydown_isDisabled_promptEmpty = customPrompt.trim() === '';
                const keydown_isDisabled_noEmail = !selectedEmailId;
                console.log(`[ReplyView onKeyDown Check] Disabled checks: noEmail=${keydown_isDisabled_noEmail}, isRefining=${keydown_isDisabled_isRefining}, promptEmpty=${keydown_isDisabled_promptEmpty}`);
                const isRefineDisabled = keydown_isDisabled_noEmail || keydown_isDisabled_isRefining || keydown_isDisabled_promptEmpty;
                if (!isRefineDisabled) {
                   console.log("[ReplyView onKeyDown] Calling handleRefineClick (direct text refine).");
                   handleRefineClick();
                } else {
                   console.log("[ReplyView onKeyDown] Refine prevented by disabled check.");
                }
              }
            }}
            disabled={!selectedEmailId || loading || isRefining}
            sx={{
              maxHeight: '30vh',
              overflow: 'auto',
              '& .MuiInputBase-root': { alignItems: 'flex-start', p:1.5 },
              '& textarea': { overflow: 'auto !important' }
            }}
          />
          {/* Refine Button - Ursprüngliches Design wiederherstellen */}
           <Button
             size="small"
             variant="outlined" // War fälschlicherweise "contained"
             onClick={handleRefineClick}
             disabled={!selectedEmailId || isRefining || customPrompt.trim() === ''}
             sx={{
               position: 'absolute',
               bottom: 8,
               right: 8,
               minWidth: 0,
               padding: '2px 6px',
               color: 'grey.400', // Ursprüngliche Farbe
               borderColor: 'grey.700', // Ursprüngliche Farbe
               '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.08)', borderColor: 'grey.600' } // Ursprünglicher Hover
             }}
           >
             {/* Kommentar verschoben und in JSX-Syntax */}
             {/* Ursprüngliche Größe */} 
             {isRefining ? <CircularProgress size={14} sx={{ mr: 0.5 }} /> : null}
             Refine
           </Button>
        </Box>

        {/* Correction Error Alert */}
        {correctionError && showCorrectionError && (
          <Alert severity="warning" sx={{ mt: 1, flexShrink: 0 }} onClose={() => setShowCorrectionError(false)}>
            {correctionError}
          </Alert>
        )}

        {/* Refine Error Alert */}
        {refineError && (
          <Alert severity="error" sx={{ mt: 1, flexShrink: 0 }} onClose={() => setRefineError(null)}>
            {refineError}
          </Alert>
        )}
      </Box>
    </Box>
  );
}; 