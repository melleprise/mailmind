import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, CircularProgress } from '@mui/material';

interface PromptRefineDialogProps {
  open: boolean;
  initialPrompt?: string;
  loading?: boolean;
  error?: string | null;
  onClose: () => void;
  onSubmit: (prompt: string) => void;
  title?: string;
  description?: string;
}

export const PromptRefineDialog: React.FC<PromptRefineDialogProps> = ({
  open,
  initialPrompt = '',
  loading = false,
  error = null,
  onClose,
  onSubmit,
  title = 'Refine Prompt',
  description,
}) => {
  const [prompt, setPrompt] = React.useState(initialPrompt);

  React.useEffect(() => {
    setPrompt(initialPrompt);
  }, [initialPrompt, open]);

  const handleSubmit = () => {
    if (!loading && prompt.trim()) {
      onSubmit(prompt.trim());
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        {description && <div style={{ marginBottom: 8 }}>{description}</div>}
        <TextField
          autoFocus
          fullWidth
          multiline
          minRows={3}
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          disabled={loading}
          label="Prompt"
        />
        {error && <div style={{ color: 'red', marginTop: 8 }}>{error}</div>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>Abbrechen</Button>
        <Button onClick={handleSubmit} disabled={loading || !prompt.trim()} variant="contained">
          {loading ? <CircularProgress size={18} /> : 'Refine'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PromptRefineDialog; 