import React from 'react';
import {
    Box
    // Removed unused imports: Typography, Button, Paper, CircularProgress, Alert,
    // Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip
} from '@mui/material';
// Removed unused imports: useQuery, queryKeys, AIRequestLog, getAiRequestLogs
import ActionList from '../actions/ActionList';

const AIActionSettings: React.FC = () => {

    // Removed useQuery hook for logs
    // Removed LogTableRow component definition

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <ActionList />
            {/* Removed AI Request Log Paper section */}
        </Box>
    );
};

// Removed LogTableRow component

export default AIActionSettings; 