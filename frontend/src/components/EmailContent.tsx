import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  useTheme,
  IconButton,
  Tooltip,
  Stack,
  ToggleButtonGroup,
  ToggleButton
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Html as HtmlIcon,
  TextFields as TextFieldIcon,
  Code as MarkdownIcon,
  OpenInNew as OpenInNewIcon,
  Download as DownloadIcon
} from '@mui/icons-material';
import { getEmailDetail, EmailDetailData } from '../services/api';
import ReactMarkdown from 'react-markdown';
import './EmailContent.css';
// import { Email, Attachment } from '../lib/types'; // Commented out - Define locally if needed or covered by EmailDetailData

// Define local placeholders if types are needed and not covered by EmailDetailData
// (Attachment might be defined within EmailDetailData already)
interface Attachment { // Example Placeholder
  id: number;
  filename: string;
  content_type: string;
  size: number;
  file: string; 
  content_id?: string | null; // Allow null based on API data type
}

// Styled components für den Iframe
const IframeContainer = styled(Box)<{ loaded: string }>(({ theme, loaded }) => ({
  position: 'relative', // Für Ladeindikator
  width: '100%',
  height: 'auto', // Erlaube dynamische Höhe
  minHeight: '100px', // Verhindert Kollabieren vor dem Laden
  opacity: loaded === "true" ? 1 : 0, // Einblenden wenn geladen
  transition: theme.transitions.create('opacity', {
    duration: theme.transitions.duration.short,
  }),
}));

const StyledIframe = styled('iframe')({
  width: '100%',
  minHeight: '100px', // Min Höhe, bevor der Inhalt geladen ist
  height: 'auto', // Start mit auto, wird dynamisch gesetzt
  border: 'none',
  display: 'block',
});

// LocalStorage key for view mode
const VIEW_MODE_STORAGE_KEY = 'emailViewMode';

// Type for view mode
type ViewMode = 'html' | 'text' | 'markdown' | 'headers';

// Function to load view mode from localStorage
const loadViewMode = (): ViewMode => {
  const storedMode = localStorage.getItem(VIEW_MODE_STORAGE_KEY);
  // Check if the stored mode is one of the valid modes
  if (storedMode === 'markdown' || storedMode === 'html' || storedMode === 'text' || storedMode === 'headers') {
    return storedMode;
  }
  // Default to Markdown if nothing valid is stored or upon first load
  return 'markdown'; // Changed default from 'html' to 'markdown'
};

// Function to save view mode to localStorage
const saveViewMode = (mode: ViewMode) => {
  localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
};

interface EmailContentProps {
  emailDetail: EmailDetailData | null;
  loading: boolean;
  error: string | null;
}

export const EmailDetail: React.FC<EmailContentProps> = ({ emailDetail, loading, error }) => {
  const componentRenderStart = performance.now(); // Start timing component render
  console.log(`[EmailDetail] Component render start.`);

  const [viewMode, setViewMode] = useState<ViewMode>(loadViewMode()); 
  const theme = useTheme();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [isIframeLoaded, setIsIframeLoaded] = useState(false);
  const [iframeSrcDoc, setIframeSrcDoc] = useState<string | undefined>(undefined);
  const iframeBlobUrlRef = useRef<string | null>(null); // Ref to store the current blob URL for cleanup

  // Helper function to generate srcDoc (moved logic here)
  const generateSrcDoc = (bodyHtml: string, attachments: Attachment[], currentTheme: typeof theme): string => {
    const effectStart = performance.now();
    console.log(`[EmailDetail] generateSrcDoc START.`);

    let processedHtml = bodyHtml;

    // 1. CID Replacement (Re-enabled)
    const cidMap: { [key: string]: string } = {};
    if (attachments && attachments.length > 0) {
      attachments.forEach(att => {
        const cleanedCid = att.content_id?.replace(/^<|>$/g, '');
        if (cleanedCid && att.file) {
          cidMap[cleanedCid] = att.file;
        }
      });
    }
    const replaceStart = performance.now();
    processedHtml = processedHtml.replace(/src="cid:([^"<>]+)"/gi, (match, rawCid) => {
      const cleanedCid = rawCid.replace(/^<|>$/g, '');
      const url = cidMap[cleanedCid];
      if (url) {
        return `src="${url}"`;
      }
      return match;
    });
    const replaceEnd = performance.now();
    console.log(`[EmailDetail] CID replacement took: ${(replaceEnd - replaceStart).toFixed(2)} ms`);

    // 2. Construct the document (NO EXTRA CSS INJECTED)
    const doc = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <!-- Minimal styles for basic rendering and dark mode compatibility -->
        <style>
          body {
             margin: 15px;
             padding: 0;
             word-wrap: break-word;
             font-family: sans-serif; /* Basic fallback font */
           }
        </style>
      </head>
      <body>
        ${processedHtml}
      </body>
      </html>
    `;

    const effectEnd = performance.now();
    console.log(`[EmailDetail] generateSrcDoc END. Duration: ${(effectEnd - effectStart).toFixed(2)} ms`);
    return doc;
  };

  useEffect(() => {
    saveViewMode(viewMode);
  }, [viewMode]);

  // Effekt zum Anpassen der Iframe-Höhe nach dem Laden
  useEffect(() => {
    if (isIframeLoaded && iframeRef.current && iframeRef.current.contentWindow) {
      try {
        const body = iframeRef.current.contentWindow.document.body;
        const html = iframeRef.current.contentWindow.document.documentElement;
        const contentHeight = Math.max(
             body.scrollHeight, body.offsetHeight, 
             html.clientHeight, html.scrollHeight, html.offsetHeight 
        );
        const newHeight = contentHeight + 30; // +30px Puffer
        iframeRef.current.style.height = `${newHeight}px`;
        console.log(`[EmailDetail] Iframe content loaded. Setting height to: ${newHeight}px (Content: ${contentHeight}px)`);
      } catch (e) {
        console.error("[EmailDetail] Error accessing iframe content height:", e);
        iframeRef.current.style.height = '500px'; 
      }
    }
  }, [isIframeLoaded]);

  // Effekt: Generiere iframeSrcDoc, wenn emailDetail.body_html sich ändert
  useEffect(() => {
    if (emailDetail && emailDetail.body_html) {
      const generatedSrcDoc = generateSrcDoc(emailDetail.body_html, emailDetail.attachments, theme);
      const blob = new Blob([generatedSrcDoc], { type: 'text/html' });
      const blobUrl = URL.createObjectURL(blob);
      setIframeSrcDoc(blobUrl);
      if (iframeBlobUrlRef.current) {
        URL.revokeObjectURL(iframeBlobUrlRef.current);
      }
      iframeBlobUrlRef.current = blobUrl;
    } else {
      setIframeSrcDoc(undefined);
      if (iframeBlobUrlRef.current) {
        URL.revokeObjectURL(iframeBlobUrlRef.current);
        iframeBlobUrlRef.current = null;
      }
    }
    setIsIframeLoaded(false);
  }, [emailDetail, theme]);

  // Cleanup Blob URL on unmount
  useEffect(() => {
    return () => {
      if (iframeBlobUrlRef.current) {
        URL.revokeObjectURL(iframeBlobUrlRef.current);
        iframeBlobUrlRef.current = null;
      }
    };
  }, []);

  // Reset iframe loaded state when view mode changes
  useEffect(() => {
    setIsIframeLoaded(false);
  }, [viewMode, emailDetail]);

  // Loading, error, and !email checks (angepasst)
  if (loading && (!emailDetail || (!emailDetail.subject && !emailDetail.body_text && !emailDetail.body_html))) {
    return (
      <Box sx={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', bgcolor: 'background.default' }}>
        <CircularProgress />
      </Box>
    );
  }
  if (error) {
    return (
      <Box sx={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', p: 2, bgcolor: 'background.default' }}>
        <Alert severity="error" sx={{ width: '100%' }}>{error}</Alert>
      </Box>
    );
  }
  if (!emailDetail) {
    return (
      <Box sx={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', bgcolor: 'background.default' }}>
        <Typography color="text.secondary">
          No email data available.
        </Typography>
      </Box>
    );
  }

  // Determine content availability
  const hasHtml = !!emailDetail.body_html;
  const hasText = !!emailDetail.body_text?.trim();
  const hasMarkdown = !!emailDetail.markdown_body?.trim(); // Check for markdown content

  // Determine available modes based on the *current email state* (for rendering the toggle group)
  const availableModes: ViewMode[] = [];
  if (hasHtml) availableModes.push('html');
  if (hasMarkdown) availableModes.push('markdown');
  if (hasText) availableModes.push('text');
  // Add 'headers' later if implemented
  
  // Determine if toggle group should be shown (at least two view options available)
  const showToggleGroup = availableModes.length > 1;

  // Log before returning the JSX including the iframe
  const renderEnd = performance.now();
  console.log(`[EmailDetail] Component render END. Duration: ${(renderEnd - componentRenderStart).toFixed(2)} ms. Rendering iframe element with srcDoc (length: ${iframeSrcDoc?.length ?? 0})`);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', bgcolor: 'background.default' }}>
      {/* Header */} 
      <Box sx={{ 
        borderBottom: '1px solid', 
        borderColor: 'divider',
        p: 2, // Revert padding
        flexShrink: 0,
        bgcolor: 'background.paper', // Revert background
        position: 'relative', // Needed for positioning the toggle button group
      }}>
        {/* --- Container for Summary and Date --- */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          {/* --- MEDIUM SUMMARY --- */}
          <Box sx={{ flexGrow: 1, pr: 2 /* Add some padding between summary and date */ }}>
            {emailDetail.medium_summary && (
              <Typography 
                variant="subtitle1" 
                sx={{ 
                  display: 'block', 
                  color: 'text.primary',
                  fontWeight: 'bold' // Make it bold
                }}
              >
                {emailDetail.medium_summary} 
              </Typography>
            )}
          </Box>
          {/* --- Date/Time --- */}
          <Typography color="text.secondary" sx={{ fontSize: '0.875rem', whiteSpace: 'nowrap', flexShrink: 0 }}>
            {new Date(emailDetail.sent_at || emailDetail.received_at || Date.now())
              .toLocaleString(undefined, { year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) // Format without seconds
            }
          </Typography>
        </Box>
        {/* --- END Container for Summary and Date --- */}

        {/* --- Subject --- */}
        <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary', pr: '40px' /* Add padding to avoid overlap */ }}>
          {emailDetail.subject}
        </Typography>

        {/* --- From Box (without Date/Time) --- */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5 }}>
            <Typography color="text.secondary" sx={{ fontSize: '0.875rem', mr: 0.5 }}>
              From:
            </Typography>
            <Chip size="small" label={emailDetail.from_address} sx={{ bgcolor: 'action.selected' }}/>
          </Box>
          {/* Date/Time removed from here */}
        </Box>
        { (emailDetail.to_contacts && emailDetail.to_contacts.length > 0) && (
          <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5, mb: 0.5 }}>
            <Typography color="text.secondary" sx={{ fontSize: '0.875rem', mr: 0.5 }}>
              To:
            </Typography>
            {emailDetail.to_contacts.map(contact => (
              <Chip key={contact.id} size="small" label={contact.email} sx={{ bgcolor: 'action.selected' }}/>
            ))}
          </Box>
        )}
         { (emailDetail.cc_contacts && emailDetail.cc_contacts.length > 0) && (
          <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5 }}>
            <Typography color="text.secondary" sx={{ fontSize: '0.875rem', mr: 0.5 }}>
              Cc:
            </Typography>
            {emailDetail.cc_contacts.map(contact => (
              <Chip key={contact.id} size="small" label={contact.email} sx={{ bgcolor: 'action.selected' }}/>
            ))}
          </Box>
        )}
      </Box>
      
      {/* Body - Conditional rendering based on viewMode */}
      <Box sx={{ 
        flex: 1, 
        overflowY: 'auto', // Keep scrolling on this container
        p: 0, 
        bgcolor: 'background.paper',
        position: 'relative', // For positioning controls like toggle group
      }}>
        
        {/* --- Toggle Button Group --- */}
        {showToggleGroup && (
          <ToggleButtonGroup
            value={viewMode}
            exclusive // Only one button can be selected at a time
            onChange={(event, newViewMode) => {
              if (newViewMode !== null) {
                console.log(`[EmailDetail] View mode changed to: ${newViewMode}`);
                setViewMode(newViewMode);
              } else {
                console.log(`[EmailDetail] Clicked selected view mode button, no change.`);
              }
            }}
            aria-label="Email view mode"
            size="small"
            sx={{
              position: 'absolute',
              top: theme.spacing(1), // Position top-right
              right: theme.spacing(1),
              zIndex: 1, // Above content
              bgcolor: 'background.default', // Make background visible
              '& .MuiToggleButtonGroup-grouped': { // Style individual buttons
                // Add some spacing if needed, or adjust borders
                // border: 0, // Optional: remove default borders if overlapping looks odd
              },
            }}
          >
            {availableModes.includes('markdown') && (
              <ToggleButton value="markdown" aria-label="Markdown view">
                 <Tooltip title="Markdown View">
                   <MarkdownIcon fontSize="small" /> 
                 </Tooltip>
              </ToggleButton>
            )}
            {availableModes.includes('text') && (
              <ToggleButton value="text" aria-label="Text view">
                 <Tooltip title="Text View">
                    <TextFieldIcon fontSize="small" />
                 </Tooltip>
              </ToggleButton>
            )}
            {availableModes.includes('html') && (
              <ToggleButton value="html" aria-label="HTML view">
                <Tooltip title="HTML View">
                  <HtmlIcon fontSize="small" />
                </Tooltip>
              </ToggleButton>
            )}
             {/* Add 'headers' button here when implemented */}
          </ToggleButtonGroup>
        )}
        {/* --- End Toggle Button Group --- */}
        
        {/* --- Content Rendering based on availability and mode --- */}
        {!hasHtml && !hasText && !hasMarkdown ? (
          // Case: Neither HTML nor Text nor Markdown content exists
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', p: 2 }}>
            <Typography color="text.secondary">No content available for this email.</Typography>
          </Box>
        ) : viewMode === 'html' && hasHtml ? (
          // Case: Render HTML (if selected and available)
          <IframeContainer 
            loaded={isIframeLoaded ? "true" : "false"} 
            // sx={{ opacity: 1 }} // Temporarily disable opacity transition for debugging spinner
          >
            {/* Show spinner SIMPLY whenever iframe is not loaded yet */}
            {!isIframeLoaded && (
              <Box sx={{ 
                position: 'absolute', 
                top: '50%', 
                left: '50%', 
                transform: 'translate(-50%, -50%)', 
                zIndex: 1, // Ensure spinner is above iframe content before it loads
                // Make background slightly visible to ensure it covers content area
                // backgroundColor: 'rgba(0, 0, 0, 0.1)', 
                display: 'flex', // Use flex to center spinner
                alignItems: 'center',
                justifyContent: 'center',
                width: '100%', // Ensure it covers the iframe area
                height: '100%', // Ensure it covers the iframe area
              }}>
                <CircularProgress size={30} />
              </Box>
            )}
            {/* {console.log(`[EmailDetail ${emailId}] Rendering iframe element with srcDoc (length: ${iframeSrcDoc?.length ?? 0})`)} */}
            <StyledIframe
              ref={iframeRef}
              // Use src instead of srcDoc when using Blob URL
              src={iframeSrcDoc} // State now holds the Blob URL or undefined
              title={`Email Body - ${emailDetail?.subject}`}
              sandbox="allow-same-origin allow-popups" // Keep sandboxing restrictive for now
              onLoad={() => {
                const loadEnd = performance.now();
                console.log(`[EmailDetail] Iframe onLoad triggered. Time since component render start: ${(loadEnd - componentRenderStart).toFixed(2)} ms`);
                // Kurze Verzögerung, um sicherzustellen, dass das Rendering abgeschlossen ist
                setTimeout(() => {
                    if (iframeRef.current) {
                        console.log(`[EmailDetail] Setting isIframeLoaded=true after timeout.`);
                        setIsIframeLoaded(true);
                    }
                }, 100); 
              }}
            />
          </IframeContainer>
        ) : viewMode === 'markdown' && hasMarkdown ? (
           // Case: Render Markdown (if selected and available)
           <Box sx={{ p: 2, overflowY: 'auto', height: '100%', bgcolor: 'background.paper' }} className="markdown-output">
              {/* Verwende react-markdown zum Rendern des Markdown-Inhalts */}
              <ReactMarkdown 
                components={{
                  // Überschreibe das Standard-Rendering für `a` (Links)
                  a: ({node, ...props}) => 
                    <a {...props} target="_blank" rel="noopener noreferrer" />
                }}
              >
                {emailDetail.markdown_body || ''}
              </ReactMarkdown>
           </Box>
        ) : viewMode === 'text' && hasText ? (
          // Case: Render Text (if selected and available)
          <Box sx={{ p: 2, overflowY: 'auto', height: '100%', bgcolor: 'background.paper' }}>
            <Typography 
               variant="subtitle2" 
               sx={{ whiteSpace: 'pre-wrap', color: 'text.secondary' }}
             >
              { emailDetail.body_text?.replace(/(\n\s*){2,}/g, '\n').trim() || '' } {/* Show text, remove extra lines */}
            </Typography>
          </Box>
        ) : (
           // Fallback/Loading state while switching modes? Or handle invalid state earlier.
           // This should ideally not be reached due to the useEffect hook adjusting the mode.
           <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', p: 2 }}>
               <CircularProgress size={20} /> 
               <Typography sx={{ml: 1}}>Loading view...</Typography>
           </Box>
        )}
        {/* --- End Content Rendering --- */}
      </Box>
    </Box>
  );
};

export default EmailDetail; 