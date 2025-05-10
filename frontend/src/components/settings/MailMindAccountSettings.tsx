import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert
} from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';
// TODO: Import API service for password reset when available

const MailMindAccountSettings: React.FC = () => {
  const { user } = useAuth();
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [loadingReset, setLoadingReset] = useState<boolean>(false);

  const handlePasswordReset = async () => {
    setLoadingReset(true);
    setResetMessage(null);
    setResetError(null);
    console.log("Password reset requested for:", user?.email);
    
    // TODO: Implement API call for password reset
    // try {
    //   const response = await api.requestPasswordReset(user?.email);
    //   setResetMessage("Password reset email sent. Please check your inbox.");
    // } catch (error) {
    //   setResetError("Failed to send password reset email. Please try again later.");
    // } finally {
    //   setLoadingReset(false);
    // }

    // Placeholder logic
    setTimeout(() => {
      setResetMessage("Password reset functionality not yet implemented. (Placeholder)");
      setLoadingReset(false);
    }, 1000);
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        MailMind Account
      </Typography>

      <TextField
        label="Email Address"
        value={user?.email || ''}
        fullWidth
        margin="normal"
        InputProps={{
          readOnly: true,
        }}
        variant="outlined"
      />

      <Box sx={{ mt: 3 }}>
        <Button 
          variant="contained" 
          onClick={handlePasswordReset}
          disabled={loadingReset || !user?.email}
        >
          {loadingReset ? 'Sending...' : 'Reset Password'}
        </Button>
        {resetMessage && (
          <Alert severity="success" sx={{ mt: 2 }}>{resetMessage}</Alert>
        )}
        {resetError && (
          <Alert severity="error" sx={{ mt: 2 }}>{resetError}</Alert>
        )}
      </Box>
    </Paper>
  );
};

export default MailMindAccountSettings; 