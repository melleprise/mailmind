import React, { useState, useRef, useEffect } from 'react';
import DOMPurify from 'dompurify'; // Import DOMPurify
import { Email } from '../types';
import { Box, CircularProgress, Typography, IconButton } from '@mui/material';

const EmailContent: React.FC<{ email: Email }> = ({ email }) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [isIframeLoaded, setIsIframeLoaded] = useState(false);
  const [iframeHeight, setIframeHeight] = useState('auto');
  const [showText, setShowText] = useState(false); // State to toggle between HTML and Text
  const [currentSrcDoc, setCurrentSrcDoc] = useState<string | undefined>(undefined); // State to hold srcDoc, initially undefined

  // Function to handle iframe load
  const handleIframeLoad = () => {
    console.timeEnd('iframeLoad'); // End iframe load timer
    console.log('[Perf] handleIframeLoad called');
    setIsIframeLoaded(true);
    adjustIframeHeight();
  };

  // Function to adjust iframe height based on content
  const adjustIframeHeight = () => {
    console.log('[Perf] adjustIframeHeight called');
    if (iframeRef.current && iframeRef.current.contentWindow && iframeRef.current.contentWindow.document.body) {
      console.time('adjustIframeHeightCalculation');
      const height = iframeRef.current.contentWindow.document.body.scrollHeight;
      console.log(`[Perf] Calculated iframe height: ${height}px`);
      setIframeHeight(`${height}px`);
      console.timeEnd('adjustIframeHeightCalculation');
    } else {
      console.warn('[Perf] adjustIframeHeight: iframe content not ready');
    }
  };

  // Effect to reset iframe loaded state and height when email changes or view toggles
  useEffect(() => {
    console.log('[Perf] Email or showText changed, resetting iframe state.');
    setIsIframeLoaded(false);
    setIframeHeight('auto'); // Reset height for loading indicator
  }, [email, showText]);


  // Performance logging for srcDoc generation and sanitization
  console.time('srcDocPreparation');
  const originalHtml = email.html || '';

  // --- Start Sanitization ---
  console.time('DOMPurifySanitize');
  const sanitizedHtml = DOMPurify.sanitize(originalHtml, {
      USE_PROFILES: { html: true }, // Ensure we allow standard HTML tags
      // FORBID_TAGS: ['style'], // Example: remove style tags completely if needed
      FORBID_ATTR: ['style'] // Remove inline style attributes
  });
  console.timeEnd('DOMPurifySanitize');
  // --- End Sanitization ---

  // Inject CSS for basic styling and dark mode support
  const injectedCss = `
    <style>
      body {
        font-family: sans-serif;
        margin: 10px; /* Add some margin */
        padding: 0;
        overflow: hidden; /* Prevent double scrollbars initially */
        color: #333; /* Default text color */
        background-color: #fff; /* Default background */
      }
      body.dark-mode {
         color: #eee; /* Light text for dark mode */
         background-color: #121212; /* Dark background for dark mode */
      }
      img { max-width: 100%; height: auto; } /* Basic responsive images */
      /* Add more styles as needed */
       /* Ensure the inner body allows scrolling */
       html, body {
            height: 100%;
            margin: 0;
            padding: 0;
            overflow-y: auto; /* Enable scrolling ONLY on the body */
        }
    </style>
  `;

  // Determine if the system prefers dark mode
  const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const bodyClass = prefersDarkMode ? 'dark-mode' : '';


  // Construct the srcDoc content with sanitized HTML
  const srcDocContent = `
    <html>
      <head>
        ${injectedCss}
      </head>
      <body class="${bodyClass}">
        ${sanitizedHtml}
        <script>
          // Adjust height after images load or content changes dynamically
          const adjustHeight = () => {
            window.parent.postMessage({ type: 'iframeHeight', height: document.body.scrollHeight }, '*');
          };
          window.onload = adjustHeight; // Initial adjustment
          const observer = new MutationObserver(adjustHeight);
          observer.observe(document.body, { childList: true, subtree: true, attributes: true });
          // Also adjust height after images load
          document.querySelectorAll('img').forEach(img => {
            img.onload = adjustHeight;
            if (img.complete) { // Handle cached images
                //adjustHeight(); // Avoid calling too often initially?
            }
          });
           // Forward scroll events to parent
           window.addEventListener('scroll', (event) => {
                // We might not need this if overflowY: 'auto' on body works well
           });
            // Listen for dark mode changes
          window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
            document.body.classList.toggle('dark-mode', event.matches);
          });
        </script>
      </body>
    </html>
  `;
  console.timeEnd('srcDocPreparation');


  // Effect to set srcDoc after a short delay to allow spinner rendering
  useEffect(() => {
    if (!showText) {
      console.log('[Perf] Scheduling srcDoc update');
      const timer = setTimeout(() => {
        console.log('[Perf] Setting srcDoc in setTimeout');
        console.time('iframeLoad'); // Start iframe load timer *before* setting srcDoc
        setCurrentSrcDoc(srcDocContent);
      }, 0); // Delay of 0ms allows browser to potentially render UI updates

      return () => clearTimeout(timer); // Cleanup timer on unmount or change
    } else {
        setCurrentSrcDoc(undefined); // Clear srcDoc when switching to text view
    }
    // Dependencies: srcDocContent changes when email changes. showText toggles view.
  }, [srcDocContent, showText]);

  // Effect to listen for height messages from iframe
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data && event.data.type === 'iframeHeight') {
        console.log(`[Perf] Received iframeHeight message: ${event.data.height}px`);
        // Add a small buffer to prevent scrollbar flickering in some cases
        setIframeHeight(`${event.data.height + 5}px`);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []); // Empty dependency array means this runs once on mount

  const toggleView = () => {
    setShowText(!showText);
  };


  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' /* Parent controls scroll */ }}>
      {/* Header with Subject and Toggle Button */}
      <Box sx={{ padding: 2, borderBottom: '1px solid #ddd', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <Typography variant="h6" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {email.subject || 'No Subject'}
        </Typography>
        <IconButton onClick={toggleView} size="small">
          {showText ? 'HTML' : 'Text'} {/* Toggle button text */}
        </IconButton>
      </Box>

      {/* Content Area */}
      <Box sx={{
          flexGrow: 1, // Takes remaining space
          position: 'relative', // Needed for positioning the loading indicator
          overflowY: 'auto', // Make this container scrollable
          minHeight: 0, // Crucial for flexbox scrolling
      }}>
        {/* Loading Indicator */}
        {!isIframeLoaded && !showText && (
            <Box sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'rgba(255, 255, 255, 0.8)', // Optional: semi-transparent overlay
                zIndex: 1, // Ensure it's above the iframe before it loads
            }}>
                <CircularProgress />
            </Box>
        )}

        {/* Iframe or Text Content */}
        {showText ? (
          <Box sx={{ padding: 2, whiteSpace: 'pre-wrap', wordBreak: 'break-word', height: '100%' }}>
            <Typography variant="body1">{email.text || 'No text content available.'}</Typography>
          </Box>
        ) : (
          <iframe
            ref={iframeRef}
            sandbox="allow-same-origin allow-scripts" // Keep allow-scripts for height adjustment script, but be cautious
            srcDoc={currentSrcDoc}
            onLoad={handleIframeLoad}
            style={{
              width: '100%',
              height: iframeHeight, // Dynamically set height
              border: 'none',
              display: 'block', // Prevent potential extra space below iframe
              visibility: isIframeLoaded ? 'visible' : 'hidden', // Hide iframe until loaded
            }}
            title="Email Content"
          />
        )}
      </Box>
    </Box>
  );
};

export default EmailContent; 