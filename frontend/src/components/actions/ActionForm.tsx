import React, { useState, useEffect } from 'react';
import { Box, Typography, TextField, Button, Paper, FormControl, InputLabel, Select, MenuItem, SelectChangeEvent, Chip, Autocomplete, CircularProgress, Checkbox, FormControlLabel, FormGroup, Tooltip, IconButton } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { AIAction, AIActionCreateData, AIActionUpdateData, createAIAction, updateAIAction } from '../../services/actionsService';
import { queryKeys } from '../../lib/queryKeys';
// Importiere Service zum Abrufen von PromptTemplates (muss noch erstellt oder erweitert werden)
import { getPrompts } from '../../services/api'; 

interface ActionFormProps {
  actionToEdit?: AIAction | null;
  onClose: () => void;
}

interface PromptTemplate {
  id: number;
  name: string;
  description: string;
}

const ActionForm: React.FC<ActionFormProps> = ({ actionToEdit, onClose }) => {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [selectedPromptIds, setSelectedPromptIds] = useState<number[]>([]);

  // Fetch PromptTemplates
  const { data: promptTemplates, isLoading: isLoadingPrompts, error: promptsError } = useQuery<PromptTemplate[], Error>({
    queryKey: queryKeys.promptTemplates,
    queryFn: getPrompts,
  });

  useEffect(() => {
    if (actionToEdit) {
      setName(actionToEdit.name);
      setDescription(actionToEdit.description);
      setIsActive(actionToEdit.is_active);
      setSelectedPromptIds(actionToEdit.prompts.map(p => p.id));
    } else {
      // Reset form on create new
      setName('');
      setDescription('');
      setIsActive(true);
      setSelectedPromptIds([]);
    }
  }, [actionToEdit]);

  const createMutation = useMutation<AIAction, Error, AIActionCreateData>({
    mutationFn: createAIAction,
    onSuccess: (data) => {
      enqueueSnackbar(`Action '${data.name}' erfolgreich erstellt.`, { variant: 'success' });
      queryClient.invalidateQueries({ queryKey: queryKeys.aiActions });
      onClose();
    },
    onError: (error) => {
      enqueueSnackbar(`Fehler beim Erstellen: ${error.message}`, { variant: 'error' });
    },
  });

  const updateMutation = useMutation<AIAction, Error, { id: number; data: AIActionUpdateData }>({
    mutationFn: ({ id, data }) => updateAIAction(id, data),
    onSuccess: (data) => {
      enqueueSnackbar(`Action '${data.name}' erfolgreich aktualisiert.`, { variant: 'success' });
      queryClient.invalidateQueries({ queryKey: queryKeys.aiActions });
      queryClient.invalidateQueries({ queryKey: queryKeys.aiAction(data.id) });
      onClose();
    },
    onError: (error) => {
      enqueueSnackbar(`Fehler beim Aktualisieren: ${error.message}`, { variant: 'error' });
    },
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const actionData: AIActionCreateData | AIActionUpdateData = {
      name,
      description,
      is_active: isActive,
      prompt_ids: selectedPromptIds,
      sort_order: actionToEdit?.sort_order ?? 0, // Behalte alte Sortierung oder setze auf 0
    };

    if (actionToEdit) {
      updateMutation.mutate({ id: actionToEdit.id, data: actionData as AIActionUpdateData });
    } else {
      createMutation.mutate(actionData as AIActionCreateData);
    }
  };

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        {actionToEdit ? 'AI Action bearbeiten' : 'Neue AI Action erstellen'}
      </Typography>
      <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <TextField
          label="Name der Action"
          variant="outlined"
          fullWidth
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <TextField
          label="Beschreibung"
          variant="outlined"
          fullWidth
          multiline
          minRows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Autocomplete
          multiple
          id="prompt-template-select"
          options={promptTemplates || []}
          getOptionLabel={(option) => option.name}
          value={(promptTemplates || []).filter(p => selectedPromptIds.includes(p.id))}
          isOptionEqualToValue={(option, value) => option.id === value.id}
          onChange={(event, newValue) => {
            setSelectedPromptIds(newValue.map(p => p.id));
          }}
          loading={isLoadingPrompts}
          renderOption={(props, option, { selected }) => (
              <li {...props}>
                  <Checkbox
                      style={{ marginRight: 8 }}
                      checked={selected}
                  />
                  <Box component="span" sx={{ flexGrow: 1 }}>{option.name}</Box>
                  <Tooltip title={option.description || 'Keine Beschreibung'}>
                      <IconButton size="small">
                          <InfoOutlinedIcon fontSize="small" />
                      </IconButton>
                  </Tooltip>
              </li>
            )}
          renderInput={(params) => (
            <TextField
              {...params}
              variant="outlined"
              label="Verknüpfte Prompts"
              placeholder="Prompts auswählen..."
              InputProps={{
                ...params.InputProps,
                endAdornment: (
                  <React.Fragment>
                    {isLoadingPrompts ? <CircularProgress color="inherit" size={20} /> : null}
                    {params.InputProps.endAdornment}
                  </React.Fragment>
                ),
              }}
            />
          )}
        />
         {promptsError && <Typography color="error">Fehler beim Laden der Prompts: {promptsError.message}</Typography>}
        <FormControlLabel
          control={<Checkbox checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />}
          label="Aktiv"
        />
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
          <Button onClick={onClose} color="secondary">
            Abbrechen
          </Button>
          <Button type="submit" variant="contained" color="primary" disabled={createMutation.isLoading || updateMutation.isLoading}>
            {createMutation.isLoading || updateMutation.isLoading ? <CircularProgress size={24} /> : 'Speichern'}
          </Button>
        </Box>
      </Box>
    </Paper>
  );
};

export default ActionForm; 