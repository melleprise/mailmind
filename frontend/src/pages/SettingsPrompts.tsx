import React, { useState, useEffect } from 'react';
// import { Helmet } from 'react-helmet-async'; // Entfernt
import {
  Grid,
  // Container, // Entfernt
  Typography,
  // Card, // Ersetzt durch Paper
  Divider,
  // CardContent, // Wird durch Paper sx ersetzt
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
  Button,
  TablePagination,
  Chip,
  Switch,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  TextField,
  FormControlLabel,
  Alert,
  Paper, // Paper importieren
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
// import Footer from '@/components/Footer'; // Entfernt
// import PageTitleWrapper from '@/components/PageTitleWrapper'; // Entfernt
// import PageHeader from '@/components/PageHeader'; // Entfernt
import EditTwoToneIcon from '@mui/icons-material/EditTwoTone';
import { useForm, Controller } from 'react-hook-form';
import {
  useFetchPromptTemplates,
  useUpdatePromptTemplate,
} from '@/lib/api';
import {
  getAvailableModels,
} from '../services/api';
import { PromptTemplate, AvailableApiModel } from '@/lib/types';

const defaultValues: Partial<PromptTemplate> = {
  name: '',
  description: '',
  prompt: '',
};

// Define known providers (adjust as needed)
const KNOWN_PROVIDERS = ['groq', 'google_gemini']; // Use google_gemini

// Die Funktion kann jetzt eine reine UI-Komponente sein, die Props erhält oder die Hooks direkt verwendet.
// Wir belassen die Hooks hier für die Kapselung der Logik.
function SettingsPromptsTable() { // Umbenannt, da es nur noch die Tabelle/Dialog ist
  const [page, setPage] = useState<number>(0);
  const [limit, setLimit] = useState<number>(10);

  const {
    data: promptData,
    isLoading: isLoadingPrompts,
    error: fetchPromptsError,
  } = useFetchPromptTemplates();

  const {
    mutate: updatePromptTemplate,
    isPending: isUpdating,
    error: updateError,
  } = useUpdatePromptTemplate();

  // Provider-Daten werden hier nicht mehr direkt benötigt

  const [editModalOpen, setEditModalOpen] = useState<boolean>(false);
  const [editingPrompt, setEditingPrompt] = useState<PromptTemplate | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableApiModel[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  const { handleSubmit, control, reset, watch, setValue, formState: { errors, isSubmitting } } = useForm<Partial<PromptTemplate>>({
    defaultValues,
  });

  // Ensure prompts is always an array
  const prompts: PromptTemplate[] = Array.isArray(promptData) ? promptData : [];
  const count: number = prompts.length;

  const paginatedPrompts = prompts.slice(page * limit, page * limit + limit);

  useEffect(() => {
    if (updateError) {
      const errorMsg = (updateError as any)?.response?.data?.detail ||
                       JSON.stringify((updateError as any)?.response?.data) ||
                       (updateError as any)?.message ||
                       "Failed to save prompt template.";
      setSaveError(errorMsg);
    } else {
      setSaveError(null);
    }
  }, [updateError]);

  const handleEdit = (prompt: PromptTemplate) => {
    console.log('Edit prompt:', prompt);
    setEditingPrompt(prompt);
    reset({
      name: prompt.name,
      description: prompt.description,
      prompt: prompt.prompt,
      provider: prompt.provider,
      model_name: prompt.model_name
    });
    setSaveError(null);
    setEditModalOpen(true);
  };

  // NEU: handleRowClick, ruft handleEdit auf
  const handleRowClick = (prompt: PromptTemplate) => {
    handleEdit(prompt);
  };

  const handleCloseModal = () => {
    setEditModalOpen(false);
    setEditingPrompt(null);
    setSaveError(null);
    reset(defaultValues);
    setAvailableModels([]);
  };

  const onSubmit = async (data: Partial<PromptTemplate>) => {
    if (!editingPrompt) return;
    setSaveError(null);

    const patchData: Partial<PromptTemplate> & Pick<PromptTemplate, 'name'> = {
        name: editingPrompt.name,
        description: data.description,
        prompt: data.prompt,
        provider: data.provider,
        model_name: data.model_name
    };

    console.log("[onSubmit] Attempting to patch template with name:", editingPrompt.name);
    console.log("[onSubmit] Data being sent:", patchData);

    updatePromptTemplate(patchData, {
        onSuccess: () => {
            handleCloseModal();
        },
        onError: (err) => {
            console.error("Error saving prompt:", err);
        }
    });
  };

  const getProviderChipColor = (provider: string): "primary" | "secondary" | "default" | "info" | "success" | "warning" | "error" => {
    switch (provider) {
      case 'google_gemini': return 'primary';
      case 'groq': return 'success';
      case 'openai': return 'info';
      default: return 'default';
    }
  }

  const handlePageChange = (event: unknown, newPage: number): void => {
    setPage(newPage);
  };

  const handleLimitChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setLimit(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Error nur für Prompts relevant hier
  const displayError = fetchPromptsError ? 'Failed to load prompt templates.' : null;

  // Fetch models when the selected provider changes (in the form)
  const handleProviderChange = async (selectedProvider: string) => {
    console.log(`[SettingsPrompts] handleProviderChange called with: ${selectedProvider}`);
    // Reset model immediately to avoid showing stale/invalid value during load
    setValue('model_name', ''); 
    setAvailableModels([]); // Clear models immediately too

    if (!selectedProvider) {
      return;
    }
    setIsLoadingModels(true);
    try {
      console.log(`[SettingsPrompts] Calling getAvailableModels for ${selectedProvider}...`);
      const models = await getAvailableModels(selectedProvider);
      console.log(`[SettingsPrompts] Received models for ${selectedProvider}:`, models);

      if (Array.isArray(models)) {
           setAvailableModels(models);
           console.log(`[SettingsPrompts] Set availableModels state for ${selectedProvider}.`);
      } else {
           console.error(`[SettingsPrompts] Invalid model data received for ${selectedProvider}:`, models);
           setAvailableModels([]);
      }
    } catch (error) {
      console.error(`[SettingsPrompts] Error fetching models for ${selectedProvider}:`, error);
      setAvailableModels([]);
    } finally {
      setIsLoadingModels(false);
      console.log(`[SettingsPrompts] Finished handleProviderChange for ${selectedProvider}`);
    }
  };

  // Reset form and available models when modal opens
  useEffect(() => {
    if (editModalOpen && editingPrompt) {
      reset({
        name: editingPrompt.name,
        provider: editingPrompt.provider,
        description: editingPrompt.description,
        prompt: editingPrompt.prompt,
        model_name: editingPrompt.model_name,
      });
      if (editingPrompt.provider) {
         handleProviderChange(editingPrompt.provider);
      }
       setSaveError(null);
    } else {
        setAvailableModels([]); // Clear models when modal closes or no prompt
        reset(defaultValues); // Reset form completely when closing
    }
  }, [editModalOpen, editingPrompt, reset]);

  // NEW useEffect: Set model value AFTER availableModels are updated
  useEffect(() => {
    // Run only when modal is open, we have an editing prompt, models are loaded, and not currently loading
    if (editModalOpen && editingPrompt && availableModels.length > 0 && !isLoadingModels) {
        const targetModelName = editingPrompt.model_name; // Get the model name from the template we are editing
        const currentFormModelValue = watch('model_name'); // Get the current value in the form (might be reset or default)

        // Check if the target model from the prompt exists in the newly loaded list
        const targetModelExists = availableModels.some(m => m.model_id === targetModelName);

        if (targetModelExists) {
            // If the target model exists and is not already set in the form, set it.
            if (currentFormModelValue !== targetModelName) {
                console.log(`[SettingsPrompts Model Effect] Setting model_name value from editingPrompt: ${targetModelName}`);
                setValue('model_name', targetModelName, { shouldValidate: true });
            }
        } else {
            // Fallback: If the target model doesn't exist in the list (or wasn't set in the prompt),
            // select the first available model if the form doesn't already have a valid selection.
            const firstModelId = availableModels[0]?.model_id;
            const currentModelIsValid = availableModels.some(m => m.model_id === currentFormModelValue);
            
            if (firstModelId && !currentModelIsValid) {
                console.log(`[SettingsPrompts Model Effect] Target model '${targetModelName}' not found or invalid. Setting model_name value to first available: ${firstModelId}`);
                setValue('model_name', firstModelId, { shouldValidate: true });
            }
        }
    }
    // Dependencies: Ensure this runs when the modal opens/closes, the prompt changes, models finish loading, or the loading state changes.
  }, [editModalOpen, editingPrompt, availableModels, isLoadingModels, setValue, watch]);

  // Gib nur den Inhalt zurück (Tabelle + Dialog)
  return (
    <>
      {/* Verwende Paper statt Card für Konsistenz mit ApiCredentialForm */}
      {/* Passe Padding und Styling über sx an */} 
      <Paper sx={{ p: 3 }}> {/* Ändere Padding auf 3 */} 
        {/* Manueller Header mit Typography */}
        <Typography variant="h6" gutterBottom>
            Prompt Templates
        </Typography>
        <Divider sx={{ mb: 2 }} /> {/* Divider unter dem Header */} 
        
        {/* Inhalt (Loading, Error, Table) direkt in Paper */} 
        {isLoadingPrompts && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        )}
        {displayError && (
          <Typography color="error" sx={{ p: 2 }}>
            {displayError}
          </Typography>
        )}
        {!isLoadingPrompts && !displayError && (
          <>
            <TableContainer> {/* TableContainer benötigt möglicherweise keinen zusätzlichen Wrapper mehr */} 
              <Table sx={{ tableLayout: 'fixed' }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ width: '20%' }}>Name</TableCell>
                    <TableCell sx={{ width: '40%' }}>Description</TableCell>
                    <TableCell sx={{ width: '15%' }}>Provider</TableCell>
                    <TableCell sx={{ width: '25%' }}>Model</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paginatedPrompts.map((prompt) => (
                    <TableRow
                      hover
                      key={prompt.id}
                      onClick={() => handleRowClick(prompt)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell sx={{ wordBreak: 'break-word' }}>
                        <Typography variant="body1">{prompt.name}</Typography>
                      </TableCell>
                      <TableCell sx={{ wordBreak: 'break-word' }}>
                        <Typography variant="body2">{prompt.description}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={prompt.provider} color={getProviderChipColor(prompt.provider)} size="small" />
                      </TableCell>
                      <TableCell sx={{ wordBreak: 'break-word' }}>
                        <Typography variant="body2">{prompt.model_name}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <Box p={2}> {/* Behalte Box für Paginierungs-Padding */} 
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

      {/* Edit Dialog */}
      <Dialog open={editModalOpen} onClose={handleCloseModal} maxWidth="md" fullWidth>
        <DialogTitle>{editingPrompt ? 'Edit Prompt Template' : 'Add Prompt Template'}</DialogTitle>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogContent dividers>
            {saveError && (
              <Alert severity="error" sx={{ mb: 2 }}>{saveError}</Alert>
            )}
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Name"
                  defaultValue={editingPrompt?.name || ''}
                  fullWidth
                  disabled={!!editingPrompt}
                  InputLabelProps={{ shrink: true }}
                  margin="dense"
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <Controller
                  name="provider"
                  control={control}
                  defaultValue={editingPrompt?.provider || ''}
                  render={({ field }) => (
                    <FormControl fullWidth margin="dense">
                      <InputLabel id="provider-select-label">Provider</InputLabel>
                      <Select
                        labelId="provider-select-label"
                        label="Provider"
                        {...field}
                        onChange={(e) => {
                          field.onChange(e);
                          handleProviderChange(e.target.value as string);
                        }}
                      >
                        {KNOWN_PROVIDERS.map((providerName) => (
                          <MenuItem key={providerName} value={providerName}>
                            {providerName}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                {/* Conditionally render based on loading state and available models */}
                {/* Wrap Select in Box with height to ensure alignment even when loading/empty */}
                <Box sx={{ minHeight: '56px', display: 'flex', alignItems: 'center' }}>
                    {isLoadingModels && (
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                        <CircularProgress size={20} />
                        <Typography variant="caption" sx={{ ml: 1 }}>Loading models...</Typography>
                    </Box>
                    )}
                    {!isLoadingModels && watch('provider') && availableModels.length === 0 && (
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                        <Typography variant="caption" color="textSecondary">No models available.</Typography>
                    </Box>
                    )}
                    {!isLoadingModels && availableModels.length > 0 && (
                    <Controller
                        name="model_name"
                        control={control}
                        rules={{ required: 'Model selection is required' }}
                        render={({ field }) => (
                        <FormControl fullWidth margin="dense" error={!!errors.model_name} disabled={isLoadingModels || !availableModels.length}>
                            <InputLabel id="model-select-label">Model</InputLabel>
                            <Select
                            labelId="model-select-label"
                            label="Model"
                            {...field}
                            >
                            {isLoadingModels && <MenuItem disabled><CircularProgress size={20} /> Loading...</MenuItem>}
                            {!isLoadingModels && availableModels.length === 0 && <MenuItem disabled>No models available for this provider</MenuItem>}
                            {availableModels.map((model) => (
                                <MenuItem key={model.model_id} value={model.model_id}>
                                {model.model_id}
                                </MenuItem>
                            ))}
                            </Select>
                            {errors.model_name && (
                                <Typography color="error" variant="caption">
                                {errors.model_name.message}
                                </Typography>
                            )}
                        </FormControl>
                        )}
                    />
                    )}
                </Box>
              </Grid>
              <Grid item xs={12}>
                <Controller
                  name="description"
                  control={control}
                  rules={{ required: 'Description is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Description"
                      fullWidth
                      multiline
                      rows={2}
                      error={!!errors.description}
                      helperText={errors.description?.message}
                      margin="dense"
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12}>
                <Controller
                  name="prompt"
                  control={control}
                  rules={{ required: 'Prompt is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Prompt"
                      fullWidth
                      multiline
                      rows={10}
                      error={!!errors.prompt}
                      helperText={errors.prompt?.message}
                      margin="dense"
                      InputProps={{ sx: { fontFamily: 'monospace' } }}
                    />
                  )}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseModal}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={isSubmitting || isUpdating}>
              {isUpdating ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
}

export default SettingsPromptsTable; // Export umbenannt
