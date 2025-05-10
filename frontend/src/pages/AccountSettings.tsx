import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  IconButton,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { api } from '../services/api';
import EmailAccountList from '../components/settings/EmailAccountList';

interface EmailAccount {
  id: number;
  name: string;
  email: string;
  provider: string;
  imap_server: string;
  imap_port: number;
  smtp_server: string;
  smtp_port: number;
  use_oauth: boolean;
  imap_use_ssl: boolean;
  smtp_use_tls: boolean;
}

interface AccountFormData {
  name: string;
  email: string;
  provider: string;
  imap_server: string;
  imap_port: number;
  imap_use_ssl: boolean;
  smtp_server: string;
  smtp_port: number;
  smtp_use_tls: boolean;
  password?: string;
  username?: string;
}

const KNOWN_PROVIDER_DOMAINS = ['gmail.com', 'googlemail.com', 'outlook.com', 'hotmail.com', 'live.com']; // Add more if needed

const AccountSettings: React.FC = () => {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState<AccountFormData>({
    name: '',
    email: '',
    provider: '',
    imap_server: '',
    imap_port: 993,
    imap_use_ssl: true,
    smtp_server: '',
    smtp_port: 587,
    smtp_use_tls: true,
  });
  const [isTesting, setIsTesting] = useState(false);
  const [syncingAccountId, setSyncingAccountId] = useState<number | null>(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.emailAccounts.list();
      setAccounts(response.data as EmailAccount[]);
    } catch (err) {
      setError('Fehler beim Laden der E-Mail-Konten');
      console.error("Load Accounts Error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddAccount = () => {
    setFormData({
      name: '',
      email: '',
      provider: '',
      imap_server: '',
      imap_port: 993,
      imap_use_ssl: true,
      smtp_server: '',
      smtp_port: 587,
      smtp_use_tls: true,
      password: '',
    });
    setError(null);
    setIsDialogOpen(true);
  };

  const handleSubmit = async () => {
    setError(null);
    try {
      setIsTesting(true);
      const response = await api.emailAccounts.create(formData);
      await loadAccounts();
      setIsDialogOpen(false);

      if (response.data && response.data.id) {
        handleSync(response.data.id);
      } else {
        console.warn("Account created, but ID missing in response for initial sync.");
      }
    } catch (err: any) {
      console.error("Submit Account Error:", err);
      const errorMsg = err.response?.data?.detail || err.message || 'Fehler beim Hinzufügen des E-Mail-Kontos';
      setError(errorMsg);
    } finally {
      setIsTesting(false);
    }
  };

  const handleDelete = async (accountId: number) => {
    if (!window.confirm('Möchten Sie dieses E-Mail-Konto wirklich löschen?')) {
      return;
    }
    setError(null);
    try {
      await api.emailAccounts.delete(accountId);
      await loadAccounts();
    } catch (err) {
      setError('Fehler beim Löschen des E-Mail-Kontos');
      console.error("Delete Account Error:", err);
    }
  };

  const handleSync = async (accountId: number) => {
    console.log(`[AccountSettings] handleSync called for account ID: ${accountId}`);
    setError(null);
    setSyncingAccountId(accountId);
    try {
      console.log(`[AccountSettings] Calling api.emailAccounts.sync(${accountId})...`);
      const response = await api.emailAccounts.sync(accountId);
      console.log(`[AccountSettings] api.emailAccounts.sync(${accountId}) successful:`, response);
      alert('Synchronisation gestartet!');
    } catch (err: any) {
      console.error(`[AccountSettings] Error in api.emailAccounts.sync(${accountId}):`, err);
      if (err.response) {
        console.error('[AccountSettings] Error response data:', err.response.data);
        console.error('[AccountSettings] Error response status:', err.response.status);
        console.error('[AccountSettings] Error response headers:', err.response.headers);
        setError(`Fehler vom Server: ${err.response.data?.error || err.response.data?.detail || err.response.statusText} (Status: ${err.response.status})`);
      } else if (err.request) {
        console.error('[AccountSettings] Error request:', err.request);
        setError('Fehler: Keine Antwort vom Server erhalten.');
      } else {
        console.error('[AccountSettings] Error message:', err.message);
        setError(`Fehler beim Starten der Synchronisation: ${err.message}`);
      }
    } finally {
      console.log(`[AccountSettings] handleSync finally block for account ID: ${accountId}`);
      setSyncingAccountId(null);
    }
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newEmail = e.target.value;
    const domain = newEmail.split('@')[1]?.toLowerCase();
    let newProvider = formData.provider;

    if (domain) {
      if (KNOWN_PROVIDER_DOMAINS.includes(domain)) {
        if (domain.includes('gmail')) newProvider = 'gmail';
        else newProvider = 'outlook';
      } else {
        newProvider = 'custom';
      }
    } else {
      newProvider = '';
    }

    handleProviderChange(newProvider, newEmail);
  };

  const handleProviderChange = (provider: string, currentEmail?: string) => {
    const emailToUse = currentEmail !== undefined ? currentEmail : formData.email;
    const serverSettings = {
      gmail: {
        imap_server: 'imap.gmail.com',
        imap_port: 993,
        imap_use_ssl: true,
        smtp_server: 'smtp.gmail.com',
        smtp_port: 587,
        smtp_use_tls: true,
      },
      outlook: {
        imap_server: 'outlook.office365.com',
        imap_port: 993,
        imap_use_ssl: true,
        smtp_server: 'smtp.office365.com',
        smtp_port: 587,
        smtp_use_tls: true,
      },
      custom: {
        imap_server: '',
        imap_port: 993,
        imap_use_ssl: true,
        smtp_server: '',
        smtp_port: 587,
        smtp_use_tls: true,
      },
      '': {
        imap_server: '',
        imap_port: 993,
        imap_use_ssl: true,
        smtp_server: '',
        smtp_port: 587,
        smtp_use_tls: true,
      }
    }[provider];

    setFormData({
      ...formData,
      email: emailToUse,
      provider,
      ...(serverSettings || {}),
    });
  };

  const handleEdit = (account: EmailAccount) => {
    console.log("Edit account:", account);
    alert("Edit functionality not implemented yet.");
  };

  if (loading && accounts.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5">E-Mail-Konten</Typography>
        <Button
          variant="contained"
          onClick={handleAddAccount}
        >
          Konto hinzufügen
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <EmailAccountList
        accounts={accounts}
        loading={loading && accounts.length > 0}
        error={null}
        syncingAccountId={syncingAccountId}
        onDelete={handleDelete}
        onEdit={handleEdit}
        onSync={handleSync}
      />

      <Dialog open={isDialogOpen} onClose={() => setIsDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Neues E-Mail-Konto hinzufügen</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <Box sx={{ display: 'grid', gap: 2, mt: 2 }}>
            <TextField
              label="Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
            />
            <TextField
              label="E-Mail"
              type="email"
              value={formData.email}
              onChange={handleEmailChange}
              fullWidth
              required
            />
            <TextField
              label="Passwort / App Passwort"
              type="password"
              value={formData.password || ''}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              fullWidth
              required
              helperText="Für Gmail/Outlook bei aktivierter 2FA bitte ein App-Passwort verwenden."
            />
            <FormControl fullWidth>
              <InputLabel id="provider-select-label">Provider</InputLabel>
              <Select
                labelId="provider-select-label"
                value={formData.provider}
                onChange={(e) => handleProviderChange(e.target.value as string)}
                label="Provider"
                displayEmpty
                required
              >
                <MenuItem value="" disabled>-- Provider wählen --</MenuItem>
                <MenuItem value="gmail">Gmail</MenuItem>
                <MenuItem value="outlook">Outlook</MenuItem>
                <MenuItem value="custom">Custom / Manual</MenuItem>
              </Select>
            </FormControl>

            {formData.provider === 'custom' && (
              <>
                <Typography variant="subtitle1" sx={{ mt: 1, mb: -1 }}>Manuelle Servereinstellungen:</Typography>
                <TextField
                  label="IMAP Server"
                  value={formData.imap_server}
                  onChange={(e) => setFormData({ ...formData, imap_server: e.target.value })}
                  fullWidth
                  required={formData.provider === 'custom'}
                />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    label="IMAP Port"
                    type="number"
                    value={formData.imap_port}
                    onChange={(e) => setFormData({ ...formData, imap_port: parseInt(e.target.value, 10) || 0 })}
                    required={formData.provider === 'custom'}
                  />
                  <FormControl fullWidth required={formData.provider === 'custom'}>
                    <InputLabel id="imap-ssl-label">IMAP SSL/TLS</InputLabel>
                    <Select
                      labelId="imap-ssl-label"
                      value={formData.imap_use_ssl ? 'yes' : 'no'}
                      label="IMAP SSL/TLS"
                      onChange={(e) => setFormData({ ...formData, imap_use_ssl: e.target.value === 'yes'})}
                    >
                      <MenuItem value="yes">Ja</MenuItem>
                      <MenuItem value="no">Nein</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
                <TextField
                  label="SMTP Server"
                  value={formData.smtp_server}
                  onChange={(e) => setFormData({ ...formData, smtp_server: e.target.value })}
                  fullWidth
                  required={formData.provider === 'custom'}
                />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    label="SMTP Port"
                    type="number"
                    value={formData.smtp_port}
                    onChange={(e) => setFormData({ ...formData, smtp_port: parseInt(e.target.value, 10) || 0 })}
                    required={formData.provider === 'custom'}
                  />
                  <FormControl fullWidth required={formData.provider === 'custom'}>
                    <InputLabel id="smtp-tls-label">SMTP STARTTLS</InputLabel>
                    <Select
                      labelId="smtp-tls-label"
                      value={formData.smtp_use_tls ? 'yes' : 'no'}
                      label="SMTP STARTTLS"
                      onChange={(e) => setFormData({ ...formData, smtp_use_tls: e.target.value === 'yes' })}
                    >
                      <MenuItem value="yes">Ja</MenuItem>
                      <MenuItem value="no">Nein</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
                <TextField
                  label="Benutzername (IMAP/SMTP)"
                  value={formData.username || ''}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  fullWidth
                  required={formData.provider === 'custom'}
                  helperText="Oft identisch mit E-Mail-Adresse"
                />
              </>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsDialogOpen(false)} disabled={isTesting}>Abbrechen</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={isTesting}>
            {isTesting ? <CircularProgress size={24} /> : 'Speichern & Verbinden'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AccountSettings; 