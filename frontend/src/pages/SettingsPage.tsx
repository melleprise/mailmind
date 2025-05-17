import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Container, Grid, Paper, CircularProgress, Alert } from '@mui/material';
import EmailAccountForm from '../components/settings/EmailAccountForm';
import EmailAccountList from '../components/settings/EmailAccountList';
import SettingsSidebar, { SettingsSection } from '../components/settings/SettingsSidebar';
import MailMindAccountSettings from '../components/settings/MailMindAccountSettings';
import ApiCredentialForm from '../components/settings/ApiCredentialForm';
import { emailAccounts, freelanceCredentials } from '../services/api';
import SettingsPromptsTable from './SettingsPrompts';
import SettingsPromptsProtocol from './SettingsPromptsProtocol';
import KnowledgeSettings from '../components/settings/KnowledgeSettings';
import AIActionSettings from '../components/settings/AIActionSettings';
import { useSnackbar } from 'notistack'; // Assuming notistack for notifications
import FreelanceProviderCredentialForm from '../components/settings/FreelanceProviderCredentialForm';

interface EmailAccount {
  id: number;
  name: string;
  email: string;
  provider: string;
}

const SettingsPage: React.FC = () => {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [errorAccounts, setErrorAccounts] = useState<string | null>(null);
  const [syncingAccountId, setSyncingAccountId] = useState<number | null>(null);
  const { enqueueSnackbar } = useSnackbar(); // For notifications

  // Freelance-Credentials State (nach oben gezogen)
  const [freelanceLoading, setFreelanceLoading] = useState<boolean>(true);
  const [hasCredentials, setHasCredentials] = useState<boolean>(false);
  const [credentials, setCredentials] = useState<any>(null);

  // Use localStorage to initialize and persist selectedSection
  const localStorageKey = 'mailmind_last_settings_section';
  const defaultSection = 'mailmind_account'; // Or another preferred default

  const [selectedSection, setSelectedSectionInternal] = useState<string>(
    () => localStorage.getItem(localStorageKey) || defaultSection
  );

  // Wrapper function to update state and localStorage
  const handleSelectSection = (section: string) => {
    setSelectedSectionInternal(section);
    localStorage.setItem(localStorageKey, section);
  };

  // Freelance-Credentials laden (Hook nach oben gezogen)
  useEffect(() => {
    const loadCredentials = async () => {
      try {
        setFreelanceLoading(true);
        const exists = await freelanceCredentials.exists();
        setHasCredentials(exists);
        if (exists) {
          const data = await freelanceCredentials.get();
          setCredentials(data);
        } else {
          setCredentials(null);
        }
      } catch (error) {
        console.error("Fehler beim Laden der Freelance-Credentials:", error);
        enqueueSnackbar('Fehler beim Laden der Zugangsdaten', { variant: 'error' });
      } finally {
        setFreelanceLoading(false);
      }
    };
    loadCredentials();
  }, [enqueueSnackbar]);

  // Handler für Speichern der Credentials
  const handleSaveCredentials = async (values: any) => {
    try {
      setFreelanceLoading(true);
      if (hasCredentials) {
        await freelanceCredentials.update(values);
        enqueueSnackbar('Zugangsdaten aktualisiert!', { variant: 'success' });
      } else {
        await freelanceCredentials.create(values);
        enqueueSnackbar('Zugangsdaten gespeichert!', { variant: 'success' });
        setHasCredentials(true);
      }
      // Teste die Zugangsdaten nach dem Speichern
      try {
        const validationResult = await freelanceCredentials.validate();
        if (validationResult.success) {
          enqueueSnackbar('Login-Test erfolgreich!', { variant: 'success' });
        } else {
          enqueueSnackbar(`Login-Test fehlgeschlagen: ${validationResult.detail}`, { variant: 'warning' });
        }
      } catch (validationError) {
        console.error("Fehler beim Validieren der Credentials:", validationError);
        enqueueSnackbar('Zugangsdaten gespeichert, aber Login-Test fehlgeschlagen', { variant: 'warning' });
      }
      // Neu laden, um aktuellen Stand zu bekommen
      const updatedData = await freelanceCredentials.get();
      setCredentials(updatedData);
    } catch (error) {
      console.error("Fehler beim Speichern der Freelance-Credentials:", error);
      enqueueSnackbar('Fehler beim Speichern der Zugangsdaten', { variant: 'error' });
    } finally {
      setFreelanceLoading(false);
    }
  };

  // Handler für Löschen der Credentials
  const handleDeleteCredentials = async () => {
    try {
      setFreelanceLoading(true);
      await freelanceCredentials.delete();
      enqueueSnackbar('Zugangsdaten gelöscht!', { variant: 'success' });
      setHasCredentials(false);
      setCredentials(null);
    } catch (error) {
      console.error("Fehler beim Löschen der Freelance-Credentials:", error);
      enqueueSnackbar('Fehler beim Löschen der Zugangsdaten', { variant: 'error' });
    } finally {
      setFreelanceLoading(false);
    }
  };

  const loadAccounts = async () => {
    setLoadingAccounts(true);
    setErrorAccounts(null);
    try {
      const response = await emailAccounts.list();
      setAccounts(response.data);
    } catch (err: any) {
      const errorData = err.response?.data;
      const errorMessage = errorData?.detail || errorData?.message || err.message || 'Failed to load accounts.';
      setErrorAccounts(errorMessage);
    } finally {
      setLoadingAccounts(false);
    }
  };

  useEffect(() => {
    loadAccounts();
  }, []);

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // WebSocket initialisieren
    const token = localStorage.getItem('authToken');
    if (!token) return;
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/notifications/?token=${token}`;
    wsRef.current = new WebSocket(wsUrl);
    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'sync_status') {
          const { accountId, status, message: notificationMessage } = data.payload;
          if (accountId === syncingAccountId) setSyncingAccountId(null);
          if (status === 'completed') enqueueSnackbar(notificationMessage || `Account ${accountId} synced successfully.`, { variant: 'success' });
          else if (status === 'failed') enqueueSnackbar(notificationMessage || `Account ${accountId} sync failed.`, { variant: 'error' });
        }
      } catch (e) { /* ignore */ }
    };
    wsRef.current.onerror = () => { wsRef.current?.close(); };
    wsRef.current.onclose = () => { wsRef.current = null; };
    return () => { wsRef.current?.close(); };
  }, [syncingAccountId, enqueueSnackbar]);

  const handleAccountAdded = () => {
    loadAccounts();
  };

  const handleDeleteAccount = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this email account?')) {
      setErrorAccounts(null);
      let deletedAccountEmail = accounts.find(acc => acc.id === id)?.email || 'the account'; // Get email before deleting
      try {
        await emailAccounts.delete(id);
        await loadAccounts(); // Wait for account list to reload
        // Always navigate to 'Add Account' section with a success message
        const successMessage = `Successfully deleted ${deletedAccountEmail}. You can add a new one now.`;
        handleSelectSection(`email_account_add?status=success&message=${encodeURIComponent(successMessage)}`); 

      } catch (err: any) {
        const errorData = err.response?.data;
        const errorMessage = errorData?.detail || errorData?.message || err.message || 'Failed to delete account.';
        setErrorAccounts(errorMessage); // Show error in the current context (e.g., list or edit view)
        // Optionally, navigate to 'email_accounts' on error?
        // handleSelectSection('email_accounts');
      }
    }
  };
  
  const handleEditAccount = (account: EmailAccount) => {
    // Navigate to the edit section for this account
    handleSelectSection(`email_account_edit_${account.id}`);
  };

  const handleTriggerSync = async (id: number) => {
    setSyncingAccountId(id);
    setErrorAccounts(null);
    try {
      const response = await emailAccounts.sync(id);
      console.log(`Sync task triggered for account ${id}:`, response.data);
      enqueueSnackbar(response.data?.detail || response.data?.status || 'Sync task started successfully!', { variant: 'info' });
    } catch (err: any) {
      let errorMessage = 'Failed to start sync task for account ' + id + '.';
      if (err.response?.data) {
        // Backend liefert oft 'error' oder 'detail'
        errorMessage = err.response.data.error || err.response.data.detail || errorMessage;
      } else if (err.message) {
        errorMessage = err.message;
      }
      setErrorAccounts(errorMessage);
      enqueueSnackbar(errorMessage, { variant: 'error' });
      setSyncingAccountId(null);
    }
  };

  const ApiCredentialsSection: React.FC = () => <Paper sx={{ p: 2 }}><Typography>API Credentials (Groq, etc.) - Placeholder</Typography></Paper>;

  const renderContent = () => {
    switch (selectedSection) {
      case 'mailmind_account':
        return <MailMindAccountSettings />;
      case 'email_accounts':
        return <Typography>Select an action (Add Account) or an existing account.</Typography>;
      case 'email_account_add':
        return <EmailAccountForm 
          onAccountAddedOrUpdated={(accountId, status, message) => {
            loadAccounts(); 
            if (accountId !== null) {
              let section = `email_account_edit_${accountId}`;
              if (status && message) {
                section += `?status=${status}&message=${encodeURIComponent(message)}`;
              }
              handleSelectSection(section); 
            } else {
              handleSelectSection('email_accounts'); 
            }
          }} 
        />;
      case 'api_credentials':
        return <Typography>Select an API credential provider from the menu.</Typography>;
      case 'prompts_templates':
        return <SettingsPromptsTable />;
      case 'prompts_protocol':
        return <SettingsPromptsProtocol />;
      case 'knowledge':
        return <KnowledgeSettings />;
      case 'actions':
        return <AIActionSettings />;
      case 'leads_freelance': {
        return (
          <FreelanceProviderCredentialForm 
            initialValues={credentials ? {
              username: credentials.username,
              link: credentials.link,
            } : {
              username: '',
              link: '',
            }}
            onSave={handleSaveCredentials}
            onDelete={handleDeleteCredentials}
            hasExistingCredentials={hasCredentials}
            loading={freelanceLoading}
          />
        );
      }
      default:
        // Handle Email Account Edit
        if (selectedSection.startsWith('email_account_edit_')) {
          const accountId = parseInt(selectedSection.replace('email_account_edit_', ''), 10);
          if (!isNaN(accountId)) {
            const accountToEdit = accounts.find(acc => acc.id === accountId);
            if (accountToEdit) {
              return <EmailAccountForm 
                        accountToEdit={accountToEdit} 
                        onDelete={handleDeleteAccount}
                        onAccountAddedOrUpdated={(accountId, status, message) => {
                          loadAccounts(); 
                          if (accountId !== null) {
                            let section = `email_account_edit_${accountId}`;
                            if (status && message) {
                                section += `?status=${status}&message=${encodeURIComponent(message)}`;
                            }
                            handleSelectSection(section); 
                          } else {
                            handleSelectSection('email_accounts'); 
                          }
                        }}
                        syncingAccountId={syncingAccountId}
                        onTriggerSync={handleTriggerSync}
                      />;
            } else {
              // If account not found (e.g., deleted in another tab), show message and maybe navigate
              // setTimeout(() => handleSelectSection('email_accounts'), 100); // Auto-navigate after short delay
              return <Typography>Account not found. Please select another section.</Typography>;
            }
          }
        }
        // --- UNIFY API CREDENTIAL FORMS ---
        if (selectedSection.startsWith('api_credential_edit_')) {
          const credentialId = selectedSection.replace('api_credential_edit_', '');
          
          let credentialName = 'Unknown API';
          if (credentialId === 'groq') {
            credentialName = 'Groq';
          } else if (credentialId === 'google_gemini') {
            credentialName = 'Google Gemini';
          } // Add more provider names here

          // Render the generic form
          return <ApiCredentialForm
                    credentialId={credentialId}
                    credentialName={credentialName}
                  />;
        }
        // Fallback if no section matches
        return <Typography>Select a section from the left.</Typography>;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ 
        mt: 4, 
        mb: 4, 
      }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Settings
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} sm={4} md={3}>
          <SettingsSidebar 
            accounts={accounts}
            selectedSection={selectedSection}
            onSelectSection={handleSelectSection}
            onEditAccount={handleEditAccount}
            onSyncAccount={handleTriggerSync}
            syncingAccountId={syncingAccountId}
          />
        </Grid>

        <Grid item xs={12} sm={8} md={9} sx={{
            overflow: 'auto', 
            maxHeight: 'calc(100vh - 180px)'
          }}>
          {loadingAccounts && selectedSection.startsWith('email_account') && <CircularProgress />}
          {errorAccounts && selectedSection.startsWith('email_account') && 
            <Alert severity="error" sx={{ mb: 2 }}>{errorAccounts}</Alert>
          }
          {renderContent()}
        </Grid>
      </Grid>
    </Container>
  );
};

export default SettingsPage; 