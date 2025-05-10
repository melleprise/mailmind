// TODO: This component is now being reactivated. Verify API interactions.
import React, { useState, useEffect, useCallback } from 'react';
import { 
    Box, Typography, Paper, TextField, Button, IconButton, Tooltip, CircularProgress, 
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Alert,
    Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon, Save as SaveIcon, Cancel as CancelIcon } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import knowledgeService, { KnowledgeField, KnowledgeFieldPayload } from '../../services/knowledgeService'; // Uncommented import
import { useSnackbar } from 'notistack';

// Define Yup schema for validation
const schema = yup.object().shape({
    // ... existing code ...
});

// Interface definitions might be slightly different from the service file, ensure consistency or rely on service export
// interface KnowledgeField { id: number; key: string; value: string; } // Can be removed if service export is used directly
// interface KnowledgeFieldPayload { key: string; value: string; } // Can be removed if service export is used directly

const KnowledgeSettings: React.FC = () => {
    const [fields, setFields] = useState<KnowledgeField[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [openAddDialog, setOpenAddDialog] = useState<boolean>(false);
    const [openEditDialog, setOpenEditDialog] = useState<boolean>(false);
    const [editingField, setEditingField] = useState<KnowledgeField | null>(null);
    const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
    const { enqueueSnackbar } = useSnackbar();

    const { control, handleSubmit, reset, setValue, formState: { errors: formErrors } } = useForm<KnowledgeFieldPayload>({
        resolver: yupResolver(schema),
        defaultValues: { key: '', value: '' }
    });

    const loadFields = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await knowledgeService.list(); // Uncommented API call
            // console.warn("KnowledgeService.list() call removed, API needs re-implementation."); // Removed warning
            setFields(response || []); // Ensure response is treated as an array
        } catch (err: any) {
            console.error("Error loading knowledge fields:", err);
            const msg = err.response?.data?.detail || 'Failed to load knowledge fields.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadFields();
    }, [loadFields]);

    const handleAddSubmit = async (data: KnowledgeFieldPayload) => {
        try {
            setError(null); // Clear previous errors
            await knowledgeService.create(data); // Uncommented API call
            // console.warn("KnowledgeService.create() call removed, API needs re-implementation."); // Removed warning
            setOpenAddDialog(false);
            reset({ key: '', value: '' }); // Reset form after successful submission
            await loadFields(); // Reload fields
            enqueueSnackbar('Field added successfully! (Simulated)', { variant: 'success' });
        } catch (err: any) {
            console.error("Error adding knowledge field:", err);
            const msg = err.response?.data?.detail || err.response?.data?.key?.[0] || err.response?.data?.value?.[0] || 'Failed to add knowledge field.'; // Show specific backend validation error if available
            setError(msg); // Display error in the dialog or globally
            enqueueSnackbar(msg, { variant: 'error' });
        }
    };

    const handleEditSubmit = async (data: KnowledgeFieldPayload) => {
        if (!editingField) return;
        try {
            setError(null); // Clear previous errors
            // Construct payload - assuming only 'value' is editable based on service impl.
            // If 'key' is also editable, the service needs adjustment.
            const updateData: KnowledgeFieldPayload = { key: editingField.key, value: data.value }; // Use original key

            await knowledgeService.update(editingField.id, updateData); // Uncommented API call
            // console.warn("KnowledgeService.update() call removed, API needs re-implementation."); // Removed warning
            setOpenEditDialog(false);
            setEditingField(null);
            reset({ key: '', value: '' }); // Reset form
            await loadFields(); // Reload fields
            enqueueSnackbar('Field updated successfully! (Simulated)', { variant: 'success' });
        } catch (err: any) {
            console.error("Error updating knowledge field:", err);
            const msg = err.response?.data?.detail || err.response?.data?.value?.[0] || 'Failed to update knowledge field.'; // Show specific backend validation error if available
            setError(msg); // Display error in the dialog or globally
            enqueueSnackbar(msg, { variant: 'error' });
        }
    };

    const handleDelete = async () => {
        if (confirmDeleteId === null) return;
        try {
            setError(null);
            await knowledgeService.delete(confirmDeleteId); // Uncommented API call
            // console.warn("KnowledgeService.delete() call removed, API needs re-implementation."); // Removed warning
            setConfirmDeleteId(null); // Close confirmation dialog
            await loadFields(); // Reload fields
            enqueueSnackbar('Field deleted successfully! (Simulated)', { variant: 'success' });
        } catch (err: any) {
            console.error("Error deleting knowledge field:", err);
            const msg = err.response?.data?.detail || 'Failed to delete knowledge field.';
            setError(msg); // Display error (consider showing it near the table or as a snackbar)
            enqueueSnackbar(msg, { variant: 'error' });
        }
    };

    const startEdit = (field: KnowledgeField) => {
        setEditingField(field);
        setValue('key', field.key); // Set initial form values for editing
        setValue('value', field.value);
        setError(null); // Clear errors when opening dialog
        setOpenEditDialog(true);
    };

    const handleCloseAddDialog = () => {
        setOpenAddDialog(false);
        reset({ key: '', value: '' }); // Reset form on close
        setError(null); // Clear errors
    };

    const handleCloseEditDialog = () => {
        setOpenEditDialog(false);
        setEditingField(null);
        reset({ key: '', value: '' }); // Reset form on close
        setError(null); // Clear errors
    };

    if (loading) {
        return <CircularProgress />;
    }

    return (
        <Paper sx={{ p: 2, mt: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Knowledge Fields</Typography>
                <Button variant="contained" startIcon={<AddIcon />} onClick={() => { setError(null); reset({ key: '', value: '' }); setOpenAddDialog(true); }}>
                    Add Field
                </Button>
            </Box>
            
            {error && !openAddDialog && !openEditDialog && (
                <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
            )}

            <Dialog open={openAddDialog} onClose={handleCloseAddDialog} maxWidth="sm" fullWidth>
                <DialogTitle>Add New Knowledge Field</DialogTitle>
                <form onSubmit={handleSubmit(handleAddSubmit)}>
                    <DialogContent>
                        {error && openAddDialog && (
                            <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
                        )}
                        <Controller
                            name="key"
                            control={control}
                            render={({ field }) => (
                                <TextField
                                    {...field}
                                    autoFocus
                                    margin="dense"
                                    label="Key (e.g., my_company_name)"
                                    type="text"
                                    fullWidth
                                    variant="outlined"
                                    error={!!formErrors.key}
                                    helperText={formErrors.key?.message || 'Identifier used in prompts like {key}. Letters, numbers, underscores allowed. Must start with a letter.'}
                                    sx={{ mb: 2 }}
                                />
                            )}
                        />
                        <Controller
                            name="value"
                            control={control}
                            render={({ field }) => (
                                <TextField
                                    {...field}
                                    margin="dense"
                                    label="Value (The content)"
                                    type="text"
                                    fullWidth
                                    multiline
                                    rows={4}
                                    variant="outlined"
                                    error={!!formErrors.value}
                                    helperText={formErrors.value?.message || 'The actual content that will be inserted.'}
                                />
                            )}
                        />
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleCloseAddDialog}>Cancel</Button>
                        <Button type="submit" variant="contained">Add</Button>
                    </DialogActions>
                </form>
            </Dialog>

            <Dialog open={openEditDialog} onClose={handleCloseEditDialog} maxWidth="sm" fullWidth>
                <DialogTitle>Edit Knowledge Field</DialogTitle>
                <form onSubmit={handleSubmit(handleEditSubmit)}>
                    <DialogContent>
                        {error && openEditDialog && (
                            <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
                        )}
                        <TextField
                            value={editingField?.key || ''}
                            disabled
                            margin="dense"
                            label="Key"
                            type="text"
                            fullWidth
                            variant="outlined"
                            helperText="Key cannot be changed after creation."
                            sx={{ mb: 2 }}
                        />
                        <Controller
                            name="value"
                            control={control}
                            render={({ field }) => (
                                <TextField
                                    {...field}
                                    autoFocus
                                    margin="dense"
                                    label="Value"
                                    type="text"
                                    fullWidth
                                    multiline
                                    rows={4}
                                    variant="outlined"
                                    error={!!formErrors.value}
                                    helperText={formErrors.value?.message}
                                />
                            )}
                        />
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleCloseEditDialog}>Cancel</Button>
                        <Button type="submit" variant="contained">Save Changes</Button>
                    </DialogActions>
                </form>
            </Dialog>

            <Dialog
                open={confirmDeleteId !== null}
                onClose={() => setConfirmDeleteId(null)}
            >
                <DialogTitle>Confirm Deletion</DialogTitle>
                <DialogContent>
                    <Typography>Are you sure you want to delete this knowledge field?</Typography>
                    {editingField && <Typography variant="body2" sx={{ mt: 1 }}>Key: {fields.find(f => f.id === confirmDeleteId)?.key}</Typography>}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setConfirmDeleteId(null)}>Cancel</Button>
                    <Button onClick={handleDelete} color="error" variant="contained">Delete</Button>
                </DialogActions>
            </Dialog>

            <TableContainer>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Key (Placeholder)</TableCell>
                            <TableCell>Value</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {fields.map((field) => (
                            <TableRow key={field.id}>
                                <TableCell sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>{`{${field.key}}`}</TableCell>
                                <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{field.value}</TableCell>
                                <TableCell align="right">
                                    <Tooltip title="Edit Field">
                                        <span>
                                            <IconButton onClick={() => startEdit(field)} color="default" size="small" disabled={loading || openAddDialog || openEditDialog}>
                                                <EditIcon fontSize="small" />
                                            </IconButton>
                                        </span>
                                    </Tooltip>
                                    <Tooltip title="Delete Field">
                                        <span>
                                            <IconButton onClick={() => setConfirmDeleteId(field.id)} color="error" size="small" disabled={loading || openAddDialog || openEditDialog}>
                                                <DeleteIcon fontSize="small" />
                                            </IconButton>
                                        </span>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
            {fields.length === 0 && !loading && !openAddDialog && !openEditDialog && (
                <Typography sx={{ mt: 2, textAlign: 'center' }}>No knowledge fields added yet.</Typography>
            )}
            {loading && fields.length > 0 && (
                <CircularProgress size={24} sx={{ position: 'absolute', bottom: 16, right: 16 }} />
            )}
        </Paper>
    );
};

export default KnowledgeSettings; 