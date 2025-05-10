import React, { useState, useEffect, useRef, FormEvent, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  InputAdornment,
  IconButton,
  CircularProgress,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material';
import { Visibility, VisibilityOff, Save as SaveIcon, Delete as DeleteIcon } from '@mui/icons-material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import ErrorIcon from '@mui/icons-material/Error';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { apiCredentials, checkApiKey } from '../../services/api';

interface ApiCredentialFormProps {
  credentialId: string; // e.g., 'groq'
  credentialName: string; // e.g., 'Groq'
}

type CheckStatus = 'idle' | 'checking' | 'valid' | 'invalid' | 'error';

const ApiCredentialForm: React.FC<ApiCredentialFormProps> = ({
  credentialId,
  credentialName
}) => {
  const [apiKey, setApiKey] = useState<string>('');
  const [showKey, setShowKey] = useState<boolean>(false);
  const [loadingSave, setLoadingSave] = useState<boolean>(false);
  const [loadingDelete, setLoadingDelete] = useState<boolean>(false);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [keyStatusIsSet, setKeyStatusIsSet] = useState<boolean>(false);
  const [keyEntryExists, setKeyEntryExists] = useState<boolean>(false);

  const [checkStatus, setCheckStatus] = useState<CheckStatus>('idle');
  const [isInteracted, setIsInteracted] = useState<boolean>(false);

  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [loadingModels, setLoadingModels] = useState<boolean>(false);
  const [errorModels, setErrorModels] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const retryTimeoutRef = useRef<number | null>(null);

  const loadModels = useCallback(async () => {
    if (!keyStatusIsSet) {
      console.log(`[ApiCredentialForm:${credentialId}] Skipping model load because keyStatusIsSet is false.`);
      setAvailableModels([]); // Clear models if key is not set
      setErrorModels(null);
      return;
    }
    setLoadingModels(true);
    setErrorModels(null); // Reset error before loading
    try {
      console.log(`[ApiCredentialForm:${credentialId}] Fetching available models...`);
      const response = await apiCredentials.getModels(credentialId);
      console.log(`[ApiCredentialForm:${credentialId}] Received models response:`, response);
      if (response.data && Array.isArray(response.data)) {
        setAvailableModels(response.data);
        console.log(`[ApiCredentialForm:${credentialId}] Successfully fetched ${response.data.length} models.`);
      } else {
        console.error(`[ApiCredentialForm:${credentialId}] Invalid model data received:`, response.data);
        setAvailableModels([]); // Set to empty array on invalid data
        setErrorModels('Invalid data format received for models.');
      }
    } catch (error: any) {
      console.error(`[ApiCredentialForm:${credentialId}] Error loading models:`, error);
      const errorMsg = error.response?.data?.detail || `Failed to load available models for ${credentialName}.`;
      setErrorModels(errorMsg);
      setAvailableModels([]); // Ensure models are cleared on error
    } finally {
      setLoadingModels(false);
    }
    // Dependencies: credentialId for the API call, keyStatusIsSet to trigger the load, credentialName for error message.
  }, [keyStatusIsSet, credentialId, credentialName]);

  const provider = credentialId;

  useEffect(() => {
    const checkKeyStatus = async () => {
      setLoadingStatus(true);
      setError(null);
      setSuccessMessage(null);
      setCheckStatus('idle');
      try {
        console.log(`[ApiCredentialForm:${provider}] Fetching initial status...`);
        const response = await apiCredentials.getStatus(provider);
        console.log(`[ApiCredentialForm:${provider}] Received status response:`, response);
        const apiKeySet = response?.data?.api_key_set;
        console.log(`[ApiCredentialForm:${provider}] Extracted api_key_set:`, apiKeySet, typeof apiKeySet);
        
        setKeyEntryExists(true);
        setKeyStatusIsSet(apiKeySet ?? false);
        console.log(`[ApiCredentialForm:${provider}] State AFTER setKeyStatusIsSet (using extracted value):`, apiKeySet ?? false);
      } catch (err: any) {
        console.error(`[ApiCredentialForm:${provider}] Error in checkKeyStatus:`, err);
        if (err.response && err.response.status === 404) {
          setKeyEntryExists(false);
          setKeyStatusIsSet(false);
          console.log(`[ApiCredentialForm:${provider}] Initial status loaded: Entry exists: false (404 received)`);
        } else {
          const errorMsg = err.response?.data?.detail || `Failed to check API key status.`;
          setError(errorMsg);
          setKeyEntryExists(false);
          setKeyStatusIsSet(false);
          console.error(`[ApiCredentialForm:${provider}] Error checking API key status (non-404):`, err);
        }
      } finally {
        setLoadingStatus(false);
      }
    };
    checkKeyStatus();
  }, [provider]);

  useEffect(() => {
    console.log(`[ApiCredentialForm:${provider}] useEffect for loadModels triggered. keyStatusIsSet =`, keyStatusIsSet);
    if (keyStatusIsSet) {
      loadModels();
    }
  }, [keyStatusIsSet, loadModels, provider]);

  useEffect(() => {
    let isActive = true;
    const isAuthenticated = !!localStorage.getItem('token');

    const connect = () => {
      if (!isActive) return;
      const currentToken = localStorage.getItem('token');
      if (!currentToken) {
          console.error(`[ApiCredentialForm:${provider} WS] Auth token not found.`);
          return;
      }
      if (wsRef.current && wsRef.current.readyState < WebSocket.CLOSING) {
           return;
      }

      const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
      const wsHost = import.meta.env.VITE_WS_BASE_URL || `${window.location.hostname}:8000`;
      const wsUrl = `${wsScheme}://${wsHost}/ws/general/?token=${currentToken}`;

      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
          if (!isActive) return;
          if (retryTimeoutRef.current) {
              clearTimeout(retryTimeoutRef.current);
              retryTimeoutRef.current = null;
          }
      };

      socket.onmessage = (event) => {
          if (!isActive) return;
          try {
              const message = JSON.parse(event.data);
              if (message.type === 'api_key_status' && message.data?.provider === provider) {
                const status = message.data.status as CheckStatus;
                const statusMessage = message.data.message || (status === 'valid' ? 'API Key is valid.' : 'API Key check resulted in an issue.');

                setCheckStatus(status);

                if (status === 'valid') {
                    setSuccessMessage(statusMessage);
                    setError(null);
                } else if (status === 'invalid' || status === 'error') {
                    setError(statusMessage);
                    setSuccessMessage(null);
                }
              }
          } catch (error) {
              console.error(`[ApiCredentialForm:${provider} WS] Parse/handle error:`, error);
          }
      };

      socket.onerror = (error) => {
      };

      socket.onclose = (event) => {
          if (!isActive) return;
          wsRef.current = null;
          if (!event.wasClean && event.code !== 1000 && isActive && isAuthenticated) {
              const retryDelay = 5000;
              if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
              retryTimeoutRef.current = window.setTimeout(() => {
                   if (isActive && isAuthenticated) connect();
              }, retryDelay);
          }
      };
    };

    if (isAuthenticated) connect();
    else if (wsRef.current) wsRef.current.close(1000, "Logged out");

    return () => {
        isActive = false;
        if (retryTimeoutRef.current) {
            clearTimeout(retryTimeoutRef.current);
            retryTimeoutRef.current = null;
        }
        const socketToClose = wsRef.current;
        if (socketToClose) {
            socketToClose.onclose = null;
            socketToClose.onerror = null;
            socketToClose.onmessage = null;
            socketToClose.onopen = null;
            if (socketToClose.readyState === WebSocket.OPEN) {
                socketToClose.close(1000, "Unmounting");
            }
            wsRef.current = null;
        }
    };
  }, [provider]);

  const handleSaveKey = async () => {
    setLoadingSave(true);
    setError(null);
    setSuccessMessage(null);
    setCheckStatus('idle');
    console.log(`[ApiCredentialForm:${provider}] handleSaveKey started. Current keyEntryExists: ${keyEntryExists}, keyStatusIsSet: ${keyStatusIsSet}`);

    if (!apiKey) {
      setError("Please enter an API Key.");
      setLoadingSave(false);
      console.log(`[ApiCredentialForm:${provider}] handleSaveKey aborted: No API key entered.`);
      return;
    }

    console.log(`Saving API Key for ${credentialName} (ID: ${credentialId}). Entry exists: ${keyEntryExists}`);

    try {
      let response;
      if (keyEntryExists) {
        console.log(`[ApiCredentialForm:${provider}] Calling apiCredentials.update with key: ${apiKey.substring(0, 5)}...`);
        response = await apiCredentials.update(credentialId, apiKey);
        console.log(`[ApiCredentialForm:${provider}] apiCredentials.update successful. Response:`, response);
      } else {
         console.log(`[ApiCredentialForm:${provider}] Calling apiCredentials.create with key: ${apiKey.substring(0, 5)}...`);
        response = await apiCredentials.create(credentialId, apiKey);
        console.log(`[ApiCredentialForm:${provider}] apiCredentials.create successful. Response:`, response);
      }

      const successMsg = response.message || `${credentialName} API Key saved successfully.`;
      console.log(`[ApiCredentialForm:${provider}] Setting success message: "${successMsg}"`);
      setSuccessMessage(successMsg);

      console.log(`[ApiCredentialForm:${provider}] Clearing API key input.`);
      setApiKey('');
      console.log(`[ApiCredentialForm:${provider}] Hiding key.`);
      setShowKey(false);
      console.log(`[ApiCredentialForm:${provider}] Setting keyEntryExists to true.`);
      setKeyEntryExists(true);
      console.log(`[ApiCredentialForm:${provider}] Setting keyStatusIsSet to true.`);
      setKeyStatusIsSet(true);
      console.log(`[ApiCredentialForm:${provider}] State updates in success block finished.`);

      if (!error && keyStatusIsSet) {
           setTimeout(async () => {
               console.log(`[ApiCredentialForm:${provider}] Triggering model refresh after save.`);
               await loadModels();
           }, 1000);
       }

    } catch (err: any) {
      console.error(`[ApiCredentialForm:${provider}] Error inside handleSaveKey catch block:`, err);
      const backendError = err?.response?.data?.detail || err?.response?.data?.error || err?.message;
      const errorMsg = `Failed to save ${credentialName} API Key. ${backendError ? `Error: ${backendError}` : 'Please try again.'}`;
      console.log(`[ApiCredentialForm:${provider}] Setting error message: "${errorMsg}"`);
      setError(errorMsg);
    } finally {
      console.log(`[ApiCredentialForm:${provider}] Entering finally block. Setting loadingSave to false.`);
      setLoadingSave(false);
    }
  };

  const handleDelete = async () => {
    setLoadingDelete(true);
    setError(null);
    setSuccessMessage(null);
    setCheckStatus('idle');
    try {
      await apiCredentials.delete(provider);
      setSuccessMessage('API Key deleted successfully.');
      setKeyEntryExists(false);
      setKeyStatusIsSet(false);
      setApiKey('');
      setShowKey(false);
      setAvailableModels([]);
      setErrorModels(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || `Failed to delete API key.`);
      console.error("Error deleting API key:", err);
    } finally {
      setLoadingDelete(false);
    }
  };

  const handleCheckKey = async () => {
    setCheckStatus('checking');
    setError(null);
    setSuccessMessage(null);
    setLoadingModels(true);
    setAvailableModels([]);
    setErrorModels(null);
    console.log(`[ApiCredentialForm:${provider}] Triggering API key check via POST /check`);
    try {
      await checkApiKey(provider);
      console.log(`[ApiCredentialForm:${provider}] Check task queued, now reloading models...`);
      await loadModels();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Error starting API key check.';
      setCheckStatus('error');
      setError(errorMsg);
      setSuccessMessage(null);
      console.error(`[ApiCredentialForm:${provider}] Error starting API key check:`, err);
      setLoadingModels(false);
      setErrorModels("Model discovery might have failed due to check error.");
    } finally {
      
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleSaveKey();
    }
  };

  const handleFormSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!apiKey || loadingSave || loadingDelete || checkStatus === 'checking') {
      return;
    }
    handleSaveKey();
  };

  const getStatusIcon = () => {
    switch (checkStatus) {
      case 'checking': return <CircularProgress size={20} sx={{ ml: 1 }} />;
      case 'valid': return <CheckCircleIcon color="success" sx={{ ml: 1 }} />;
      case 'invalid': return <CancelIcon color="error" sx={{ ml: 1 }} />;
      case 'error': return <ErrorIcon color="error" sx={{ ml: 1 }} />;
      default: return null;
    }
  };

  const getStatusText = () => {
      if (loadingStatus) return "Loading status...";
      if (keyStatusIsSet) return "API Key is set.";
      return "API Key is not set.";
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        {credentialName} API Credentials
      </Typography>

      <form onSubmit={handleFormSubmit} noValidate>
        <TextField
          fullWidth
          required
          name={`api-key-${provider}`}
          label={`${keyStatusIsSet ? 'Update' : 'Enter'} ${credentialName} API Key`}
          type={isInteracted ? (showKey ? 'text' : 'password') : 'text'}
          value={apiKey}
          autoComplete="off"
          onFocus={() => setIsInteracted(true)}
          onChange={(e) => {
            setApiKey(e.target.value);
            setError(null);
            setSuccessMessage(null);
            if (checkStatus !== 'idle' && checkStatus !== 'checking') {
              setCheckStatus('idle');
            }
          }}
          onKeyDown={handleKeyDown}
          placeholder={keyStatusIsSet ? "Enter new key to update" : "Enter your API Key"}
          disabled={loadingSave || loadingDelete || loadingStatus || checkStatus === 'checking'}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label="toggle api key visibility"
                  onClick={() => {
                    setShowKey(!showKey);
                    setIsInteracted(true);
                  }}
                  onMouseDown={(event) => event.preventDefault()}
                  edge="end"
                >
                  {showKey ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
            autoComplete: "off",
          }}
          sx={{ mt: 0, mb: 2 }}
        />

        {error && <Alert severity="error" sx={{ mb: 2, mt: 1 }}>{error}</Alert>}
        {successMessage && <Alert severity="success" sx={{ mb: 2, mt: 1 }}>{successMessage}</Alert>}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
           <Box>
                {keyEntryExists && (
                  <Tooltip title="Request backend to verify the stored key (if set)">
                      <span>
                          <Button
                              variant="outlined"
                              onClick={handleCheckKey}
                              disabled={checkStatus === 'checking' || loadingSave || loadingDelete}
                              startIcon={checkStatus === 'checking' ? <CircularProgress size={16} /> : <HelpOutlineIcon />}
                              size="small"
                              sx={{ mr: 1 }}
                              type="button"
                          >
                              Check Key
                          </Button>
                       </span>
                  </Tooltip>
                )}
                 {keyEntryExists && (
                    <Button
                      variant="outlined"
                      color="error"
                      onClick={handleDelete}
                      disabled={loadingDelete || loadingSave || checkStatus === 'checking'}
                      startIcon={loadingDelete ? <CircularProgress size={16} /> : <DeleteIcon />}
                      size="small"
                      type="button"
                  >
                      Delete Key
                  </Button>
                 )}
           </Box>

          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={!apiKey || loadingSave || loadingDelete || checkStatus === 'checking'}
            startIcon={loadingSave ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
          >
            {keyEntryExists ? 'Update Key' : 'Save Key'}
          </Button>
        </Box>
      </form>

      {(keyStatusIsSet || availableModels.length > 0) && (
          <Box sx={{ mt: 3 }}>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="subtitle1" gutterBottom>
                  Discovered Models
              </Typography>
              {loadingModels && <CircularProgress size={20} />}
              {errorModels && !loadingModels && <Alert severity="warning" sx={{ mb: 1 }}>{errorModels}</Alert>}
              {!loadingModels && !errorModels && availableModels.length === 0 && keyStatusIsSet && (
                  <Typography variant="body2" color="text.secondary">
                      No models discovered or loaded yet. Try 'Check Key' or save a valid key.
                  </Typography>
              )}
              {!loadingModels && availableModels.length > 0 && (
                  <List dense disablePadding>
                      {availableModels.map((model, index) => {
                          const displayId = model.model_id.startsWith('models/') 
                              ? model.model_id.substring(7) 
                              : model.model_id;
                              
                          return (
                              <ListItem key={`${model.provider}-${model.model_id}-${index}`} disableGutters>
                                  <ListItemText 
                                      primary={displayId}
                                  />
                              </ListItem>
                          );
                      })}
                  </List>
              )}
          </Box>
      )}

    </Paper>
  );
};

export default ApiCredentialForm; 