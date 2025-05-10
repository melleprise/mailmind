import React, { useState, useEffect } from 'react';
import { Box, TextField, Button, CircularProgress, Typography, Paper, Grid, Switch, FormControlLabel, InputAdornment, IconButton, Tooltip, CardActions } from '@mui/material';
import { Visibility, VisibilityOff, Delete as DeleteIcon, Sync as SyncIcon, Save as SaveIcon, ArrowForward as ContinueIcon, Search as SearchIcon } from '@mui/icons-material';
import { emailAccounts } from '../../services/api'; // Import correct object

// Interface für Account-Daten (könnte aus SettingsPage kommen)
interface EmailAccount {
  id: number;
  name: string;
  email: string;
  provider: string;
  // Assuming these might be available for editing:
  imap_server?: string;
  imap_port?: number | string;
  imap_use_ssl?: boolean;
  smtp_server?: string;
  smtp_port?: number | string;
  smtp_use_tls?: boolean;
}

// Interface für die Einstellungen (erweitert für manuelle Bearbeitung)
interface AccountSettings {
  imap_server: string;
  imap_port: number | string; // Allow string for empty/suggested value initially
  imap_use_ssl: boolean;
  smtp_server: string;
  smtp_port: number | string; // Allow string for empty/suggested value initially
  smtp_use_tls: boolean;
}

// Default leere Einstellungen für manuelles Formular
const defaultManualSettings: AccountSettings = {
    imap_server: '',
    imap_port: '',
    imap_use_ssl: true,
    smtp_server: '',
    smtp_port: '',
    smtp_use_tls: true,
};

// Define props for the form
interface EmailAccountFormProps {
  accountToEdit?: EmailAccount | null; // Account being edited
  onAccountAddedOrUpdated?: (accountId: number | null, status?: string, message?: string) => void; // Callback after success, optionally passing the new/updated account ID
  onDelete?: (id: number) => void; // Callback for delete button
  syncingAccountId?: number | null; // Receive syncing state
  onTriggerSync?: (id: number) => void; // Receive sync trigger handler
}

const EmailAccountForm: React.FC<EmailAccountFormProps> = ({ accountToEdit, onAccountAddedOrUpdated, onDelete, syncingAccountId, onTriggerSync }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [accountName, setAccountName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null); // Für Erfolgsmeldungen
  // Add state for suggested settings
  const [suggestedSettings, setSuggestedSettings] = useState<AccountSettings | null>(null);
  const [showSettingsSection, setShowSettingsSection] = useState(false); // Start hidden
  // Add state to track if using manual settings
  const [isManualMode, setIsManualMode] = useState(false); 
  const [manualSettings, setManualSettings] = useState<AccountSettings>(defaultManualSettings);
  const [showPassword, setShowPassword] = useState(false); // State for password visibility

  useEffect(() => {
    if (accountToEdit) {
      setAccountName(accountToEdit.name || '');
      setEmail(accountToEdit.email);
      // Don't prefill password for security
      setPassword(''); 
      setManualSettings({ 
        imap_server: accountToEdit.imap_server || '', 
        imap_port: accountToEdit.imap_port || '',
        imap_use_ssl: accountToEdit.imap_use_ssl ?? true,
        smtp_server: accountToEdit.smtp_server || '',
        smtp_port: accountToEdit.smtp_port || '',
        smtp_use_tls: accountToEdit.smtp_use_tls ?? true,
       });
      // Show settings section immediately in edit mode
      setShowSettingsSection(true); 
      setIsManualMode(true); // Always start in manual mode when editing existing
      setError(null); // Clear any previous errors
      setSuccessMessage(null);
    } else {
      // Reset form completely if switching to Add mode
      setAccountName('');
      setEmail('');
      setPassword('');
      setManualSettings(defaultManualSettings);
      setShowSettingsSection(false);
      setIsManualMode(false); // Reset manual mode on switch to Add
      setSuggestedSettings(null); // Clear suggestions on switch to Add
      setError(null);
      setSuccessMessage(null);
    }
  }, [accountToEdit]);

  // New useEffect to read URL parameters on mount/edit mode entry
  useEffect(() => {
    // Run this effect regardless of whether it's edit or add mode initially
    // Use window.location.search directly as it reflects the current URL
    const params = new URLSearchParams(window.location.search);
    const status = params.get('status');
    const message = params.get('message');

    if (status === 'success' && message) {
      setSuccessMessage(decodeURIComponent(message));
      // Clean the URL - remove query parameters
      window.history.replaceState(null, '', window.location.pathname);
    } else if (status === 'error' && message) {
      // Display error only if we are in edit mode (accountToEdit exists)
      // Error during save is handled inline, this is for errors passed via URL (e.g., if we decided to redirect on save error)
      if (accountToEdit) {
         setError(decodeURIComponent(message));
         // Clean the URL
         window.history.replaceState(null, '', window.location.pathname);
      }
    }
  }, [accountToEdit]); // Keep dependency on accountToEdit to re-evaluate if mode changes

  // Helper function to update manual settings state
  const handleManualSettingChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | React.ChangeEvent<{ name?: string | undefined; value: unknown }>, checked?: boolean) => {
      const { name, value, type } = event.target as HTMLInputElement;
      setManualSettings(prev => ({
          ...prev,
          [name!]: type === 'checkbox' ? checked : type === 'number' ? (value === '' ? '' : Number(value)) : value
      }));
  };

  // Separate Change handler for Switches
  const handleManualSwitchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
     const { name, checked } = event.target;
     setManualSettings(prev => ({
         ...prev,
         [name!]: checked
     }));
  };

  // --- Function to fetch suggested settings --- 
  const handleFindSettings = async () => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);
    setShowSettingsSection(false); // Hide current settings if any
    setSuggestedSettings(null);
    setIsManualMode(false); // Assume suggestion mode initially

    try {
      // Call the new API function
      const response = await emailAccounts.suggestSettings(email);
      // Extract settings from the nested structure
      const responseData = response.data; 
      const settingsData = responseData.settings; // Get settings from responseData.settings
      console.info("[EmailAccountForm] Received suggested settings response:", responseData);

      // Check if settingsData exists and has essential fields
      if (settingsData && settingsData.imap_server && settingsData.smtp_server) {
        setSuggestedSettings({
          ...settingsData,
          // Ports should already be numbers from backend if successful
          imap_port: settingsData.imap_port || '', // Fallback to empty string if somehow missing
          smtp_port: settingsData.smtp_port || '', // Fallback to empty string if somehow missing
        });
        setShowSettingsSection(true); // Show the section with suggested data
        setIsManualMode(false); // Ensure we are NOT in manual mode
        setManualSettings(defaultManualSettings); // Clear manual settings
      } else {
        // Switch to manual mode if no sufficient suggestions
        setError('Could not automatically determine all settings. Please enter them manually.');
        setShowSettingsSection(true);
        setIsManualMode(true);
        setManualSettings(defaultManualSettings); // Reset to empty manual fields
        setSuggestedSettings(null);
      }
    } catch (apiError: any) {
      console.error('Error finding settings:', apiError.response?.data || apiError.message);
      const errorMessage = apiError.response?.data?.detail || apiError.response?.data?.message || 'Could not fetch settings. Please enter them manually.';
      setError(errorMessage);
      // Force manual mode on error
      setShowSettingsSection(true); 
      setIsManualMode(true);        
      setManualSettings(defaultManualSettings); 
      setSuggestedSettings(null);
    } finally {
      setLoading(false);
    }
  };
  // --- End function --- 

  // Helper to determine provider from email domain
  const getProviderFromEmail = (emailAddr: string): string => {
    if (!emailAddr) return 'custom'; // Default to custom if email is empty
    const domain = emailAddr.split('@')[1]?.toLowerCase();
    if (domain === 'gmail.com' || domain === 'googlemail.com') return 'gmail'; // Use 'gmail' (lowercase)
    if (domain === 'outlook.com' || domain === 'hotmail.com' || domain === 'live.com') return 'outlook'; // Use 'outlook' (lowercase)
    // Add more known providers if needed
    return 'custom'; // Fallback to 'custom' for unknown domains
  }

  const handleSaveAccount = async () => {
    // Determine settings to use based on mode
    const settingsToUse = isManualMode ? manualSettings : suggestedSettings;

    // Validierung (einfach) - Ports müssen Nummern sein
    const imapPortNumber = Number(settingsToUse.imap_port);
    const smtpPortNumber = Number(settingsToUse.smtp_port);

    if (isNaN(imapPortNumber) || isNaN(smtpPortNumber) || imapPortNumber <= 0 || smtpPortNumber <= 0) {
        setError('IMAP and SMTP ports must be valid positive numbers.');
        return;
    }

    // Determine provider based on email
    const provider = getProviderFromEmail(email);

    const payload = {
      email: email,
      password: password,
      name: accountName || email,
      provider: provider,
      imap_server: settingsToUse.imap_server,
      imap_port: imapPortNumber,
      imap_use_ssl: settingsToUse.imap_use_ssl,
      smtp_server: settingsToUse.smtp_server,
      smtp_port: smtpPortNumber,
      smtp_use_tls: settingsToUse.smtp_use_tls,
      // Provider wird jetzt vom Backend gesetzt basierend auf IMAP/SMTP
    };

    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      let response;
      if (accountToEdit) {
        // Update existing account - Use imported emailAccounts
        response = await emailAccounts.update(accountToEdit.id, payload);
        setSuccessMessage('Account updated successfully!');
      } else {
        // Create new account - Use imported emailAccounts
        response = await emailAccounts.create(payload);
        setSuccessMessage('Account added successfully! Initial sync started.');
      }
      console.log('Save response:', response.data);
      // Reset password field after successful save
      setPassword(''); 
      // Callback mit ID, Status und Nachricht
      if (onAccountAddedOrUpdated) {
        onAccountAddedOrUpdated(response.data.id, 'success', response.data.message || successMessage);
      }
      // Reset internal state if creating a new account
      if (!accountToEdit) {
         setAccountName('');
         setPassword('');
         setShowSettingsSection(false);
         setIsManualMode(false);
         setSuggestedSettings(null);
         setManualSettings(defaultManualSettings);
      }

    } catch (err: any) {
      console.error('Error saving account:', err.response || err.message);
      const errorData = err.response?.data;
      let errorMessage = `An error occurred while ${accountToEdit ? 'updating' : 'saving'} the account.`;

      if (errorData && typeof errorData === 'object') {
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else {
          const fieldErrors = Object.entries(errorData)
                                   .map(([field, errors]) => `${field}: ${(Array.isArray(errors) ? errors.join(', ') : errors)}`)
                                   .join('\n');
           errorMessage = fieldErrors ? `Validation errors: \n${fieldErrors}` : errorMessage;
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Helper to determine current value for fields
  const getCurrentSetting = (key: keyof AccountSettings) => {
     // Return manual setting if in manual mode, otherwise suggested, fallback to empty
     return isManualMode 
         ? manualSettings[key] 
         : (suggestedSettings ? suggestedSettings[key] : ''); 
  }

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      {/* Header with Title and Optional Delete/Sync Buttons */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" gutterBottom sx={{ mb: 0 }}>
          {accountToEdit ? (accountToEdit.name || accountToEdit.email) : 'Add New Email Account'}
        </Typography>
        {/* Group Sync and Delete buttons */}
        {accountToEdit && (onTriggerSync || onDelete) && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Sync Button/Indicator */}
            {onTriggerSync && (
               syncingAccountId === accountToEdit.id ? (
                 <CircularProgress size={24} />
               ) : (
                 <Tooltip title="Sync Account Now">
                    {/* Wrap IconButton in span when disabled for Tooltip */}
                   <span>
                     <IconButton 
                       onClick={() => onTriggerSync(accountToEdit.id)}
                       size="small" 
                       disabled={syncingAccountId !== null} // Disable if ANY sync is in progress via UI
                       color="primary"
                     >
                       <SyncIcon />
                     </IconButton>
                    </span>
                 </Tooltip>
               )
            )}
            {/* Delete Button */}
            {onDelete && (
              <Tooltip title="Delete Account">
                 {/* Wrap IconButton in span when disabled for Tooltip */}
                <span>
                  <IconButton 
                    onClick={() => onDelete(accountToEdit.id)} 
                    size="small" 
                    color="error"
                    disabled={syncingAccountId === accountToEdit.id} // Disable delete while this account is syncing
                  >
                    <DeleteIcon />
                  </IconButton>
                 </span>
              </Tooltip>
            )}
          </Box>
        )}
      </Box>

      {/* Erfolgsmeldung anzeigen */} 
      {successMessage && (
         <Typography color="success.main" sx={{ mt: 1, mb: 2 }}>
           {successMessage}
         </Typography>
      )}
      <Box component="form" noValidate autoComplete="off">
        <TextField
          required
          fullWidth
          margin="normal"
          label="Email Address"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          required
          fullWidth
          margin="normal"
          label="Password / App Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
           helperText="For Gmail/Outlook use an App Password if 2FA is enabled."
          InputLabelProps={{ shrink: true }}
          type={showPassword ? 'text' : 'password'}
          InputProps={{
            endAdornment: (
              <InputAdornment 
                position="end">
                <IconButton
                  aria-label="toggle password visibility"
                  onClick={() => setShowPassword(!showPassword)}
                  onMouseDown={(event) => event.preventDefault()}
                  edge="end"
                  sx={{ 
                    '&:hover': { backgroundColor: 'transparent' }
                  }}
                >
                  {showPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          }}
        />

        {error && (
          <Typography color="error" sx={{ mt: 1, mb: 2, whiteSpace: 'pre-wrap' }}>
            {error}
          </Typography>
        )}

        {/* Account Name (Optional) */}
        <TextField
          fullWidth
          margin="normal"
          label="Account Name (Optional)"
          value={accountName}
          onChange={(e) => setAccountName(e.target.value)}
          helperText="A friendly name for this account (e.g., Work Gmail). Defaults to email if left blank."
          InputLabelProps={{ shrink: true }}
          disabled={loading} // Disable while loading/saving
        />

        {/* Buttons visible before settings section is shown (Add mode only) */}
        {!accountToEdit && !showSettingsSection && ( 
         <Box sx={{ mt: 2, display: 'flex', gap: 1 }}> { /* Use Flexbox for button layout */}
            <Button 
                variant="contained" 
                color="secondary" // Use a different color? Or outlined?
                onClick={handleFindSettings} 
                disabled={loading || !email || !password} // Disable if no email/pw or loading
                startIcon={<SearchIcon />}
              >
                Suggest Settings
              </Button>
              <Button 
                variant="outlined" 
                onClick={() => {
                    setError(null); // Clear errors
                    setSuggestedSettings(null); // Clear suggestions
                    setManualSettings(defaultManualSettings); // Prepare empty manual fields
                    setIsManualMode(true); 
                    setShowSettingsSection(true);
                }} 
                disabled={loading || !email || !password} // Disable if no email/pw or loading
                // endIcon={<ContinueIcon />} // Use different icon?
              >
                Enter Manually
              </Button>
          </Box>
        )}

        {/* Einstellungsbereich anzeigen (entweder Vorschlag oder manuelle Eingabe) */}
        {showSettingsSection && ( 
          <Box sx={{ mt: 3, p: 2, border: '1px dashed', borderColor: 'grey.400', borderRadius: 1 }}>
            <Typography variant="subtitle1" gutterBottom>
                {isManualMode ? 'Enter Settings Manually:' : 'Suggested Settings (Edit if necessary):'}
            </Typography>
            <Grid container spacing={2}>
              {/* IMAP Fields */}
              <Grid item xs={12} sm={6}>
                <TextField
                    fullWidth
                    required
                    label="IMAP Server"
                    name="imap_server"
                    value={getCurrentSetting('imap_server')}
                    onChange={handleManualSettingChange}
                    disabled={!isManualMode && !!suggestedSettings} // Disable if showing suggestions
                    margin="dense"
                 />
              </Grid>
              <Grid item xs={6} sm={3}>
                 <TextField
                    fullWidth
                    required
                    label="IMAP Port"
                    name="imap_port"
                    type="number"
                    value={getCurrentSetting('imap_port')}
                    disabled={!isManualMode && !!suggestedSettings} // Disable if showing suggestions
                    onChange={handleManualSettingChange}
                    margin="dense"
                    inputProps={{ min: 1, max: 65535 }}
                 />
              </Grid>
              <Grid item xs={6} sm={3} sx={{ display: 'flex', alignItems: 'center' }}>
                 <FormControlLabel
                    control={<Switch
                                name="imap_use_ssl"
                                checked={getCurrentSetting('imap_use_ssl')}
                                disabled={!isManualMode && !!suggestedSettings} // Disable if showing suggestions
                                onChange={handleManualSwitchChange}
                             />}
                    label="IMAP SSL/TLS"
                 />
              </Grid>

              {/* SMTP Fields - Make always editable */}
              <Grid item xs={12} sm={6}>
                 <TextField
                    fullWidth
                    required
                    label="SMTP Server"
                    name="smtp_server"
                    value={getCurrentSetting('smtp_server')}
                    onChange={handleManualSettingChange}
                    disabled={!isManualMode && !!suggestedSettings} // Disable if showing suggestions
                    margin="dense"
                 />
              </Grid>
              <Grid item xs={6} sm={3}>
                 <TextField
                    fullWidth
                    required
                    label="SMTP Port"
                    name="smtp_port"
                    type="number"
                    value={getCurrentSetting('smtp_port')}
                    disabled={!isManualMode && !!suggestedSettings} // Disable if showing suggestions
                    onChange={handleManualSettingChange}
                    margin="dense"
                    inputProps={{ min: 1, max: 65535 }}
                 />
              </Grid>
               <Grid item xs={6} sm={3} sx={{ display: 'flex', alignItems: 'center' }}>
                 <FormControlLabel
                    control={<Switch
                                name="smtp_use_tls"
                                checked={getCurrentSetting('smtp_use_tls')}
                                disabled={!isManualMode && !!suggestedSettings} // Disable if showing suggestions
                                onChange={handleManualSwitchChange}
                            />}
                    label="SMTP STARTTLS"
                 />
              </Grid>
            </Grid>

            {/* Action Buttons within the settings section */}
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}> {/* Align buttons to the right */}
                <Button
                  variant="outlined"
                  onClick={() => {
                    // Always hide section and clear state on cancel
                    setError(null);
                    setSuccessMessage(null);
                    setShowSettingsSection(false); 
                    setSuggestedSettings(null);
                    setIsManualMode(false);
                  }}
                  disabled={loading}
                  sx={{ mr: 1 }} // Add margin between buttons
                >
                  Cancel
                </Button>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleSaveAccount} 
                  // Simpler disabled check: Require necessary fields based on mode
                  disabled={loading || !email || !password || 
                            (getCurrentSetting('imap_server') === '') || (getCurrentSetting('imap_port') === '') || 
                            (getCurrentSetting('smtp_server') === '') || (getCurrentSetting('smtp_port') === '')
                  }
                  startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />} // Use SaveIcon here
                >
                  {loading ? 'Saving...' : (accountToEdit ? 'Update Account' : 'Save Account')}
                </Button>
                {/* Button to switch from Suggested to Manual */}
                {!isManualMode && suggestedSettings && (
                    <Button
                      variant="text"
                      onClick={() => {
                          setIsManualMode(true); // Switch to manual
                          // Pre-fill manual settings with suggested values for editing
                          setManualSettings(suggestedSettings);
                      }}
                      disabled={loading}
                      sx={{ ml: 1 }} // Add margin
                    >
                      Edit Settings Manually
                    </Button>
                )}
            </Box>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default EmailAccountForm; 