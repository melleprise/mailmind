import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom'; // Import useNavigate
// import { Helmet } from 'react-helmet-async'; // Entfernt
import { useTranslation } from 'react-i18next';
import { 
  // Grid, // Entfernt
  // Container, // Entfernt
  Typography, 
  Card, 
  CardHeader, 
  Divider, 
  CardContent, 
  Box, 
  CircularProgress, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Tooltip, 
  IconButton, 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button,
  TablePagination,
  Paper, // Paper importieren
  Alert // Import Alert
} from '@mui/material';
// import Footer from 'src/components/Footer'; // Entfernt
// import PageTitleWrapper from 'src/components/PageTitleWrapper'; // Entfernt
// import PageHeader from 'src/components/PageHeader'; // Entfernt
import VisibilityTwoToneIcon from '@mui/icons-material/VisibilityTwoTone';
import CheckCircleTwoToneIcon from '@mui/icons-material/CheckCircleTwoTone';
import CancelTwoToneIcon from '@mui/icons-material/CancelTwoTone';
import { format, parseISO } from 'date-fns';
import { de } from 'date-fns/locale';
// Entferne alte API-Imports
// import { getAiRequestLogs, getAiRequestLogDetail, AIRequestLog, AIRequestLogDetail } from 'src/services/api';
import { useFetchAIRequestLogs, useFetchAIRequestLogDetail } from '@/lib/api'; // Importiere den TanStack Query Hook
import { AIRequestLog, AIRequestLogDetail } from '@/lib/types'; // Importiere Typen
// TODO: AIRequestLogDetail muss evtl. noch in types.ts definiert werden
// TODO: Hook für Detailabruf muss noch erstellt und importiert werden (z.B. useFetchAIRequestLogDetail)

function SettingsPromptsProtocol() {
  const { t } = useTranslation();
  const navigate = useNavigate(); // Initialize useNavigate
  
  // Verwende TanStack Query Hook
  const {
    data: logsData,
    isLoading: loadingList,
    error: fetchListError,
  } = useFetchAIRequestLogs();

  // State für Dialog-Sichtbarkeit und die ID des ausgewählten Logs
  const [openDialog, setOpenDialog] = useState<boolean>(false);
  const [selectedLogId, setSelectedLogId] = useState<number | string | null>(null);

  // Verwende den neuen Hook zum Abrufen der Details
  const {
    data: selectedLog, // Enthält AIRequestLogDetail oder undefined
    isLoading: loadingDetail, 
    error: fetchDetailError, 
    isError: isDetailError // Boolean flag for error state
  } = useFetchAIRequestLogDetail(selectedLogId); // Wird nur aktiv, wenn selectedLogId gesetzt ist

  // State für Pagination
  const [page, setPage] = useState<number>(0);
  const [limit, setLimit] = useState<number>(10);

  // Extrahiere Logs und berechne count
  const logs: AIRequestLog[] = logsData || [];
  const count: number = logs.length; // Client-seitige Paginierung
  const paginatedLogs = logs.slice(page * limit, page * limit + limit);

  // Funktion für Row Click - Setzt nur noch die ID und öffnet den Dialog
  const handleRowClick = (logId: number | string) => {
    console.log(`[Protocol] Row clicked for log ID: ${logId}. Setting selected ID and opening dialog.`);
    setSelectedLogId(logId);
    setOpenDialog(true);
  };

  // handleCloseDialog Funktion
  const handleCloseDialog = () => {
    console.log("[Protocol] Closing details dialog.");
    setOpenDialog(false);
    setSelectedLogId(null); // Setze die ID zurück, deaktiviert den Detail-Query
  };

  const handlePageChange = (event: any, newPage: number): void => {
    setPage(newPage);
  };

  const handleLimitChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setLimit(parseInt(event.target.value));
    setPage(0); // Reset to first page when limit changes
  };

  // Fehlerbehandlung vom Hook
  const displayListError = fetchListError ? t('Failed to load request logs.') : null;

  // Helper function to format detail error message
  const getDetailErrorMessage = () => {
      if (!fetchDetailError) return null;
      if (fetchDetailError instanceof Error) {
          return fetchDetailError.message;
      }
      return t('An unknown error occurred while loading details.');
  };

  return (
    <>
      {/* Entferne Helmet, PageTitleWrapper, Container, Grid, Footer */}
      {/* Verwende Paper wie bei Templates */} 
      <Paper sx={{ p: 3 }}> 
        <Typography variant="h6" gutterBottom>
            {t('Prompt Protocol')}
        </Typography>
        <Divider sx={{ mb: 2 }} />

        {/* Inhalt direkt in Paper */} 
        {loadingList && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        )}
        {displayListError && (
          <Typography color="error" sx={{ p: 2 }}>
            {displayListError}
          </Typography>
        )}
        {!loadingList && !displayListError && (
          <>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>{t('Timestamp')}</TableCell>
                    <TableCell>{t('Provider')}</TableCell>
                    <TableCell>{t('Model')}</TableCell>
                    <TableCell align="center">{t('Status')}</TableCell>
                    <TableCell align="right">{t('Duration (ms)')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paginatedLogs.map((log) => (
                    <TableRow 
                      hover 
                      key={log.id}
                      onClick={() => handleRowClick(log.id)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell>
                        <Typography variant="body1" noWrap>
                          {log.timestamp ? format(parseISO(log.timestamp), 'Pp', { locale: de }) : 'Invalid Date'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body1" noWrap>
                          {log.provider}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body1" noWrap>
                          {log.model_name}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        {log.is_success ? (
                          <Tooltip title={t('Success')} arrow>
                            <CheckCircleTwoToneIcon color="success" />
                          </Tooltip>
                        ) : (
                          <Tooltip title={t('Failure')} arrow>
                            <CancelTwoToneIcon color="error" />
                          </Tooltip>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body1" noWrap>
                          {log.duration_ms !== null && log.duration_ms !== undefined ? log.duration_ms : '-'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
             <Box p={2}>
              <TablePagination
                component="div"
                count={count}
                onPageChange={handlePageChange}
                onRowsPerPageChange={handleLimitChange}
                page={page}
                rowsPerPage={limit}
                rowsPerPageOptions={[5, 10, 25, 50]}
              />
            </Box>
          </>
        )}
      </Paper>
      {/* Detail Dialog - verwendet jetzt den State vom useFetchAIRequestLogDetail Hook */}
      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>{t('Request Details')}</DialogTitle>
        <DialogContent dividers>
           {/* Ladeanzeige für Details */}
           {loadingDetail && <CircularProgress sx={{ display: 'block', margin: 'auto'}} />}
           {/* Fehleranzeige für Details */}
           {isDetailError && !loadingDetail && <Alert severity="error">{getDetailErrorMessage()}</Alert>}
           {/* Detailanzeige, wenn geladen und kein Fehler */}
           {!loadingDetail && !isDetailError && selectedLog && (
            <Box sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}> 
              <Typography variant="h6" gutterBottom>{t('Prompt Sent')}:</Typography>
              <Box sx={{ p: 1, border: '1px dashed grey', mb: 2, overflowX: 'auto' }}>
                {selectedLog.prompt_text || t('Prompt not recorded.')}
              </Box>
              
              <Typography variant="h6" gutterBottom>{t('Raw Response Received')}:</Typography>
              <Box sx={{ p: 1, border: '1px dashed grey', mb: 2, overflowX: 'auto' }}>
                 {selectedLog.raw_response_text || t('No response recorded.')}
              </Box>

              <Typography variant="h6" gutterBottom>{t('Details')}:</Typography>
              <Box sx={{ p: 1, border: '1px dashed grey', mb: 2 }}>
                 Timestamp: {selectedLog.timestamp ? format(parseISO(selectedLog.timestamp), 'Pp', { locale: de }) : 'N/A'}<br/>
                 User: {selectedLog.user_email || 'N/A'}<br/>
                 Provider: {selectedLog.provider}<br/>
                 Model: {selectedLog.model_name}<br/>
                 Status: {selectedLog.is_success ? 'Success' : 'Failure'}<br/>
                 Duration: {selectedLog.duration_ms !== null && selectedLog.duration_ms !== undefined ? `${selectedLog.duration_ms} ms` : '-'}<br/>
                 Trigger Source: {selectedLog.triggering_source || 'N/A'}<br/>
                 Status Code: {selectedLog.status_code ?? 'N/A'}<br/>
                 Error Message: {selectedLog.error_message || 'None'}
              </Box>
            </Box>
           )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>{t('Close')}</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default SettingsPromptsProtocol; 