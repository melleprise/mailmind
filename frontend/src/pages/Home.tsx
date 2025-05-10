import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Typography,
  Button,
  Box,
  Paper,
} from '@mui/material';

const Home: React.FC = () => {
  return (
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
};

export default Home; 