import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Button } from '@mui/material';

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="100vh"
      textAlign="center"
      p={3}
    >
      <Typography variant="h1" component="h1" gutterBottom>
        404
      </Typography>
      <Typography variant="h4" component="h2" gutterBottom>
        Page Not Found
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        The page you are looking for doesn't exist or has been moved.
      </Typography>
      <Button
        variant="contained"
        color="primary"
        onClick={() => navigate('/emails')}
        sx={{ mt: 2 }}
      >
        Go to Email List
      </Button>
    </Box>
  );
};

export default NotFound; 