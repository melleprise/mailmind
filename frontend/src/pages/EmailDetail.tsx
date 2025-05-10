import React, { useEffect, useState } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemText,
  Typography,
  Paper,
  IconButton,
  Divider,
  Chip,
  CircularProgress,
  Button,
  Alert,
  Stack,
  Grid,
  useTheme,
  ToggleButton,
  ToggleButtonGroup,
  TextField,
} from '@mui/material';
import {
  AttachFile as AttachFileIcon,
  Html as HtmlIcon,
  TextFields as TextFieldsIcon,
} from '@mui/icons-material';
import { getEmailById, markEmailRead, regenerateEmailSuggestions } from '../services/api';
import { format } from 'date-fns';
import { useEmailStore } from '../stores/emailStore';
// import { Email, AISuggestion, Attachment } from '../types'; // Cannot find module - commented out
import { getEmailDetail /*, sendReply */ } from '../services/api'; // Removed fetchEmailDetail (use getEmailDetail), sendReply (define below or import if exists elsewhere) - Commented out sendReply
import { useAuth } from '../contexts/AuthContext';
// import InteractionCard from '../components/InteractionCard'; // Cannot find module - commented out
// import SummarySuggestions from '../components/SummarySuggestions'; // Cannot find module - commented out
// import { markEmailAsRead, moveEmailToSpam } from '../services/emailActions'; // Cannot find module - commented out

// Interface for the data structure returned by getEmailById
interface EmailDetailData {
  id: number;
  subject: string;
  from_address: string;
  from_name: string; // Added based on EmailList
  // Assuming the backend provides these based on the serializer
  to_contacts: { id: number; name: string; email: string; }[]; 
  cc_contacts: { id: number; name: string; email: string; }[];
  bcc_contacts: { id: number; name: string; email: string; }[];
  received_at: string; // Changed from received_date
  sent_at: string; // Added based on serializer
  body_html: string;
  body_text: string;
  is_read: boolean;
  attachments: Attachment[];
  suggestions?: AISuggestion[]; // Add suggestions array
  has_attachments?: boolean;
  ai_processed?: boolean;
  ai_processed_at?: string; // Match store type
}

// Define types locally if import fails
interface Attachment {
  id: number;
  filename: string;
  content_type: string;
  size: number;
  file: string; 
  content_id?: string;
}
interface AISuggestion {
  id: string; 
  type: string;
  title: string;
  content: string;
  status: string;
  created_at: string;
  processing_time: number;
}

// Add Props interface to accept emailId
interface EmailDetailProps {
  emailId: number | null;
}

const EmailDetail: React.FC<EmailDetailProps> = ({ emailId }) => {
  const theme = useTheme(); // Get theme object
  const numericEmailId = emailId;

  // Zustand selectors - These trigger re-renders when their values change
  const selectedEmail = useEmailStore((state) => state.selectedEmail);
  const loading = useEmailStore((state) => state.loading);
  const error = useEmailStore((state) => state.error);
  const fetchEmail = useEmailStore((state) => state.fetchEmail); // Keep ref to the action
  const clearSelectedEmail = useEmailStore((state) => state.clearSelectedEmail); // Keep ref to the action
  // Get the counter from the store
  const fetchCounter = useEmailStore((state) => state.fetchCounter);

  // Local state for regeneration UI only
  const [regenerating, setRegenerating] = useState<boolean>(false);
  const [regenerateStatus, setRegenerateStatus] = useState<string | null>(null);
  const [iframeSrcDoc, setIframeSrcDoc] = useState<string | undefined>(undefined);
  const [viewMode, setViewMode] = useState<'html' | 'text'>('html'); // State for view mode
  const [prompt, setPrompt] = useState('');

  // Log component render entry
  console.log(`[EmailDetail Render] Start. emailId prop: ${emailId}, Store loading: ${loading}, Store selectedId: ${selectedEmail?.id}`);

  // Effect to fetch email based on emailId prop
  useEffect(() => {
    // Use the Zustand state directly inside the effect
    const currentSelectedId = useEmailStore.getState().selectedEmail?.id;
    const isLoading = useEmailStore.getState().loading;

    // Log entry into this effect
    console.log(`[EmailDetail Fetch Effect] Running. Prop emailId: ${numericEmailId}, Current selectedId: ${currentSelectedId}, IsLoading: ${isLoading}`);

    if (numericEmailId) {
      // Check if the ID changed OR if there's no selected email yet
      if ((!currentSelectedId || currentSelectedId !== numericEmailId) && !isLoading) {
        console.log(`[EmailDetail Fetch Effect] Requesting fetch for ${numericEmailId} because selected is ${currentSelectedId} or ID changed.`);
        fetchEmail(numericEmailId); // Call the action
      } else if (currentSelectedId === numericEmailId) {
         console.log(`[EmailDetail Fetch Effect] ID ${numericEmailId} matches selected ID. No fetch needed.`);
      } else if (isLoading) {
         console.log(`[EmailDetail Fetch Effect] Skipping fetch for ${numericEmailId} because isLoading is true.`);
      }
    } else {
      // If emailId becomes null, clear the selection
      if (currentSelectedId) {
          console.log("[EmailDetail Fetch Effect] Clearing selection because numericEmailId is null.");
          clearSelectedEmail(); // Call the action
      } else {
          console.log("[EmailDetail Fetch Effect] numericEmailId is null, nothing selected. Doing nothing.");
      }
    }
  }, [numericEmailId, fetchEmail, clearSelectedEmail]);

  // Effect to create iframe content with injected styles and resolved CIDs
  useEffect(() => {
    // ADD CONSOLE LOG HERE to check if this effect runs and what selectedEmail contains
    console.log('[EmailDetail iframeSrcDoc Effect] Running. selectedEmail ID:', selectedEmail?.id, 'Has body_html:', !!selectedEmail?.body_html, 'Has body_text:', !!selectedEmail?.body_text);

    if (selectedEmail?.body_html) {
      let processedHtml = selectedEmail.body_html;

      // 1. Create a map of content_id to attachment URL
      const cidMap: { [key: string]: string } = {};
      if (selectedEmail.attachments && selectedEmail.attachments.length > 0) {
        selectedEmail.attachments.forEach(att => {
          // Ensure content_id exists and remove '<>' brackets if present
          const cleanedCid = att.content_id?.replace(/^<|>$/g, '');
          if (cleanedCid && att.file) { 
            cidMap[cleanedCid] = att.file; // Use the file URL directly
          }
        });
      }

      // 2. Replace cid: links in the HTML
      processedHtml = processedHtml.replace(/src="cid:([^"]+)"/gi, (match, cid) => {
        const cleanedCid = cid.replace(/^<|>$/g, ''); // Clean CID just in case
        const url = cidMap[cleanedCid];
        if (url) {
          console.log(`Replacing CID: ${cleanedCid} with URL: ${url}`);
          return `src="${url}"`;
        }
        console.warn(`Could not find attachment URL for CID: ${cleanedCid}`);
        return match; // Keep original src if no match found
      });

      // Use theme's paper background for the body inside iframe
      const bodyBgColor = theme.palette.background.paper;
      // Use white text color as requested
      const textColor = '#ffffff';

      const styles = `
        <style>
          /* Base styles for html and body */
          html, body {
            background-color: ${bodyBgColor} !important;
            background: ${bodyBgColor} !important;
            color: ${textColor} !important;
            font-family: ${theme.typography.fontFamily};
            font-size: ${theme.typography.body2.fontSize};
            line-height: ${theme.typography.body2.lineHeight};
            margin: 0;
            padding: 8px;
          }

          /* Target specific problematic wrappers like the one found */
          .hse-body-background, .hse-body-wrapper-table, #hs_cos_wrapper_main /* Add other common wrappers */ {
            background-color: ${bodyBgColor} !important;
            background: ${bodyBgColor} !important;
          }

          /* Universal selector for broad coverage */
          * {
            background-color: transparent !important;
            background: none !important;
            color: inherit !important; /* Use inherit */
            border-color: rgba(255, 255, 255, 0.23) !important;
          }

          /* Re-apply body color to ensure it overrides * */
          body {
            color: ${textColor} !important;
          }

          /* Re-apply link color specifically */
          a {
            background-color: transparent !important;
            background: none !important;
            color: ${theme.palette.primary.main} !important;
          }

          /* Basic image styling */
          img {
            max-width: 100%;
            height: auto;
           /* filter: grayscale(100%); */ /* Removed grayscale filter */
          }
        </style>
      `;

      // Construct the full HTML document for srcDoc with processed HTML
      const doc = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          ${styles}
        </head>
        <body>
          ${processedHtml} 
        </body>
        </html>
      `;
      setIframeSrcDoc(doc);
    } else {
      setIframeSrcDoc(undefined); // Clear if no HTML body
    }
    // Depend only on selectedEmail object itself
    // ADD fetchCounter to dependencies to force re-run
  }, [selectedEmail, fetchCounter]);

  const handleRegenerate = async () => {
    if (!numericEmailId) return;
    setRegenerating(true);
    setRegenerateStatus(null);
    try {
      await regenerateEmailSuggestions(numericEmailId);
      setRegenerateStatus('Suggestion regeneration queued successfully. Refreshing data...');
      fetchEmail(numericEmailId); 
    } catch (err) {
      console.error("Error regenerating suggestions:", err);
      setRegenerateStatus('Failed to queue suggestion regeneration.');
    } finally {
      setRegenerating(false);
    }
  };

  const handleViewModeChange = (
    event: React.MouseEvent<HTMLElement>,
    newViewMode: 'html' | 'text' | null, // Can be null if nothing is selected
  ) => {
    if (newViewMode !== null) {
      setViewMode(newViewMode);
    }
  };

  // Placeholder function for marking as spam
  const handleMarkAsSpam = async () => {
    if (!selectedEmail) return;
    try {
      console.log(`Marking email ${selectedEmail.id} as read and moving to Spam...`);
      
      // 1. Mark as read (implement API call in services/emailActions.ts)
      // await markEmailAsRead(selectedEmail.id); // Uncomment when API is ready
      
      // 2. Move to Spam (implement API call in services/emailActions.ts)
      // await moveEmailToSpam(selectedEmail.id); // Uncomment when API is ready

      console.log(`Email ${selectedEmail.id} marked as spam successfully.`);
      // Optional: Close detail view or navigate back/refresh list
      // Example: navigate(-1); or trigger list refresh
      alert('E-Mail als Spam markiert und verschoben.'); // Simple feedback

    } catch (error) {
      console.error('Error marking email as spam:', error);
      alert('Fehler beim Markieren als Spam.'); // Simple error feedback
    }
  };

  // Log right before loading check
  console.log(`[EmailDetail Render] Before loading check. loading: ${loading}, selectedEmail?.id: ${selectedEmail?.id}, numericEmailId: ${numericEmailId}`);

  // --- CHECKS --- 
  // 1. Loading Check (Simplified)
  if (loading) {
    console.log('[EmailDetail Render] Showing loading spinner.');
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress />;</Box>;
  }
  
  // 2. Error Check
  if (error) {
    console.log(`[EmailDetail Render] Showing error: ${error}`);
    return <Alert severity="error" sx={{ m: 2 }}>{error}</Alert>;
  }

  // 3. No emailId prop Check
  if (numericEmailId === null) {
    console.log('[EmailDetail Render] No emailId prop provided, showing placeholder.');
    return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', p: 4 }}>
            <Typography color="text.secondary">Select an email to view details.</Typography>
        </Box>
    );
  }

  // 4. Mismatch/Missing selectedEmail Check
  // If loading is finished, but the email ID doesn't match the requested ID,
  // show a spinner briefly, assuming the state update is pending.
  if (!selectedEmail || selectedEmail.id !== numericEmailId) {
    // Refine log to show exact values being compared
    console.warn(`[EmailDetail Render] Mismatch/null check triggered. numericEmailId: ${numericEmailId}, selectedEmail object: ${selectedEmail ? JSON.stringify({id: selectedEmail.id}) : 'null'}. Showing spinner temporarily...`);
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress />;</Box>; 
  }

  // --- Render email details (selectedEmail IS NOW GUARANTEED TO MATCH numericEmailId) ---
  // Log when starting to render actual content
  console.log(`[EmailDetail Render] Rendering content for email ID: ${selectedEmail.id}`);

  const formatContacts = (contacts: { name: string; email: string }[] | undefined) => {
    if (!contacts) return ''; // Handle undefined case
    return contacts.map(c => c.name ? `${c.name} <${c.email}>` : c.email).join(', ');
  };

  // Placeholder for handleSendReply - implement actual logic later
  const handleSendReply = () => {
    console.warn('handleSendReply function not implemented yet.');
    // Add logic to send the reply using the 'prompt' state and selectedEmail details
    // Example: sendReply(selectedEmail.id, prompt);
  };

  return (
    <Box sx={{ p: 2, height: '100%', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
      <Paper elevation={2} sx={{ p: 3, mb: 2, flexShrink: 0 /* Prevent header from shrinking */ }}>
        <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'medium' /* Optional: make it slightly bolder */ }}>
          {selectedEmail.subject || 'No Subject'}
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          From: {selectedEmail.from_name ? `${selectedEmail.from_name} <${selectedEmail.from_address}>` : selectedEmail.from_address}
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block">
          Received: {selectedEmail.received_at ? new Date(selectedEmail.received_at).toLocaleString() : 'N/A'}
        </Typography>
        {selectedEmail.to_contacts && selectedEmail.to_contacts.length > 0 && (
          <Typography variant="subtitle1" color="text.secondary">
            To: {formatContacts(selectedEmail.to_contacts)}
          </Typography>
        )}
        {selectedEmail.cc_contacts && selectedEmail.cc_contacts.length > 0 && (
          <Typography variant="subtitle1" color="text.secondary">
            Cc: {formatContacts(selectedEmail.cc_contacts)}
          </Typography>
        )}
      </Paper>

      {/* Mode Toggle Buttons */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={handleViewModeChange}
          aria-label="Email view mode"
          size="small"
          sx={{ marginBottom: 1 }}
        >
          <ToggleButton value="html" aria-label="html view">
            <HtmlIcon />
          </ToggleButton>
          <ToggleButton value="text" aria-label="text view">
            <TextFieldsIcon />
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Conditional Rendering based on viewMode */}
      {viewMode === 'html' && iframeSrcDoc && (
            <iframe
              srcDoc={iframeSrcDoc}
          title="Email Content"
          style={{ width: '100%', height: '500px', border: 'none', backgroundColor: theme.palette.background.paper }}
        />
      )}
      {/* NEU: Fallback für HTML-View, wenn nur Text da ist */}
      {viewMode === 'html' && !iframeSrcDoc && selectedEmail?.body_text && (
          <Typography component="pre" sx={{ p: 2, whiteSpace: 'pre-wrap', fontFamily: 'monospace', wordWrap: 'break-word' }}>
              {selectedEmail.body_text}
          </Typography>
      )}
      {/* Fallback für HTML-View, wenn weder HTML noch Text da sind */}
      {viewMode === 'html' && !iframeSrcDoc && !selectedEmail?.body_text && (
        <Typography sx={{ p: 2 }}>
            No content available.
        </Typography>
        )}

        {viewMode === 'text' && (
         <Typography component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', wordWrap: 'break-word' }}>
           {selectedEmail?.body_text || 'No text content available.'}
            </Typography>
        )}

      {/* Attachments Section */}
      {selectedEmail.attachments && selectedEmail.attachments.length > 0 && (
        <Paper elevation={1} sx={{ p: 2, flexShrink: 0 /* Prevent attachments from shrinking */ }}>
          <Typography variant="h6" gutterBottom>Attachments</Typography>
          <List dense>
            {selectedEmail.attachments.map((att) => (
              <ListItem 
                key={att.id} 
                component="a" 
                href={att.file} // Use the direct file URL
                target="_blank" 
                rel="noopener noreferrer"
                button
              >
                <IconButton edge="start"><AttachFileIcon /></IconButton>
                <ListItemText 
                  primary={att.filename}
                  secondary={`${(att.size / 1024).toFixed(1)} KB - ${att.content_type}`}
                      />
              </ListItem>
                    ))}
          </List>
                </Paper>
            )}

        {/* Suggestions Column */}
        <Grid item xs={12} md={4}>
          <Paper elevation={1} sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">AI Suggestions</Typography>
              <Button 
                variant="outlined"
                size="small"
                onClick={handleRegenerate}
                disabled={regenerating || loading} // Only disable if regenerating or store is loading
              >
                {regenerating ? <CircularProgress size={20} /> : 'Regenerate'}
              </Button>
            </Box>
            
            {regenerateStatus && (
              <Alert severity={regenerateStatus.startsWith('Failed') ? 'error' : 'success'} sx={{ mb: 2 }}>
                {regenerateStatus}
              </Alert>
            )}

            {/* Display suggestions - Ensure selectedEmail.suggestions is checked */}
            {selectedEmail.suggestions && selectedEmail.suggestions.length > 0 ? (
              selectedEmail.suggestions.map((suggestion) => (
                <Paper key={suggestion.id} variant="outlined" sx={{ p: 1.5, mb: 1.5 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    {suggestion.title} 
                    <Typography variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>({suggestion.type})</Typography>
                  </Typography>
                  <Typography variant="body2">{suggestion.content}</Typography>
                </Paper>
              ))
            ) : (
               <Typography variant="body2" color="text.secondary">
                 {/* Check ai_processed status for better messaging */}
                 {selectedEmail.ai_processed === false ? 'Processing suggestions...' :
                  selectedEmail.ai_processed === true && (!selectedEmail.suggestions || selectedEmail.suggestions.length === 0) ? 'No suggestions generated or available.' :
                  'Loading suggestions status...'}
               </Typography>
            )}
          </Paper>
      </Grid>

      {/* Reply/Prompt Input Area - Assuming this is where it is */}
      {selectedEmail && (
        <Box sx={{ mt: 2, mb: 2, p: 2, border: '1px solid grey', borderRadius: 1 }}>
          <TextField
            fullWidth
            variant="outlined"
            multiline
            rows={4}
            placeholder="Enter custom instructions to refine..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            sx={{ mb: 1 }}
          />
          <Button variant="contained" onClick={handleSendReply} disabled={loading}>
            {loading ? <CircularProgress size={24} /> : 'Send'}
          </Button>
           {/* Add Spam and Correct/Refine Buttons here, next to Send */}
           {/* <Button variant="outlined" sx={{ ml: 1 }}>Correct</Button> */}
           {/* <Button variant="outlined" sx={{ ml: 1 }}>Refine</Button> */}
        </Box>
      )}
      
      {/* NEW SPAM BUTTON */}
      {selectedEmail && (
         <Box sx={{ display: 'flex', justifyContent: 'flex-start', gap: 1, mb: 2, mt: 2 }}>
           {/* Style similar to SummarySuggestions buttons */}
           <Button 
             variant="outlined" // Or "contained" depending on desired style
             size="small" // Match size if applicable
             onClick={handleMarkAsSpam}
             disabled={loading}
             sx={{ 
               // Add styling similar to SummarySuggestion buttons below, adjust as needed
               // Example styling (inspect existing buttons for exact values):
               // backgroundColor: theme.palette.action.hover, 
               // borderColor: theme.palette.divider,
               // color: theme.palette.text.secondary,
               // '&:hover': {
               //   backgroundColor: theme.palette.action.selected,
               // },
               textTransform: 'none', // Often used for this style
               borderRadius: '16px', // Example rounded corners
               padding: '4px 12px', // Example padding
             }}
           >
             Spam
           </Button>
            {/* Potentially add other action buttons here (Archive, Delete etc.) */}
         </Box>
      )}

      {/* Summary Suggestions */}
      {/* {selectedEmail && selectedEmail.suggestions && selectedEmail.suggestions.length > 0 && ( // Commented out use as component import is missing
        <SummarySuggestions
          suggestions={selectedEmail.suggestions}
          onSelect={(suggestion: AISuggestion) => setPrompt(suggestion.content)} // Example: Populate prompt on select + Add type
        />
      )} */}
    </Box>
  );
};

export default EmailDetail; 