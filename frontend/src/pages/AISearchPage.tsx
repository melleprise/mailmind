import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Grid,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  CircularProgress,
  Alert,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import { Stack } from '@mui/system';

import { api, emailAccounts, EmailListItem, EmailDetailData, getEmails, getEmailDetail, suggestFolderStructure, FolderStructureSuggestion, EmailAccount } from '../services/api';
import { EmailList } from '../components/EmailList';
import { EmailDetail } from '../components/EmailContent';
import SuggestionTreeView from '../components/SuggestionTreeView';

// --- Helper function to get all paths ---
const getAllFolderPaths = (structure: FolderStructureSuggestion | null, currentPath = ''): string[] => {
  if (!structure) return [];
  let paths: string[] = [];
  Object.entries(structure).forEach(([key, value]) => {
    const nodePath = currentPath ? `${currentPath}/${key}` : key;
    paths.push(nodePath);
    if (value && typeof value === 'object' && Object.keys(value).length > 0) {
      paths = paths.concat(getAllFolderPaths(value as FolderStructureSuggestion, nodePath));
    }
  });
  return paths;
};
// --- End Helper Function ---

const AISearchPage: React.FC = () => {
  const [folders, setFolders] = useState<string[]>([]);
  const [loadingFolders, setLoadingFolders] = useState(false);
  const [folderError, setFolderError] = useState<string | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);

  const [emails, setEmails] = useState<EmailListItem[]>([]);
  const [loadingEmails, setLoadingEmails] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMoreEmails, setHasMoreEmails] = useState(false);
  
  const [selectedEmailId, setSelectedEmailId] = useState<number | null>(null);

  const [loadingSuggestion, setLoadingSuggestion] = useState(false);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);
  const [suggestedStructure, setSuggestedStructure] = useState<FolderStructureSuggestion | null>(null);
  const [isSuggestionDialogOpen, setIsSuggestionDialogOpen] = useState(false);
  const [selectedFoldersToCreate, setSelectedFoldersToCreate] = useState<string[]>([]);
  const [initialExpandedNodes, setInitialExpandedNodes] = useState<string[]>([]);
  const [creatingFolders, setCreatingFolders] = useState(false);
  const [createFoldersError, setCreateFoldersError] = useState<string | null>(null);
  const [createFoldersSuccess, setCreateFoldersSuccess] = useState<string | null>(null);

  const placeholderAccountId: number | null = null;
  const { selectedAccountId = placeholderAccountId } = {};

  const [userEmailAccounts, setUserEmailAccounts] = useState<EmailAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [selectedAccountIdForView, setSelectedAccountIdForView] = useState<number | string>('all');

  const [selectedTargetAccountId, setSelectedTargetAccountId] = useState<number | string>('');

  const fetchFolderPathsForAccount = useCallback(async (accountId: number, accountName: string): Promise<string[]> => {
    console.log(`[AISearchPage] Fetching folders for account ID: ${accountId} (${accountName})`);
    const response = await emailAccounts.getFolders(accountId);
    
    if (response.data && Array.isArray(response.data.folders)) {
        
        // Filtere leere/null Strings UND [Gmail]/All Mail heraus
        const validFolderPaths = response.data.folders.filter((folderPath: any) => 
            folderPath && 
            typeof folderPath === 'string' && 
            folderPath.trim() !== '' &&
            folderPath !== '[Gmail]/All Mail' // Expliziter Ausschluss
        );

        const originalCount = response.data.folders.length;
        const filteredCount = originalCount - validFolderPaths.length;
        if (filteredCount > 0) {
          console.log(`[AISearchPage] Filtered ${filteredCount} invalid folder strings (empty/null or '[Gmail]/All Mail') for account ${accountId}.`);
        }
        
        return validFolderPaths;
    } else {
        console.warn(`[AISearchPage] Unexpected folder data structure received for account ${accountId}:`, response.data);
        throw new Error(`Unerwartete Ordnerdatenstruktur für Konto ${accountName} erhalten.`);
    }
  }, []);

  useEffect(() => {
    const fetchAllFolders = async () => {
      setLoadingFolders(true);
      setFolderError(null);
      setFolders([]);
      setSelectedFolder(null);
      setEmails([]);
      setSelectedEmailId(null);
      console.log('[AISearchPage] Fetching folders for ALL accounts.');
      try {
        const accountsResponse = await emailAccounts.list();
        if (!accountsResponse.data || !Array.isArray(accountsResponse.data)) {
          throw new Error('Konnte keine Kontenliste abrufen.');
        }
        const allAccountFolderPathsPromises = accountsResponse.data.map(account => 
          fetchFolderPathsForAccount(account.id, account.email || `Konto ${account.id}`)
            .catch(err => {
              console.error(`[AISearchPage] Error fetching folders for account ${account.id}:`, err);
              return [];
            })
        );
        const results = await Promise.all(allAccountFolderPathsPromises);
        const combinedFolderPaths = results.flat();
        const uniqueFolderPaths = Array.from(new Set(combinedFolderPaths));
        uniqueFolderPaths.sort();
        setFolders(uniqueFolderPaths);
        console.log(`[AISearchPage] All unique folders fetched successfully (${uniqueFolderPaths.length}):`, uniqueFolderPaths.slice(0, 10));
      } catch (error: any) { 
        console.error('[AISearchPage] Error fetching all folders:', error);
        setFolderError(`Fehler beim Laden aller Ordner: ${error.message || 'Unbekannter Fehler'}`);
        setFolders([]);
      } finally {
        setLoadingFolders(false);
      }
    };

    const fetchSingleAccountFolders = async (accountId: number) => {
      setLoadingFolders(true);
      setFolderError(null);
      setFolders([]);
      setSelectedFolder(null);
      setEmails([]);
      setSelectedEmailId(null);
      console.log(`[AISearchPage] Fetching folders for single account ID: ${accountId}`);
       try {
        const accountName = `Konto ${accountId}`;
        const accountFolderPaths = await fetchFolderPathsForAccount(accountId, accountName);
        accountFolderPaths.sort();
        setFolders(accountFolderPaths);
        console.log(`[AISearchPage] Folders for account ${accountId} fetched successfully (${accountFolderPaths.length}):`, accountFolderPaths.slice(0,10));
      } catch (error: any) {
        console.error(`[AISearchPage] Error fetching folders for account ${accountId}:`, error);
        setFolderError(`Fehler beim Laden der Ordner für Konto ${accountId}: ${error.message || 'Unbekannter Fehler'}`);
        setFolders([]);
      } finally {
        setLoadingFolders(false);
      }
    };

    if (selectedAccountIdForView === 'all') {
      fetchAllFolders();
    } else if (typeof selectedAccountIdForView === 'number') {
      fetchSingleAccountFolders(selectedAccountIdForView);
    } else {
      setFolders([]);
      setSelectedFolder(null);
      setLoadingFolders(false);
      setFolderError(null);
      console.log('[AISearchPage] No specific account or "All Accounts" selected, clearing folders.');
    }
  }, [selectedAccountIdForView, fetchFolderPathsForAccount]);

  const fetchEmails = useCallback(async (folder: string, page: number) => {
    console.log(`[AISearchPage] Fetching emails for folder: ${folder}, page: ${page}`);
    setLoadingEmails(true);
    setEmailError(null);
    try {
      const response = await getEmails({ folderName: folder, page: page, limit: 30 });
      if (response && Array.isArray(response.results)) {
        setEmails(prevEmails => page === 1 ? response.results : [...prevEmails, ...response.results]);
        setCurrentPage(page);
        setHasMoreEmails(response.next !== null);
      } else {
        console.error("[AISearchPage] Unexpected data structure received from getEmails:", response);
        throw new Error('Unerwartete Datenstruktur für E-Mails empfangen.');
      }
    } catch (error: any) { 
      console.error(`[AISearchPage] Error fetching emails for folder ${folder}:`, error);
      setEmailError(`Fehler beim Laden der E-Mails: ${error.message || 'Unbekannter Fehler'}`);
      if(page === 1) setEmails([]); 
    } finally {
      setLoadingEmails(false);
    }
  }, []);

  useEffect(() => {
    if (selectedFolder) {
      console.log(`[AISearchPage] Selected folder changed to: ${selectedFolder}. Fetching emails.`);
      setEmails([]);
      setSelectedEmailId(null);
      setCurrentPage(1);
      setHasMoreEmails(false);
      fetchEmails(selectedFolder, 1);
    } else {
       setEmails([]);
       setSelectedEmailId(null);
       setCurrentPage(1);
       setHasMoreEmails(false);
       setEmailError(null);
    }
  }, [selectedFolder, fetchEmails]);

  const handleFolderSelect = (folderPath: string) => {
    setSelectedFolder(folderPath);
    setSelectedEmailId(null);
  };
  
  const handleEmailSelect = (id: number | null) => {
    setSelectedEmailId(id);
  };

  const handleLoadMoreEmails = () => {
    if (!loadingEmails && hasMoreEmails && selectedFolder) {
      fetchEmails(selectedFolder, currentPage + 1);
    }
  };
  
  const handleBackToList = () => {
      setSelectedEmailId(null);
  };

  useEffect(() => {
    const fetchAccounts = async () => {
      setLoadingAccounts(true);
      try {
        const response = await emailAccounts.list();
        setUserEmailAccounts(response.data || []);
      } catch (err) {
        console.error("Failed to fetch accounts", err);
        // Handle error appropriately
      } finally {
        setLoadingAccounts(false);
      }
    };
    fetchAccounts();
  }, []);

  const handleSuggestFolders = async () => {
    setLoadingSuggestion(true);
    setSuggestionError(null);
    setSuggestedStructure(null);
    setSelectedFoldersToCreate([]);
    setInitialExpandedNodes([]);
    setCreateFoldersError(null);
    setCreateFoldersSuccess(null);
    console.log('[AISearchPage] Requesting folder structure suggestion...');
    try {
      const structure = await suggestFolderStructure();
      console.log('[AISearchPage] Received folder structure suggestion:', structure);
      if (Object.keys(structure).length === 0) {
          setSuggestionError("Die AI konnte keine Ordnerstruktur vorschlagen. Eventuell zu wenige oder zu ähnliche E-Mails?");
          setSuggestedStructure(null);
      } else {
          setSuggestedStructure(structure);
          const allPaths = getAllFolderPaths(structure);
          setSelectedFoldersToCreate(allPaths);
          setInitialExpandedNodes(allPaths);
          setIsSuggestionDialogOpen(true);
      }
    } catch (error: any) { 
      console.error('[AISearchPage] Error suggesting folder structure:', error);
      const message = error.response?.data?.detail || error.message || 'Ein unbekannter Fehler ist aufgetreten.';
      setSuggestionError(`Fehler beim Vorschlagen der Ordnerstruktur: ${message}`);
      setSuggestedStructure(null);
      setIsSuggestionDialogOpen(true);
    } finally {
      setLoadingSuggestion(false);
    }
  };

  const handleCloseSuggestionDialog = () => {
      setIsSuggestionDialogOpen(false);
  };

  const handleSelectAllFolders = () => {
    const allPaths = getAllFolderPaths(suggestedStructure);
    setSelectedFoldersToCreate(allPaths);
  };

  const handleDeselectAllFolders = () => {
    setSelectedFoldersToCreate([]);
  };

  const handleCreateSelectedFolders = async () => {
    const targetAccountId = selectedTargetAccountId;
    
    if (!targetAccountId) {
        setCreateFoldersError("Bitte wählen Sie zuerst ein E-Mail-Konto aus dem Dropdown aus.");
        return;
    }
    if (selectedFoldersToCreate.length === 0) {
        setCreateFoldersError("Bitte wählen Sie mindestens einen Ordner zum Erstellen aus.");
        return;
    }

    setCreatingFolders(true);
    setCreateFoldersError(null);
    setCreateFoldersSuccess(null);
    console.log(`[AISearchPage] Creating folders for account ${targetAccountId}:`, selectedFoldersToCreate);

    try {
      const response = await api.post(`/email-accounts/${targetAccountId}/create-folders/`, { 
        folder_paths: selectedFoldersToCreate 
      });

      console.log("[AISearchPage] Folder creation response:", response.data);
      const { created_count = 0, failed_count = 0, failed_folders = {} } = response.data || {};
      let successMsg = `Erfolgreich ${created_count} Ordner erstellt/gefunden.`;
      if (failed_count > 0) {
        successMsg += ` ${failed_count} Ordner konnten nicht erstellt werden.`;
        console.warn("Failed folders:", failed_folders);
        setCreateFoldersError(`Einige Ordner konnten nicht erstellt werden: ${Object.keys(failed_folders).join(', ')}`); 
      } else {
        setCreateFoldersError(null);
      }
      setCreateFoldersSuccess(successMsg);

    } catch (error: any) {
      console.error("[AISearchPage] Error creating folders:", error);
      const message = error.response?.data?.detail || error.response?.data?.folder_paths?.[0] || error.message || 'Unbekannter Fehler beim Erstellen der Ordner.';
      setCreateFoldersError(`Fehler: ${message}`);
      setCreateFoldersSuccess(null);
    } finally {
      setCreatingFolders(false);
    }
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
{/*      <Typography variant="h4" gutterBottom>
        AI Search & Organize Emails
      </Typography>
*/}
      {/* Account Selection Dropdown - Wieder auskommentiert */}
      {/*
      <Grid container spacing={2} sx={{ mb: 2 }}> 
        <Grid item xs={12} md={3}> 
          
          <FormControl fullWidth size="small"> 
            <InputLabel id="account-select-label">Email Account</InputLabel>
            <Select
              labelId="account-select-label"
              id="account-select"
              value={selectedAccountIdForView}
              label="Email Account"
              onChange={(e) => {
                const value = e.target.value;
                setSelectedAccountIdForView(value === 'all' ? 'all' : Number(value));
              }}
              disabled={loadingAccounts}
              
              MenuProps={{
                PaperProps: {
                  sx: {
                    minWidth: '350px', 
                    
                  },
                },
              }}
            >
              <MenuItem value="all">All Accounts</MenuItem>
              {loadingAccounts && <MenuItem disabled>Loading accounts...</MenuItem>}
              {userEmailAccounts.map((account) => (
                <MenuItem key={account.id} value={account.id}>
                  {account.name || account.email}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} md={9}></Grid> 
      </Grid>
      */}
      {/* Ende Account Selection Dropdown */}

      <Grid container spacing={2}>
        {/* Folder List */}
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 0, flexGrow: 1, overflowY: 'auto', mb: 1 }}>
            <Box sx={{ p: 1, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6" gutterBottom sx={{ fontSize: '1rem', mb: 0 }}>
                Ordner {selectedAccountIdForView === 'all' ? "(Alle Konten)" : selectedAccountIdForView ? `(${userEmailAccounts.find(acc => acc.id === selectedAccountIdForView)?.email || '...?'})` : "(Kein Konto)"}
              </Typography>
              <Tooltip title="Ordnerstruktur vorschlagen (AI)">
                <span>
                  <IconButton 
                    onClick={handleSuggestFolders} 
                    disabled={loadingSuggestion || loadingFolders}
                    size="small"
                  >
                    {loadingSuggestion ? <CircularProgress size={20} /> : <AutoFixHighIcon fontSize="inherit" />}
                  </IconButton>
                </span>
              </Tooltip>
            </Box>
            {suggestionError && !isSuggestionDialogOpen && (
                <Alert severity="error" sx={{ m: 1 }}>{suggestionError}</Alert>
            )}
            {loadingFolders ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100px', p: 2 }}>
                <CircularProgress />
              </Box>
            ) : folderError ? (
              <Alert severity="error" sx={{ m: 1 }}>{folderError}</Alert>
            ) : folders.length === 0 && selectedAccountIdForView !== 'all' && typeof selectedAccountIdForView !== 'number' ? (
              <Typography variant="body2" sx={{ p: 2, color: 'text.secondary' }}>
                Bitte zuerst ein Konto auswählen.
              </Typography>
            ) : folders.length === 0 ? (
              <Typography variant="body2" sx={{ p: 2, color: 'text.secondary' }}>
                Keine Ordner gefunden oder verfügbar.
              </Typography>
            ) : (
              <List dense disablePadding>
                {folders.map((folderPath) => (
                  <ListItem key={folderPath} disablePadding>
                    <ListItemButton
                      selected={selectedFolder === folderPath}
                      onClick={() => handleFolderSelect(folderPath)}
                      sx={{ paddingTop: '2px', paddingBottom: '2px' }}
                    >
                      <ListItemText 
                        primary={folderPath}
                        primaryTypographyProps={{ sx: { fontSize: '0.875rem' } }}
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={9}>
          {selectedEmailId !== null ? (
              <Paper sx={{ p: 0, flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <Box sx={{ p: 1, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center' }}>
                      <IconButton onClick={handleBackToList} size="small" sx={{ mr: 1 }}>
                          <ArrowBackIcon />
                      </IconButton>
                      <Typography variant="h6" sx={{ fontSize: '1rem' }}>E-Mail Details</Typography>
                  </Box>
                  <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
                    <EmailDetail emailId={selectedEmailId} />
                  </Box>
              </Paper>
          ) : (
              <Paper sx={{ p: 0, flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <Box sx={{ p: 1, borderBottom: 1, borderColor: 'divider' }}>
                      <Typography variant="h6" gutterBottom sx={{ fontSize: '1rem', mb: 0 }}>
                          {selectedFolder ? `E-Mails in: ${selectedFolder}` : "E-Mails"}
                      </Typography>
                  </Box>
                  
                  <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
                    {!selectedFolder ? (
                        <Box sx={{ p: 2, textAlign: 'center' }}>
                            <Typography color="text.secondary">Bitte wählen Sie links einen Ordner aus.</Typography>
                        </Box>
                    ) : loadingEmails && currentPage === 1 ? (
                      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', p: 2 }}>
                        <CircularProgress />
                      </Box>
                    ) : emailError ? (
                      <Alert severity="error" sx={{ m: 1 }}>{emailError}</Alert>
                    ) : emails.length === 0 ? (
                      <Box sx={{ p: 2, textAlign: 'center' }}>
                          <Typography color="text.secondary">Keine E-Mails in diesem Ordner gefunden.</Typography>
                      </Box>
                    ) : (
                      <EmailList 
                        emails={emails}
                        selectedEmailId={selectedEmailId}
                        onSelectEmail={handleEmailSelect}
                        onLoadMore={handleLoadMoreEmails}
                        hasMore={hasMoreEmails}
                        loadingMore={loadingEmails && currentPage > 1}
                        displayMode="detailed"
                      />
                    )}
                  </Box>
              </Paper>
          )}
        </Grid>
      </Grid>

      <Dialog 
        open={isSuggestionDialogOpen} 
        onClose={handleCloseSuggestionDialog}
        aria-labelledby="suggestion-dialog-title"
        maxWidth="md" 
        fullWidth
      >
        <DialogTitle id="suggestion-dialog-title">Vorgeschlagene Ordnerstruktur</DialogTitle>
        <DialogContent>
          {createFoldersError && (
              <Alert severity="error" sx={{ mb: 2 }}>{createFoldersError}</Alert>
          )}
          {createFoldersSuccess && (
              <Alert severity="success" sx={{ mb: 2 }}>{createFoldersSuccess}</Alert>
          )}

          {suggestionError && !suggestedStructure && (
              <Alert severity="error" sx={{ mb: 2 }}>{suggestionError}</Alert>
          )}

          {suggestedStructure && !creatingFolders && (
            <FormControl fullWidth sx={{ my: 2 }} size="small">
              <InputLabel id="target-account-select-label">Ziel-E-Mail-Konto</InputLabel>
              <Select
                labelId="target-account-select-label"
                label="Ziel-E-Mail-Konto"
                value={selectedTargetAccountId}
                onChange={(e) => setSelectedTargetAccountId(e.target.value as number | string)}
              >
                <MenuItem value="" disabled><em>Bitte wählen...</em></MenuItem>
                {loadingAccounts && <MenuItem value="" disabled><em>Lade Konten...</em></MenuItem>}
                {userEmailAccounts.map((account) => (
                  <MenuItem key={account.id} value={account.id}>
                    {account.name || account.email} ({account.provider})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {suggestedStructure && !creatingFolders ? (
            <>
              <DialogContentText component="div" sx={{ mb: 1 }}> 
                Basierend auf Ihren E-Mails schlägt die AI folgende Ordnerstruktur vor. Wählen Sie die zu erstellenden Ordner aus.
              </DialogContentText>
              <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                <Button 
                  startIcon={<CheckBoxIcon />}
                  onClick={handleSelectAllFolders}
                  size="small"
                  variant="outlined"
                >
                  Alle auswählen
                </Button>
                <Button 
                  startIcon={<CheckBoxOutlineBlankIcon />}
                  onClick={handleDeselectAllFolders}
                  size="small"
                  variant="outlined"
                >
                  Alle abwählen
                </Button>
              </Stack>
              <SuggestionTreeView 
                structure={suggestedStructure}
                selectedPaths={selectedFoldersToCreate}
                onSelectionChange={setSelectedFoldersToCreate}
                initialExpandedNodes={initialExpandedNodes}
              />
            </>
          ) : creatingFolders ? (
                 <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '150px' }}>
                   <CircularProgress />
                   <Typography sx={{ ml: 2 }}>Ordner werden erstellt...</Typography>
                 </Box>
            ) : !suggestionError ? (
                 <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '150px' }}>
                   <CircularProgress />
                   <Typography sx={{ ml: 2 }}>Vorschlag wird geladen...</Typography>
                 </Box>
            ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseSuggestionDialog}>Schließen</Button>
          <Button 
            onClick={handleCreateSelectedFolders}
            variant="contained"
            disabled={!selectedTargetAccountId || selectedFoldersToCreate.length === 0 || creatingFolders || loadingSuggestion || !suggestedStructure}
          >
            {creatingFolders ? <CircularProgress size={24} /> : "Ausgewählte Ordner erstellen"}
          </Button>
        </DialogActions>
      </Dialog>

    </Container>
  );
};

export default AISearchPage; 