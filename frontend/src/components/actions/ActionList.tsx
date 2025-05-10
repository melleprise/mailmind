import React, { useState } from 'react';
import { Box, Typography, Button, Paper, List, ListItem, ListItemText, ListItemSecondaryAction, CircularProgress, IconButton, Tooltip, Grid, Switch } from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { getAIActions, runAIAction, deleteAIAction, AIAction, updateAIAction } from '../../services/actionsService';
import { queryKeys } from '../../lib/queryKeys';
import ActionForm from './ActionForm'; // Importieren für Modal
import ConfirmationDialog from '../common/ConfirmationDialog'; // Angenommen, es gibt eine solche Komponente

const ActionList: React.FC = () => {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const [runningActionId, setRunningActionId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingAction, setEditingAction] = useState<AIAction | null>(null);
  const [deleteActionId, setDeleteActionId] = useState<number | null>(null);

  // Daten abrufen
  const { data: actions, isLoading, error } = useQuery<AIAction[], Error>({
    queryKey: queryKeys.aiActions,
    queryFn: getAIActions,
  });

  // Action ausführen
  const runActionMutation = useMutation<any, Error, number>({
    mutationFn: runAIAction,
    onSuccess: (data, actionId) => {
      enqueueSnackbar(`Action '${data.action}' gestartet.`, { variant: 'success' });
      setRunningActionId(null);
    },
    onError: (error: Error, actionId) => {
      enqueueSnackbar(`Fehler beim Starten der Action: ${error.message}`, { variant: 'error' });
      setRunningActionId(null);
    },
  });

  // Action löschen
  const deleteActionMutation = useMutation<void, Error, number>({
    mutationFn: deleteAIAction,
    onSuccess: () => {
      enqueueSnackbar('Action erfolgreich gelöscht.', { variant: 'success' });
      queryClient.invalidateQueries({ queryKey: queryKeys.aiActions }); // Aktualisiert die Liste
      setDeleteActionId(null);
    },
    onError: (error: Error) => {
      enqueueSnackbar(`Fehler beim Löschen der Action: ${error.message}`, { variant: 'error' });
      setDeleteActionId(null);
    },
  });

  // Action aktivieren/deaktivieren
  const toggleActiveMutation = useMutation<AIAction, Error, { id: number; isActive: boolean }>({
    mutationFn: ({ id, isActive }) => updateAIAction(id, { is_active: isActive }),
    onSuccess: (data) => {
      enqueueSnackbar(`Action '${data.name}' ${data.is_active ? 'aktiviert' : 'deaktiviert'}.`, { variant: 'info' });
      queryClient.invalidateQueries({ queryKey: queryKeys.aiActions });
    },
    onError: (error) => {
      enqueueSnackbar(`Fehler beim Ändern des Status: ${error.message}`, { variant: 'error' });
    },
  });

  const handleRunAction = (id: number) => {
    setRunningActionId(id);
    runActionMutation.mutate(id);
  };

  const handleEditAction = (action: AIAction) => {
    setEditingAction(action);
    setShowForm(true);
  };

  const handleOpenDeleteDialog = (id: number) => {
    setDeleteActionId(id);
  };

  const handleConfirmDelete = () => {
    if (deleteActionId) {
      deleteActionMutation.mutate(deleteActionId);
    }
  };

  const handleToggleActive = (action: AIAction) => {
    toggleActiveMutation.mutate({ id: action.id, isActive: !action.is_active });
  };

  if (isLoading) return <CircularProgress />;
  if (error) return <Typography color="error">Fehler beim Laden der Actions: {error.message}</Typography>;

  return (
    <Paper sx={{ p: 2 }}>
      <Grid container justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h6">Verfügbare AI Actions</Typography>
        <Button variant="contained" onClick={() => { setEditingAction(null); setShowForm(true); }}>
          Neue Action
        </Button>
      </Grid>

      {showForm && (
        <ActionForm
          actionToEdit={editingAction}
          onClose={() => setShowForm(false)}
        />
      )}

      <List>
        {actions?.map(action => (
          <ListItem key={action.id} divider>
            <ListItemText
              primary={action.name}
              secondary={action.description || 'Keine Beschreibung'}
              sx={{ mr: 2 }} // Abstand nach rechts
            />
            <ListItemSecondaryAction sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
               <Tooltip title={action.is_active ? "Deaktivieren" : "Aktivieren"}>
                 <Switch
                   checked={action.is_active}
                   onChange={() => handleToggleActive(action)}
                   size="small"
                   disabled={toggleActiveMutation.isLoading && toggleActiveMutation.variables?.id === action.id}
                 />
               </Tooltip>
              <Tooltip title="Ausführen">
                <span> {/* Span für Tooltip bei disabled Button */} 
                  <IconButton
                    edge="end"
                    aria-label="run"
                    onClick={() => handleRunAction(action.id)}
                    disabled={runningActionId === action.id || !action.is_active}
                  >
                    {runningActionId === action.id ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                  </IconButton>
                 </span>
              </Tooltip>
              <Tooltip title="Bearbeiten">
                <IconButton edge="end" aria-label="edit" onClick={() => handleEditAction(action)}>
                  <EditIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Löschen">
                 <span>
                   <IconButton
                     edge="end"
                     aria-label="delete"
                     onClick={() => handleOpenDeleteDialog(action.id)}
                     disabled={deleteActionMutation.isLoading && deleteActionMutation.variables === action.id}
                   >
                     {deleteActionMutation.isLoading && deleteActionMutation.variables === action.id ? (
                         <CircularProgress size={20} />
                       ) : (
                         <DeleteIcon />
                       )}
                   </IconButton>
                 </span>
              </Tooltip>
            </ListItemSecondaryAction>
          </ListItem>
        ))}
      </List>

      {/* Bestätigungsdialog */} 
      {/* <ConfirmationDialog
        open={deleteActionId !== null}
        onClose={() => setDeleteActionId(null)}
        onConfirm={handleConfirmDelete}
        title="Action löschen?"
        message={`Möchten Sie die Action wirklich löschen? Dieser Vorgang kann nicht rückgängig gemacht werden.`}
        confirmText="Löschen"
        cancelText="Abbrechen"
      /> */}
      {/* Dummy-Platzhalter, ersetze durch echten Dialog */}
       {deleteActionId !== null && (
         <div style={{ border: '1px solid red', padding: 10, marginTop: 10 }}>
           Sicher löschen (ID: {deleteActionId})? 
           <Button onClick={handleConfirmDelete} size="small" color="error">Ja</Button>
           <Button onClick={() => setDeleteActionId(null)} size="small">Nein</Button>
         </div>
       )}
    </Paper>
  );
};

export default ActionList; 