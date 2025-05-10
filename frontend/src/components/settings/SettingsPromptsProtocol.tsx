import React, { useState } from 'react';
import {
  Box,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  TablePagination,
  Paper,
  Chip,
  Tooltip,
  IconButton,
  Collapse,
  Alert
} from '@mui/material';
import { useFetchAIRequestLogs } from '@/lib/api';
import { AIRequestLog } from '@/lib/types';
import { format } from 'date-fns';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';

// Helper Row component for expandable details
const LogRow: React.FC<{ log: AIRequestLog }> = ({ log }) => {
  const [open, setOpen] = useState(false);

  return (
    <React.Fragment>
      <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell>
          <IconButton
            aria-label="expand row"
            size="small"
            onClick={() => setOpen(!open)}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          {log.timestamp ? format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss') : 'N/A'}
        </TableCell>
        <TableCell>{log.user_email || log.user || 'N/A'}</TableCell>
        <TableCell>{log.provider || 'N/A'} / {log.model_name || 'N/A'}</TableCell>
        <TableCell align="center">
          <Chip 
            label={log.is_success ? 'Success' : 'Fail'} 
            color={log.is_success ? 'success' : 'error'} 
            size="small" 
          />
        </TableCell>
        <TableCell align="right">{log.duration_ms !== null ? `${log.duration_ms} ms` : 'N/A'}</TableCell>
        <TableCell>{log.triggering_source || 'N/A'}</TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={7}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
              <Typography variant="h6" gutterBottom component="div">
                Details
              </Typography>
              <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace', maxHeight: '200px', overflowY: 'auto', mb: 1, p: 1, border: '1px solid', borderColor: 'divider' }}>
                <strong>Prompt:</strong><br />
                {log.prompt_text || 'N/A'}
              </Typography>
              <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace', maxHeight: '200px', overflowY: 'auto', mb: 1, p: 1, border: '1px solid', borderColor: 'divider' }}>
                <strong>Raw Response:</strong><br />
                {log.raw_response_text || 'N/A'}
              </Typography>
              {log.error_message && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  <strong>Error Message:</strong> {log.error_message}
                </Alert>
              )}
              <Typography variant="caption" display="block" gutterBottom>
                 Status Code: {log.status_code ?? 'N/A'} | Request ID: {log.id} 
              </Typography>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </React.Fragment>
  );
};


function SettingsPromptsProtocol() {
  const [page, setPage] = useState<number>(0);
  const [limit, setLimit] = useState<number>(10);

  const {
    data: logData,
    isLoading,
    error,
    refetch // Funktion zum Neuladen hinzufügen
  } = useFetchAIRequestLogs();

  const logs: AIRequestLog[] = logData || [];
  const count: number = logs.length;

  const handlePageChange = (event: unknown, newPage: number): void => {
    setPage(newPage);
  };

  const handleLimitChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setLimit(parseInt(event.target.value, 10));
    setPage(0);
  };
  
  // Logs nach Timestamp absteigend sortieren (neueste zuerst)
  const sortedLogs = logs.sort((a, b) => 
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
  const paginatedLogs = sortedLogs.slice(page * limit, page * limit + limit);

  const displayError = error ? 'Failed to load request logs.' : null;

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" gutterBottom component="div">
          Prompt Protocol
        </Typography>
        <Button variant="outlined" onClick={() => refetch()} disabled={isLoading}>
          {isLoading ? 'Loading...' : 'Refresh Logs'}
        </Button>
      </Box>
      <Divider sx={{ mb: 2 }} />

      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      )}
      {displayError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {displayError}
        </Alert>
      )}
      {!isLoading && !displayError && (
        <>
          <TableContainer>
            <Table stickyHeader aria-label="collapsible table">
              <TableHead>
                <TableRow>
                  <TableCell /> {/* For expand button */}
                  <TableCell>Timestamp</TableCell>
                  <TableCell>User</TableCell>
                  <TableCell>Provider/Model</TableCell>
                  <TableCell align="center">Status</TableCell>
                  <TableCell align="right">Duration</TableCell>
                  <TableCell>Source</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedLogs.map((log) => (
                  <LogRow key={log.id} log={log} />
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={count}
            onPageChange={handlePageChange}
            onRowsPerPageChange={handleLimitChange}
            page={page}
            rowsPerPage={limit}
            rowsPerPageOptions={[10, 25, 50, 100]}
          />
        </>
      )}
    </Paper>
  );
}

export default SettingsPromptsProtocol; 