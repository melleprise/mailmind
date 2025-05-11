import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Box, Container, CircularProgress, CssBaseline, GlobalStyles, Typography, Button, Paper } from '@mui/material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AppThemeProvider } from './contexts/ThemeContext';
import Navbar from './components/Navbar';
import Subheader from './components/Subheader';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import VerifyEmail from './pages/VerifyEmail';
import AddEmailAccount from './pages/AddEmailAccount';
import SettingsPage from './pages/SettingsPage';
import SettingsPrompts from './pages/SettingsPrompts';
import ResendVerification from './pages/ResendVerification';
import AISearchPage from './pages/AISearchPage';
import LeadsPage from './pages/LeadsPage';
import { I18nextProvider } from 'react-i18next';
import i18n from './i18n';
import MailIcon from '@mui/icons-material/Mail';
import { Link as RouterLink } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
};

const HomeLoggedOut: React.FC = () => (
  <Container maxWidth="md">
    <Box
      sx={{
        mt: 8,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      <Paper
        elevation={3}
        sx={{
          p: 4,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <Typography variant="h3" component="h1" gutterBottom>
          Welcome to Email AI Mind
        </Typography>
        <Typography variant="h5" component="h2" gutterBottom>
          Your Smart Email Assistant
        </Typography>
        <Typography variant="body1" paragraph>
          Let AI help you manage your emails efficiently. Swipe right to keep,
          left to archive, and get smart suggestions for quick responses.
        </Typography>
        <Box sx={{ mt: 3 }}>
          <Button
            variant="contained"
            color="primary"
            size="large"
            component={RouterLink}
            to="/register"
            sx={{ mr: 2 }}
          >
            Get Started
          </Button>
          <Button
            variant="outlined"
            color="primary"
            size="large"
            component={RouterLink}
            to="/login"
          >
            Login
          </Button>
        </Box>
      </Paper>
    </Box>
  </Container>
);

const AppRoutes: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  return (
    <Box 
      component="div"
      sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        minHeight: '100vh',
        maxWidth: '100vw',
        overflow: 'hidden',
        margin: 0,
        padding: 0,
      }}
    >
      <Navbar />
      {location.pathname === '/aisearch' && <Subheader />}
      <Box 
        component="main" 
        sx={{ 
          flex: 1,
          display: 'flex',
          width: '100vw',
          maxWidth: '100vw',
          overflow: 'hidden',
          margin: 0,
          padding: 0,
        }}
      >
        <I18nextProvider i18n={i18n}>
          <Routes>
            <Route path="/" element={
              isAuthenticated ? <Navigate to="/leads" replace /> : <HomeLoggedOut />
            } />
            <Route path="/login" element={
              <Box sx={{ width: '100%', margin: 0, padding: 0 }}>
                <Login />
              </Box>
            } />
            <Route path="/register" element={
              <Box sx={{ width: '100%', margin: 0, padding: 0 }}>
                <Register />
              </Box>
            } />
            <Route path="/verify-email/:token" element={
              <Box sx={{ width: '100%', margin: 0, padding: 0 }}>
                <VerifyEmail />
              </Box>
            } />
            <Route path="/settings/add-account" element={
               <ProtectedRoute>
                 <Box sx={{ width: '100%', margin: 0, padding: 0 }}>
                   <AddEmailAccount />
                 </Box>
               </ProtectedRoute>
            } />
            <Route 
              path="/settings"
              element={ 
                <ProtectedRoute>
                  <Box sx={{ width: '100%', margin: 0, padding: 0 }}>
                    <SettingsPage />
                  </Box>
                </ProtectedRoute>
              }
            />
            <Route 
              path="/settings/prompts"
              element={ 
                <ProtectedRoute>
                  <Box sx={{ width: '100%', margin: 0, padding: 0 }}>
                    <SettingsPrompts />
                  </Box>
                </ProtectedRoute>
              }
            />
            <Route path="/resend-verification" element={
              <Box sx={{ width: '100%', margin: 0, padding: 0 }}>
                <ResendVerification />
              </Box>
            } />
            <Route path="/dashboard" element={<Navigate to="/mail" replace />} />
            <Route
              path="/mail"
              element={
                <ProtectedRoute>
                  <Box sx={{ 
                    width: '100vw', 
                    maxWidth: '100vw',
                    margin: 0,
                    padding: 0,
                    overflow: 'hidden',
                  }}>
                    <Dashboard />
                  </Box>
                </ProtectedRoute>
              }
            />
            <Route
              path="/leads"
              element={
                <ProtectedRoute>
                  <Box sx={{ 
                    width: '100vw', 
                    maxWidth: '100vw',
                    margin: 0,
                    padding: 0,
                    overflow: 'hidden',
                    height: 'calc(100vh - 64px)',
                  }}>
                    <LeadsPage />
                  </Box>
                </ProtectedRoute>
              }
            />
            <Route
              path="/aisearch"
              element={
                <ProtectedRoute>
                  <Box sx={{ 
                    width: '100vw', 
                    maxWidth: '100vw',
                    height: 'calc(100vh - 112px)',
                    margin: 0,
                    padding: 0,
                    overflowY: 'auto',
                  }}>
                    <AISearchPage />
                  </Box>
                </ProtectedRoute>
              }
            />
          </Routes>
        </I18nextProvider>
      </Box>
    </Box>
  );
};

const globalStyles = (
  <GlobalStyles
    styles={{
      body: {
        overflow: 'hidden',
        margin: 0,
        padding: 0,
        width: '100vw',
        height: '100vh',
        maxWidth: '100%',
      },
      '#root': {
        height: '100vh',
        width: '100vw',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        maxWidth: '100%',
      }
    }}
  />
);

const App: React.FC = () => {
  return (
    <AppThemeProvider>
      <AuthProvider>
        <>
          <CssBaseline />
          {globalStyles}
          <Box sx={{ 
            display: 'flex',
            flexDirection: 'column',
            width: '100vw',
            maxWidth: '100vw',
            margin: 0,
            padding: 0,
            overflow: 'hidden',
            bgcolor: 'background.default',
          }}>
            <AppRoutes />
          </Box>
        </>
      </AuthProvider>
    </AppThemeProvider>
  );
};

export default App; 