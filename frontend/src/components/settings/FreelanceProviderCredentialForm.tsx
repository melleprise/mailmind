import React, { useState, FormEvent, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  InputAdornment,
  IconButton,
  CircularProgress,
  Alert,
  Divider
} from '@mui/material';
import { Visibility, VisibilityOff, Save as SaveIcon, Delete as DeleteIcon } from '@mui/icons-material';

interface FreelanceProviderCredentialFormProps {
  initialValues?: {
    username: string;
    password?: string; // Optional, wird nie mit echtem Wert übertragen
    link_1: string;
    link_2: string;
    link_3?: string; // Neues Feld für Pagination URL 2
  };
  onSave: (values: { username: string; password: string; link_1: string; link_2: string; link_3: string }) => void;
  onDelete?: () => void;
  loading?: boolean;
  hasExistingCredentials?: boolean;
  hashedCredentials?: boolean; // Zeigt nur an, dass Passwort gespeichert ist, nicht den Wert
}

const FreelanceProviderCredentialForm: React.FC<FreelanceProviderCredentialFormProps> = ({ 
  initialValues, 
  onSave, 
  onDelete,
  loading = false,
  hasExistingCredentials = false,
  hashedCredentials = true // Standardmäßig sicherer Modus
}) => {
  const [username, setUsername] = useState(initialValues?.username || '');
  const [password, setPassword] = useState(''); // Nie vorausgefüllt
  const [link1, setLink1] = useState(initialValues?.link_1 || '');
  const [link2, setLink2] = useState(initialValues?.link_2 || '');
  const [link3, setLink3] = useState(initialValues?.link_3 || '');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Aktualisiere die Formulardaten, wenn sich initialValues ändert
  useEffect(() => {
    if (initialValues) {
      console.log("Aktualisiere Formularfelder mit:", initialValues);
      setUsername(initialValues.username || '');
      setLink1(initialValues.link_1 || '');
      setLink2(initialValues.link_2 || '');
      setLink3(initialValues.link_3 || '');
    }
  }, [initialValues]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username || (!password && !hasExistingCredentials) || !link1 || !link2 || !link3) {
      setError('Alle Felder sind erforderlich.');
      return;
    }
    
    setError(null);
    setSuccessMessage(null);
    setIsSubmitting(true);
    
    try {
      await onSave({ username, password, link_1: link1, link_2: link2, link_3: link3 });
      setSuccessMessage('Zugangsdaten erfolgreich gespeichert.');
      // Passwort nach dem Speichern immer zurücksetzen
      setPassword('');
    } catch (err: any) {
      setError(err?.message || 'Fehler beim Speichern der Zugangsdaten.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    
    setError(null);
    setSuccessMessage(null);
    setIsDeleting(true);
    
    try {
      await onDelete();
      setSuccessMessage('Zugangsdaten erfolgreich gelöscht.');
      setUsername('');
      setPassword('');
      setLink1('');
      setLink2('');
      setLink3('');
    } catch (err: any) {
      setError(err?.message || 'Fehler beim Löschen der Zugangsdaten.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      const form = event.currentTarget.closest('form');
      if (form) form.requestSubmit();
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        freelance.de Zugangsdaten
      </Typography>

      <form onSubmit={handleSubmit} autoComplete="off" noValidate>
        <TextField
          label="Username"
          value={username}
          onChange={e => {
            setUsername(e.target.value);
            setError(null);
          }}
          fullWidth
          margin="normal"
          required
          disabled={isSubmitting || isDeleting}
          onKeyDown={handleKeyDown}
          autoComplete="new-username" // Verhindert Auto-Ausfüllen
        />
        
        <TextField
          label={hasExistingCredentials ? "Neues Passwort (leer = unverändert)" : "Passwort"}
          type={showPassword ? 'text' : 'password'}
          value={password}
          onChange={e => {
            setPassword(e.target.value);
            setError(null);
          }}
          fullWidth
          margin="normal"
          required={!hasExistingCredentials} // Bei Update optional
          disabled={isSubmitting || isDeleting}
          onKeyDown={handleKeyDown}
          autoComplete="new-password" // Verhindert Auto-Ausfüllen
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label="toggle password visibility"
                  onClick={() => setShowPassword(!showPassword)}
                  onMouseDown={(e) => e.preventDefault()}
                  edge="end"
                >
                  {showPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          }}
          placeholder={hasExistingCredentials ? "Nur bei Änderung eingeben" : ""}
          helperText={hasExistingCredentials ? "Passwort ist gespeichert und verschlüsselt" : ""}
        />
        
        <TextField
          label="Login URL"
          value={link1}
          onChange={e => {
            setLink1(e.target.value);
            setError(null);
          }}
          fullWidth
          margin="normal"
          required
          disabled={isSubmitting || isDeleting}
          onKeyDown={handleKeyDown}
          autoComplete="off"
        />
        
        <TextField
          label="Pagination URL 1"
          value={link2}
          onChange={e => {
            setLink2(e.target.value);
            setError(null);
          }}
          fullWidth
          margin="normal"
          required
          disabled={isSubmitting || isDeleting}
          onKeyDown={handleKeyDown}
          autoComplete="off"
        />

        <TextField
          label="Pagination URL 2"
          value={link3}
          onChange={e => {
            setLink3(e.target.value);
            setError(null);
          }}
          fullWidth
          margin="normal"
          required
          disabled={isSubmitting || isDeleting}
          onKeyDown={handleKeyDown}
          autoComplete="off"
        />

        {error && <Alert severity="error" sx={{ mb: 2, mt: 1 }}>{error}</Alert>}
        {successMessage && <Alert severity="success" sx={{ mb: 2, mt: 1 }}>{successMessage}</Alert>}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
          <Box>
            {hasExistingCredentials && onDelete && (
              <Button
                variant="outlined"
                color="error"
                onClick={handleDelete}
                disabled={isDeleting || isSubmitting}
                startIcon={isDeleting ? <CircularProgress size={16} /> : <DeleteIcon />}
                size="small"
                type="button"
              >
                Löschen
              </Button>
            )}
          </Box>

          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={(!username || (!password && !hasExistingCredentials) || !link1 || !link2 || !link3) || isSubmitting || isDeleting}
            startIcon={isSubmitting ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
          >
            {hasExistingCredentials ? 'Aktualisieren' : 'Speichern'}
          </Button>
        </Box>
      </form>

      {hasExistingCredentials && (
        <Box sx={{ mt: 3 }}>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="subtitle1" gutterBottom>
            Status
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Zugangsdaten sind gespeichert und verschlüsselt für Crawling-Operationen verfügbar.
          </Typography>
          <Button
            variant="outlined"
            color="primary"
            sx={{ mt: 2 }}
            onClick={async () => {
              setError(null);
              setSuccessMessage(null);
              try {
                setIsSubmitting(true);
                const result = await import('../../services/api').then(m => m.freelanceCredentials.validate());
                if (result.success) {
                  setSuccessMessage('Login-Test erfolgreich!');
                } else {
                  setError('Login-Test fehlgeschlagen: ' + result.detail);
                }
              } catch (e: any) {
                setError('Fehler beim Verbindungstest: ' + (e?.message || e));
              } finally {
                setIsSubmitting(false);
              }
            }}
            disabled={isSubmitting || isDeleting}
          >
            Verbindung testen
          </Button>
        </Box>
      )}
    </Paper>
  );
};

export default FreelanceProviderCredentialForm; 