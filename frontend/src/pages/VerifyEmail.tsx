import React, { useState, useEffect } from 'react';
import { useParams, Link as RouterLink, useNavigate } from 'react-router-dom';
import { Container, Typography, Box, Alert, CircularProgress, Button } from '@mui/material';
import { authApi } from '../services/api';
import { getErrorMessage } from '../utils/error';

const VerifyEmail: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [verifiedAttempted, setVerifiedAttempted] = useState(false);

  useEffect(() => {
    const verify = async () => {
      if (!token) {
        setError('Verification token is missing.');
        setLoading(false);
        setVerifiedAttempted(true);
        return;
      }

      if (verifiedAttempted) return;

      setLoading(true);
      setError(null);
      setSuccess(null);
      setVerifiedAttempted(true);

      try {
        const response = await authApi.verifyEmail(token);
        setSuccess(response.message || 'Email successfully verified. Redirecting to login...');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    verify();
  }, [token, verifiedAttempted, navigate]);

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          mt: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <Typography component="h1" variant="h5" gutterBottom>
          Email Verification
        </Typography>

        {loading && <CircularProgress sx={{ mt: 4 }} />}

        {!loading && success && (
          <Box sx={{ mt: 4 }}>
            <Alert severity="success">{success}</Alert>
            <Button
              component={RouterLink}
              to="/login"
              variant="contained"
              sx={{ mt: 3 }}
            >
              Go to Login
            </Button>
          </Box>
        )}

        {!loading && error && (
          <Box sx={{ mt: 4 }}>
            <Alert severity="error">{error}</Alert>
            <Button
              component={RouterLink}
              to="/register"
              variant="outlined"
              sx={{ mt: 3 }}
            >
              Try Registering Again
            </Button>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default VerifyEmail; 