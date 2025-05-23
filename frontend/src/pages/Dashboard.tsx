import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Button,
  Avatar,
  Divider,
  IconButton,
  CircularProgress,
  TextField,
  Alert,
} from '@mui/material';
import {
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  Refresh as RefreshIcon,
  Archive as ArchiveIcon,
} from '@mui/icons-material';
import { AISuggestions } from '../components/AISuggestions';
import EmailList from '../components/EmailList';
import EmailDetail from '../components/EmailContent';
import { useAuth } from '../contexts/AuthContext';
import {
  getEmails,
  regenerateSuggestions,
  archiveEmail,
  EmailListItem,
  PaginatedEmailsResponse,
  AISuggestion,
  updateAiSuggestion,
  getEmailDetail,
  EmailDetailData,
} from '../services/api';
import { useQueryClient } from '@tanstack/react-query';
import { useEmailStore } from '../stores/emailStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { queryKeys } from '../lib/queryKeys';
import {
  EmailAccount,
  emailAccounts,
  FolderItem,
  EmailDetail as EmailDetailType,
  setNotificationPreference as apiSetNotificationPreference,
  getNotificationPreference as apiGetNotificationPreference,
} from '../services/api';

const LOCAL_STORAGE_KEY = 'selectedEmailId';
const EMAILS_PAGE_SIZE = 30; // Number of emails to load per page

// Helper function to load/save selected email ID
const LOCAL_STORAGE_SELECTED_EMAIL_ID = 'selectedEmailId';
const loadSelectedEmailId = (): number | null => {
  const stored = localStorage.getItem(LOCAL_STORAGE_SELECTED_EMAIL_ID);
  // console.log(`[Dashboard] Loaded selected email ID from localStorage: ${stored}`);
  return stored ? parseInt(stored, 10) : null;
};
const saveSelectedEmailId = (id: number | null) => {
  if (id === null) {
    // console.log("[Dashboard] Removed selected email ID from localStorage");
    localStorage.removeItem(LOCAL_STORAGE_SELECTED_EMAIL_ID);
  } else {
    // console.log(`[Dashboard] Saved selected email ID to localStorage: ${id}`);
    localStorage.setItem(LOCAL_STORAGE_SELECTED_EMAIL_ID, id.toString());
  }
};

console.log('[Dashboard] Datei geladen, Komponente wird initialisiert...');

export const Dashboard: React.FC = () => {
  console.log('[Dashboard] Render START');
  const { user, isAuthenticated, token } = useAuth();
  const queryClient = useQueryClient();
  const setSelectedEmailIdStore = useEmailStore((state) => state.setSelectedEmailId);
  const clearSelectedEmailStore = useEmailStore((state) => state.clearSelectedEmail);
  const setEmailDetailStore = useEmailStore((state) => state.setEmailDetail);
  const incrementFetchCounter = useEmailStore(state => state.incrementFetchCounter);
  const selectedFolder = useEmailStore((state) => state.selectedFolder);
  const selectedAccountId = useEmailStore((state) => state.selectedAccountId);
  const clearAllEmailActions = useEmailStore((state) => state.clearAllEmailActions);

  const [emails, setEmails] = useState<EmailListItem[]>([]);
  const [currentSelectedEmailIdValue, setCurrentSelectedEmailIdValue] = useState<number | null>(null);
  const [loadingEmails, setLoadingEmails] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalEmails, setTotalEmails] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [isFindingStoredEmail, setIsFindingStoredEmail] = useState<boolean>(false);
  const [subsequentSearchFailed, setSubsequentSearchFailed] = useState<boolean>(false);
  const LOCAL_STORAGE_PANEL_EXPANDED = 'suggestionPanelExpanded';
  const [suggestionPanelExpanded, setSuggestionPanelExpanded] = useState<boolean>(() => {
    const stored = localStorage.getItem(LOCAL_STORAGE_PANEL_EXPANDED);
    return stored === null ? false : stored === 'true';
  });
  const suggestionsPanelRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // State, um das Neuladen von EmailDetail zu erzwingen
  const [emailDetailKey, setEmailDetailKey] = useState<number>(0);

  const [currentEmailDetail, setCurrentEmailDetail] = useState<EmailDetailData | null>(null);
  const [loadingEmailDetail, setLoadingEmailDetail] = useState<boolean>(false);
  const [errorEmailDetail, setErrorEmailDetail] = useState<string | null>(null);

  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);

  const targetEmailIdToRestoreRef = useRef<number | null>(null);

  const [initialLoadComplete, setInitialLoadComplete] = useState<boolean>(false);

  // Centralized function to set and save the selected email ID
  const setSelectedEmailId = useCallback((id: number | null) => {
    const currentValue = currentSelectedEmailIdValue; // Capture current value for comparison
    console.log(`%c[setSelectedEmailId] CALLED WITH ID: ${id}. Current value was: ${currentValue}`, 'color: magenta; font-weight: bold;'); // === ADDED LOG ===
    // console.trace("setSelectedEmailId called from:"); // Optional: uncomment for stack trace
    if (id !== currentValue) { // Only update if the ID actually changes
        // console.log(`[setSelectedEmailId] ID changed from ${currentValue} to ${id}. Updating state and storage.`);
        setCurrentSelectedEmailIdValue(id);
        saveSelectedEmailId(id);
    } else {
        // console.log(`[setSelectedEmailId] ID ${id} is the same as current. Skipping state update and storage.`);
    }
    // Added currentValue dependency to ensure the comparison inside uses the latest value
  }, [setCurrentSelectedEmailIdValue, currentSelectedEmailIdValue]); 

  const handleExpandPanelRequest = useCallback(() => {
    console.log(`[Dashboard] Expand panel requested by AISuggestions.`);
    if (!suggestionPanelExpanded) {
        setSuggestionPanelExpanded(true);
    }
  }, [suggestionPanelExpanded]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
        const target = event.target as Node;

        // Prüfe, ob der Klick außerhalb des Panels war UND NICHT innerhalb eines MUI Menüs/Popovers
        const isClickInsidePanel = suggestionsPanelRef.current && suggestionsPanelRef.current.contains(target);
        const isClickInsideMuiMenu = (target instanceof Element) && target.closest('.MuiMenu-root, .MuiPopover-root');

        if (!isClickInsidePanel && !isClickInsideMuiMenu) {
            console.log("[Dashboard] Click truly outside detected (not panel, not menu), collapsing suggestions panel.");
            setSuggestionPanelExpanded(false);
        } else {
            // Optional: Logge, warum nicht kollabiert wird
            // console.log(`[Dashboard] Click detected, but not collapsing. Inside panel: ${isClickInsidePanel}, Inside menu: ${!!isClickInsideMuiMenu}`);
        }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Escape') {
             console.log("[Dashboard] Escape key pressed, collapsing suggestions panel.");
            setSuggestionPanelExpanded(false);
        }
    };

    if (suggestionPanelExpanded) {
        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('keydown', handleKeyDown);
        console.log("[Dashboard] Added listeners for click outside / Esc key.");
    }

    return () => {
        document.removeEventListener('mousedown', handleClickOutside);
        document.removeEventListener('keydown', handleKeyDown);
    };
  }, [suggestionPanelExpanded]);

  const clearAndFetchEmails = useCallback(async (folder: string | null, accountId: number | 'all') => {
    // console.log(`[Dashboard] Clearing and fetching emails for folder: ${folder}, account: ${accountId}`);
    setEmails([]);
    setCurrentPage(1);
    setHasMore(false); // Reset hasMore
    setSubsequentSearchFailed(false); // Reset search failed state
    setEmailError(null);
    setIsFindingStoredEmail(false); // Reset search state

    if (folder) {
      await fetchEmailBatch(1, folder, accountId);
    } else {
      setLoadingEmails(false);
    }
  }, []);

  const fetchEmailBatch = useCallback(async (page: number, folderToFetch?: string, accountToFetch?: number | 'all') => {
    console.log('[Dashboard] fetchEmailBatch START', { page, folderToFetch, accountToFetch });
    const effectiveFolder = folderToFetch || selectedFolder;
    const effectiveAccount = accountToFetch ?? selectedAccountId;

    if (!effectiveFolder) {
      // console.log("[fetchEmailBatch] No folder, aborting.");
      setLoadingEmails(false);
      setHasMore(false);
      return;
    }
    // console.log(`[fetchEmailBatch] Fetching page ${page} for folder '${effectiveFolder}', account '${effectiveAccount}'`);
    setLoadingEmails(true);
    if (page === 1) setEmailError(null); // Reset error only for the first page of a new list

    try {
      const response = await getEmails({ page, limit: EMAILS_PAGE_SIZE, folder: effectiveFolder, account: effectiveAccount });
      console.log('[Dashboard] fetchEmailBatch SUCCESS', response);
      // console.log(`[fetchEmailBatch] Response for page ${page}: ${response.results.length} items, hasMore: ${response.next !== null}`);
      setEmails(prevEmails => page === 1 ? response.results : [...prevEmails, ...response.results]);
      setTotalEmails(response.count);
      setHasMore(response.next !== null);
      setCurrentPage(page);
      if (page === 1) {
        setInitialLoadComplete(true);
      }
    } catch (err) {
      console.error('[Dashboard] fetchEmailBatch ERROR:', err);
      setEmailError('Failed to load emails.');
      setHasMore(false);
      setInitialLoadComplete(true);
      if (targetEmailIdToRestoreRef.current) {
        // console.log(`[fetchEmailBatch] Error during restoration for ${targetEmailIdToRestoreRef.current}. Clearing target.`);
        targetEmailIdToRestoreRef.current = null;
      }
    } finally {
      setLoadingEmails(false);
      console.log('[Dashboard] fetchEmailBatch FINALLY: setLoadingEmails(false) executed.');
    }
  }, [selectedFolder, selectedAccountId]);

  // Effect for initializing and handling folder/account changes
  useEffect(() => {
    console.log('[Dashboard] useEffect: selectedFolder/selectedAccountId geändert:', selectedFolder, selectedAccountId);
    const folderToLoad = selectedFolder || 'INBOX';
    // console.log(`[FolderEffect] Folder: '${folderToLoad}', Account: '${selectedAccountId}'`);

    setEmails([]);
    setCurrentPage(1);
            setHasMore(false);
    setEmailError(null);
    setInitialLoadComplete(false);

    const storedId = loadSelectedEmailId();
    targetEmailIdToRestoreRef.current = storedId;
    // console.log(`%c[FolderEffect] Target ID to restore REF SET TO: ${targetEmailIdToRestoreRef.current}`, 'color: yellow; font-weight: bold;');

    // Clear visual selection from previous folder immediately, WITHOUT saving null to localStorage.
    setCurrentSelectedEmailIdValue(null); // Use the direct setter

    fetchEmailBatch(1, folderToLoad, selectedAccountId);

  }, [selectedFolder, selectedAccountId]); // fetchEmailBatch removed previously

  // Main effect for restoring selected email ID or selecting default after emails load
  useEffect(() => {
    console.log('[Dashboard] useEffect: emails/initialLoadComplete/hasMore/selectedFolder/selectedAccountId:', { emails, initialLoadComplete, hasMore, selectedFolder, selectedAccountId });
    // console.log(`%c[RestoreSelectionEffect] === HOOK ENTRY === InitialLoadComplete: ${initialLoadComplete}, Loading: ${loadingEmails}, Target: ${targetEmailIdToRestoreRef.current}, Emails: ${emails.length}`, 'color: cyan; font-weight: bold;');

    // Wait until the initial load (page 1) is complete AND loading is finished
    if (!initialLoadComplete || loadingEmails) {
       // console.log("[RestoreSelectionEffect] Waiting (Initial load not complete OR emails are loading)");
            return; 
        }
    // console.log(`%c[RestoreSelectionEffect] Proceeding past loading check & initial load complete.`, 'color: lightgreen; font-weight: bold;');

    const targetId = targetEmailIdToRestoreRef.current;

    if (targetId !== null) {
      // console.log(`[RestoreSelectionEffect] Attempting to restore target ID: ${targetId}`);
      const emailInList = emails.find(email => email.id === targetId);

      if (emailInList) {
        // Found the target ID!
        // console.log(`[RestoreSelectionEffect] Target ID ${targetId} found. Selecting.`);
        setSelectedEmailId(targetId);
        targetEmailIdToRestoreRef.current = null; // Mark restoration as complete
                                } else {
        // Target ID not found in the currently loaded emails. Decide whether to fetch more or give up.
        if (hasMore) {
           // console.log(`[RestoreSelectionEffect] Target ${targetId} not in list, hasMore=true. Fetching page ${currentPage + 1}.`);
           // Avoid infinite loops if API keeps saying hasMore but doesn't return the email
           const MAX_RESTORATION_PAGES = 10; // Example limit
           if (currentPage < MAX_RESTORATION_PAGES) {
                if (!loadingEmails) { // Re-check loading status
                    fetchEmailBatch(currentPage + 1, selectedFolder, selectedAccountId);
                }
           } else {
                // console.warn(`[RestoreSelectionEffect] Reached page limit (${MAX_RESTORATION_PAGES}) trying to restore ${targetId}. Giving up.`);
                targetEmailIdToRestoreRef.current = null; // Stop search
                if (currentSelectedEmailIdValue === null) { // Select default only if nothing ended up selected
                    setSelectedEmailId(emails.length > 0 ? emails[0].id : null);
                }
            }
        } else {
           // Target ID not found AND no more pages. Search definitively failed.
           // This condition should only be met *after* at least one batch of emails has loaded and confirmed !hasMore.
           // console.log(`[RestoreSelectionEffect] Target ${targetId} not found, and !hasMore. Search failed for this target.`);
           targetEmailIdToRestoreRef.current = null;
           if (currentSelectedEmailIdValue === null) { // Select default only if nothing ended up selected
                setSelectedEmailId(emails.length > 0 ? emails[0].id : null);
           }
        }
      }
    } else {
      // No target ID to restore. Select default if needed.
      // This should only run if localStorage was initially empty OR restoration is complete/failed.
      if (currentSelectedEmailIdValue === null && emails.length > 0) {
        // console.log("[RestoreSelectionEffect] No target ID, no current selection. Selecting first email.");
        setSelectedEmailId(emails[0].id);
      }
    }
  }, [
    emails,
    loadingEmails,
    hasMore,
    currentPage,
    currentSelectedEmailIdValue,
    selectedFolder,
    selectedAccountId,
    fetchEmailBatch,
    setSelectedEmailId,
    initialLoadComplete,
  ]);

  // Effect to fetch email detail when currentSelectedEmailIdValue changes
  useEffect(() => {
    console.log('[Dashboard] useEffect: currentSelectedEmailIdValue geändert:', currentSelectedEmailIdValue);
    if (currentSelectedEmailIdValue !== null) {
      // console.log(`[EmailDetailEffect] selectedEmailId (internal) changed to ${currentSelectedEmailIdValue}. Fetching details.`);
      setLoadingEmailDetail(true);
      setErrorEmailDetail(null);
      getEmailDetail(currentSelectedEmailIdValue)
        .then((data) => {
          setCurrentEmailDetail(data);
        })
        .catch((err) => {
          console.error(`[EmailDetailEffect] Error for ${currentSelectedEmailIdValue}:`, err);
          setErrorEmailDetail('Failed to load email details.');
          setCurrentEmailDetail(null);
        })
        .finally(() => setLoadingEmailDetail(false));
    } else {
      setCurrentEmailDetail(null);
    }
  }, [currentSelectedEmailIdValue]); // Depends on the internal selectedEmailId state

  // --- Event Handlers ---
  const handleSelectEmail = useCallback((id: number | null) => {
    // console.log(`[handleSelectEmail] User selected: ${id}`);
    targetEmailIdToRestoreRef.current = null; // User interaction overrides restoration target
    setSelectedEmailId(id);
    // setSuggestionPanelExpanded(false); // Assuming this is UI logic
  }, [setSelectedEmailId]);

  const handleLoadMore = useCallback(() => {
    if (!loadingEmails && hasMore) {
      // console.log(`[handleLoadMore] Fetching page ${currentPage + 1}`);
      fetchEmailBatch(currentPage + 1, selectedFolder, selectedAccountId);
    }
  }, [loadingEmails, hasMore, currentPage, selectedFolder, selectedAccountId, fetchEmailBatch]);

  const handleArchive = useCallback(async (emailIdToArchive: number) => {
    // console.log('[Archive] Requested for:', emailIdToArchive);
    const originalEmails = [...emails];
    const emailIndex = originalEmails.findIndex(e => e.id === emailIdToArchive);
    setEmails(prevEmails => prevEmails.filter(email => email.id !== emailIdToArchive));
    try {
      await archiveEmail(emailIdToArchive);
      if (currentSelectedEmailIdValue === emailIdToArchive) {
        let nextSelectedId: number | null = null;
        const remainingEmails = emails.filter(e => e.id !== emailIdToArchive);
        if (remainingEmails.length > 0) {
          if (emailIndex >= 0 && emailIndex < remainingEmails.length) {
            nextSelectedId = remainingEmails[emailIndex]?.id ?? null;
          } else if (remainingEmails.length > 0) {
            nextSelectedId = remainingEmails[remainingEmails.length - 1]?.id ?? null;
            } 
        }
        targetEmailIdToRestoreRef.current = null; // Clear restoration target
        setSelectedEmailId(nextSelectedId);
      }
    } catch (error) {
      console.error(`[Archive] Failed for ${emailIdToArchive}:`, error);
      setEmails(originalEmails);
    }
  }, [currentSelectedEmailIdValue, emails, setSelectedEmailId, selectedFolder, selectedAccountId /* for consistency if used by archive directly */]);

  const handleRefreshSuggestions = useCallback(async (emailId: number) => {
    console.log('[Dashboard] ASYNC Refresh suggestions requested for email:', emailId);
    setLoadingEmailDetail(true);
    setErrorEmailDetail(null);
    try {
      await regenerateSuggestions(emailId);
      console.log('[Dashboard] ASYNC Suggestion regeneration successfully queued. Starte Polling...');
      // Polling bis Suggestions da sind (max. 20s)
      let elapsed = 0;
      const interval = 2000;
      const maxTime = 20000;
      let found = false;
      while (elapsed < maxTime && !found) {
        await new Promise(res => setTimeout(res, interval));
        elapsed += interval;
        const detail = await getEmailDetail(emailId);
        if (detail.suggestions && detail.suggestions.length > 0) {
          setCurrentEmailDetail(detail);
          found = true;
        }
      }
      setLoadingEmailDetail(false);
    } catch (error) {
      console.error(`[Dashboard] Failed to QUEUE suggestion regeneration for ${emailId}:`, error);
      setErrorEmailDetail(`Failed to start suggestion generation. ${error instanceof Error ? error.message : 'Please try again.'}`);
      setLoadingEmailDetail(false);
    }
  }, []);

  const handleUpdateSuggestion = useCallback(async (
      suggestionId: string, 
      updatedData: Partial<Pick<AISuggestion, 'content' | 'suggested_subject'>>
  ) => {
      console.log(`[Dashboard] Update requested for suggestion ${suggestionId}:`, updatedData);
      try {
          const updatedSuggestion = await updateAiSuggestion(suggestionId, updatedData);
          
          setCurrentEmailDetail(prevSuggestions => 
              prevSuggestions && prevSuggestions.suggestions
                ? { ...prevSuggestions, suggestions: prevSuggestions.suggestions.map(suggestion => 
                  suggestion.id === suggestionId 
                      ? { ...suggestion, ...updatedSuggestion }
                      : suggestion
                  ) }
                : prevSuggestions
          );
          console.log(`[Dashboard] Suggestion ${suggestionId} updated locally.`);

      } catch (error) {
          console.error(`[Dashboard] Failed to update suggestion ${suggestionId}:`, error);
          setErrorEmailDetail(`Failed to save changes for suggestion. ${error instanceof Error ? error.message : 'Please try again.'}`);
      }
  }, []);

  // Handler zum sofortigen Entfernen aus der lokalen Liste
  const handleDeleteEmail = useCallback((id: number) => {
    setEmails(prevEmails => {
      const emailIndex = prevEmails.findIndex(e => e.id === id);
      const newEmails = prevEmails.filter(e => e.id !== id);
      // Wenn die gelöschte E-Mail selektiert war, wähle die nächste/andere
      if (currentSelectedEmailIdValue === id) {
        let nextSelectedId: number | null = null;
        if (newEmails.length > 0) {
          if (emailIndex >= 0 && emailIndex < newEmails.length) {
            nextSelectedId = newEmails[emailIndex]?.id ?? null;
          } else {
            nextSelectedId = newEmails[newEmails.length - 1]?.id ?? null;
          }
        }
        setSelectedEmailId(nextSelectedId);
      }
      return newEmails;
    });
  }, [currentSelectedEmailIdValue, setSelectedEmailId]);

  // WebSocket für E-Mail-Events (email.refresh)
  useEffect(() => {
    if (!isAuthenticated || !token) {
      console.warn('[Dashboard GENERAL WS] Kein Token oder nicht authentifiziert, WebSocket wird nicht aufgebaut.');
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }
    let isActive = true;
    const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsHost = import.meta.env.VITE_WS_BASE_URL || `${window.location.hostname}:8000`;
    const wsUrl = `${wsScheme}://${wsHost}/ws/general/?token=${token}`;
    console.log('[Dashboard GENERAL WS] Connecting to', wsUrl);
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;
    socket.onopen = () => {
      if (!isActive) return;
      console.log('[Dashboard GENERAL WS] WebSocket connected.');
    };
    socket.onmessage = (event) => {
      if (!isActive) return;
      console.log('[Dashboard GENERAL WS] WebSocket Nachricht empfangen:', event.data);
      try {
        const message = JSON.parse(event.data);
        console.log('[Dashboard GENERAL WS] Parsed message:', message);
        // --- Hole aktuelle Werte direkt aus dem Store ---
        const folder = useEmailStore.getState().selectedFolder || 'INBOX';
        const accountId = useEmailStore.getState().selectedAccountId ?? 'all';
        const eventType = message.type;
        if (eventType === 'email.refresh' || eventType === 'email_new' || eventType === 'email.new') {
          console.log('[Dashboard GENERAL WS] Event empfangen... E-Mail-Liste wird neu geladen. Typ:', eventType, 'selectedFolder:', folder, 'selectedAccountId:', accountId);
          fetchEmailBatch(1, folder, accountId);
          console.log('[Dashboard GENERAL WS] fetchEmailBatch wurde aufgerufen.');
        } else {
          console.log('[Dashboard GENERAL WS] Unbehandeltes Event empfangen:', message);
        }
      } catch (err) {
        console.error('[Dashboard GENERAL WS] Fehler beim Parsen der Nachricht:', err, event.data);
      }
    };
    socket.onerror = (err) => {
      if (!isActive) return;
      console.error('[Dashboard GENERAL WS] WebSocket Fehler:', err);
    };
    socket.onclose = (event) => {
      if (!isActive) return;
      console.warn('[Dashboard GENERAL WS] WebSocket Verbindung geschlossen:', event);
      wsRef.current = null;
    };
    return () => {
      isActive = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isAuthenticated, token, selectedFolder, selectedAccountId]);

  // Speichere Panel-Status bei Änderung
  useEffect(() => {
    localStorage.setItem(LOCAL_STORAGE_PANEL_EXPANDED, suggestionPanelExpanded ? 'true' : 'false');
  }, [suggestionPanelExpanded]);

  console.log('[Dashboard] Render END');
  return (
    <Box sx={{ display: 'flex', width: '100%', height: 'calc(100vh - 64px)', overflow: 'hidden', bgcolor: 'background.default', margin: 0, padding: 0 }}>
        {/* <div style={{ padding: '20px', color: 'white' }}>Dashboard Component Rendered - Test</div> */}

       <Box sx={{ width: suggestionPanelExpanded ? '60px' : '300px', minWidth: suggestionPanelExpanded ? '60px' : '300px', flexShrink: 0, borderRight: '1px solid', borderColor: 'divider', overflowY: 'auto', overflowX: 'hidden', bgcolor: 'background.paper', display: 'flex', flexDirection: 'column', transition: (theme) => theme.transitions.create(['width', 'min-width'], { duration: theme.transitions.duration.enteringScreen, easing: theme.transitions.easing.easeInOut }) }}>
        <EmailList
          emails={emails}
           selectedEmailId={currentSelectedEmailIdValue}
          onSelectEmail={handleSelectEmail}
          onLoadMore={handleLoadMore}
          hasMore={hasMore}
           loadingMore={loadingEmails && currentPage > 1} // Show loadingMore only if not on first page
          isCollapsed={suggestionPanelExpanded}
        />
      </Box>

       <Box sx={{ flexGrow: 1, width: 'auto', overflow: 'auto', height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'grey.900', transition: (theme) => theme.transitions.create(['margin-left', 'margin-right'], { duration: theme.transitions.duration.enteringScreen, easing: theme.transitions.easing.easeInOut }) }}>
         {currentSelectedEmailIdValue !== null ? (
          <EmailDetail 
            key={emailDetailKey} 
            emailDetail={currentEmailDetail} 
            loading={loadingEmailDetail} 
            error={errorEmailDetail} 
          />
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
             {emailError && <Alert severity="error">{emailError}</Alert>}
             {!emailError && !loadingEmails && emails.length === 0 && (
                 <Typography variant="h6" color="text.secondary">No emails to display.</Typography>
             )}
              {!emailError && loadingEmails && emails.length === 0 && (
                 <Typography variant="h6" color="text.secondary">Loading emails...</Typography>
             )}
             {!emailError && !loadingEmails && emails.length > 0 && currentSelectedEmailIdValue === null && (
                  <Typography variant="h6" color="text.secondary">Select an email to view details.</Typography>
             )}
            </Box>
          )}
      </Box>

       <Box ref={suggestionsPanelRef} sx={{ width: suggestionPanelExpanded ? '50%' : '300px', minWidth: suggestionPanelExpanded ? '400px' : '300px', maxWidth: '60%', flexShrink: 0, height: 'calc(100vh - 64px)', borderLeft: '1px solid', borderColor: 'divider', display: 'flex', flexDirection: 'column', transition: (theme) => theme.transitions.create(['width', 'min-width', 'max-width'], { duration: theme.transitions.duration.enteringScreen, easing: theme.transitions.easing.easeInOut }), overflow: 'hidden', bgcolor: 'background.paper' }}>
        <AISuggestions
           selectedEmailId={currentSelectedEmailIdValue}
          currentEmailDetail={currentEmailDetail}
          loading={loadingEmailDetail}
          error={errorEmailDetail}
          onArchive={handleArchive}
          onRefreshSuggestions={handleRefreshSuggestions}
          onExpandRequest={handleExpandPanelRequest}
          isExpanded={suggestionPanelExpanded}
          onUpdateSuggestion={handleUpdateSuggestion}
          onDeleteEmail={handleDeleteEmail}
        />
      </Box>
    </Box>
  );
};

export default Dashboard; 