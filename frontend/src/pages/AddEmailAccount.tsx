import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container, Typography, TextField, Button, Box, Paper, Alert, CircularProgress, 
  FormControlLabel, Checkbox, Grid, Switch
} from '@mui/material';
import { emailAccounts } from '../services/api'; // Import der API-Funktionen
import { getErrorMessage } from '../utils/error';

// Interface passend zur API-Funktion
interface EmailAccountFormData {
  email: string;
  imap_server: string;
  imap_port: number;
  imap_use_ssl: boolean;
  username: string;
  password: string;
  // Optional: Felder für SMTP, Account-Name etc.
  account_name?: string;
  smtp_server?: string;
  smtp_port?: number;
  smtp_use_tls?: boolean;
}

const AddEmailAccount: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<EmailAccountFormData>({
    email: '',
    imap_server: '',
    imap_port: 993,
    imap_use_ssl: true,
    username: '', 
    password: '',
    account_name: '', 
    smtp_server: '', // Optional
    smtp_port: 587, // Optional
    smtp_use_tls: true, // Optional
  });
  const [formErrors, setFormErrors] = useState<Partial<EmailAccountFormData>>({});
  const [apiResult, setApiResult] = useState<{ status: 'success' | 'error' | 'validation_error'; message: string; errors?: any } | null>(null);
  const [loading, setLoading] = useState(false);

  // Einfache Client-seitige Validierung (kann erweitert werden)
  const validateForm = (): boolean => {
    const errors: Partial<EmailAccountFormData> = {};
    if (!formData.email) errors.email = 'Email is required';
    if (!formData.imap_server) errors.imap_server = 'IMAP Server is required';
    if (!formData.imap_port) errors.imap_port = 'IMAP Port is required';
    if (!formData.username) errors.username = 'Username is required';
    if (!formData.password) errors.password = 'Password is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    // Behandlung für Checkbox/Switch
    const isCheckbox = type === 'checkbox';
    const targetValue = isCheckbox ? (e.target as HTMLInputElement).checked : value;
    
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? Number(targetValue) : targetValue,
    }));
    // Fehler für dieses Feld löschen
    if (formErrors[name as keyof EmailAccountFormData]) {
      setFormErrors(prev => ({ ...prev, [name]: undefined }));
    }
    setApiResult(null); // API-Ergebnis bei Änderung zurücksetzen
  };

  const handleTestConnection = async () => {
    setApiResult(null);
    if (!validateForm()) return;

    setLoading(true);
    try {
      // Nur die für den Test relevanten Daten senden
      const testData = {
        email: formData.email,
        imap_server: formData.imap_server,
        imap_port: formData.imap_port,
        imap_use_ssl: formData.imap_use_ssl,
        username: formData.username,
        password: formData.password,
      };
      const response = await emailAccounts.testConnection(testData);
      setApiResult({ status: response.data.status, message: response.data.message });
    } catch (error: any) {
      // Fehler vom Backend anzeigen, wenn vorhanden, sonst generische Meldung
      const backendError = error.response?.data;
      if (backendError && backendError.status) {
         setApiResult({ 
           status: backendError.status, 
           message: backendError.message || 'An error occurred.', 
           errors: backendError.errors 
         });
      } else {
        setApiResult({ status: 'error', message: getErrorMessage(error) });
      }
    } finally {
      setLoading(false);
    }
  };

  // Dummy-Funktion fürs Speichern (später implementieren)
  const handleSaveAccount = () => {
    alert('Save functionality not implemented yet.');
    // Hier käme später der API-Call zum tatsächlichen Speichern
    // const response = await emailAccounts.create(formData);
    // navigate('/settings/accounts'); // oder wohin auch immer
  };

  return (
    <Container component="main" maxWidth="md">
      <Paper elevation={3} sx={{ p: 4, mt: 4 }}>
        <Typography component="h1" variant="h5" gutterBottom>
          Add New Email Account
        </Typography>

        {apiResult && (
          <Alert 
             severity={apiResult.status === 'success' ? 'success' : 'error'}
             sx={{ mb: 2 }}
           >
             {apiResult.message}
             {/* Optional: Detaillierte Validierungsfehler anzeigen */}
             {apiResult.status === 'validation_error' && apiResult.errors && (
               <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                 {JSON.stringify(apiResult.errors, null, 2)}
               </pre>
             )}
           </Alert>
        )}

        <Box component="form" noValidate sx={{ mt: 1 }}>
          <Grid container spacing={2}>
            {/* Allgemeine Infos */}
            <Grid item xs={12} sm={6}>
              <TextField
                name="account_name"
                label="Account Name (optional)"
                fullWidth
                value={formData.account_name}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                required
                name="email"
                label="Email Address"
                fullWidth
                value={formData.email}
                onChange={handleChange}
                error={!!formErrors.email}
                helperText={formErrors.email}
              />
            </Grid>
            
            {/* IMAP Settings */}
            <Grid item xs={12}><Typography variant="h6" sx={{mt: 2}}>IMAP (Incoming Mail)</Typography></Grid>
            <Grid item xs={12} sm={8}>
              <TextField
                required
                name="imap_server"
                label="IMAP Server"
                fullWidth
                value={formData.imap_server}
                onChange={handleChange}
                error={!!formErrors.imap_server}
                helperText={formErrors.imap_server}
              />
            </Grid>
            <Grid item xs={6} sm={2}>
              <TextField
                required
                name="imap_port"
                label="Port"
                type="number"
                fullWidth
                value={formData.imap_port}
                onChange={handleChange}
                error={!!formErrors.imap_port}
                helperText={formErrors.imap_port}
              />
            </Grid>
             <Grid item xs={6} sm={2} sx={{ display: 'flex', alignItems: 'center' }}>
               <FormControlLabel
                 control={<Switch checked={formData.imap_use_ssl} onChange={handleChange} name="imap_use_ssl" />}
                 label="Use SSL"
               />
             </Grid>

            {/* SMTP Settings (Optional fürs Erste) */}
            <Grid item xs={12}><Typography variant="h6" sx={{mt: 2}}>SMTP (Outgoing Mail - Optional)</Typography></Grid>
             <Grid item xs={12} sm={8}>
               <TextField
                 name="smtp_server"
                 label="SMTP Server"
                 fullWidth
                 value={formData.smtp_server}
                 onChange={handleChange}
               />
             </Grid>
             <Grid item xs={6} sm={2}>
               <TextField
                 name="smtp_port"
                 label="Port"
                 type="number"
                 fullWidth
                 value={formData.smtp_port}
                 onChange={handleChange}
               />
             </Grid>
             <Grid item xs={6} sm={2} sx={{ display: 'flex', alignItems: 'center' }}>
               <FormControlLabel
                 control={<Switch checked={formData.smtp_use_tls} onChange={handleChange} name="smtp_use_tls" />}
                 label="Use TLS"
               />
             </Grid>

            {/* Credentials */}
             <Grid item xs={12}><Typography variant="h6" sx={{mt: 2}}>Credentials</Typography></Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                required
                name="username"
                label="Username"
                fullWidth
                value={formData.username}
                onChange={handleChange}
                error={!!formErrors.username}
                helperText={formErrors.username || "Usually your full email address"}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                required
                name="password"
                label="Password / App Password"
                type="password"
                fullWidth
                value={formData.password}
                onChange={handleChange}
                error={!!formErrors.password}
                helperText={formErrors.password}
              />
            </Grid>
          </Grid>

          {/* Buttons */}
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
            <Button
              variant="outlined"
              onClick={handleTestConnection}
              disabled={loading}
              sx={{ mr: 1 }}
            >
              {loading ? <CircularProgress size={24} /> : 'Test Connection'}
            </Button>
            <Button
              variant="contained"
              onClick={handleSaveAccount}
              disabled={loading || apiResult?.status !== 'success'} // Nur Speichern, wenn Test erfolgreich war
            >
              Save Account
            </Button>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
};

export default AddEmailAccount; 