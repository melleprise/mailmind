import React from 'react';
import { Box, Button, IconButton, Tooltip } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';

interface AISuggestionContextMenuProps {
  disabled?: boolean;
  onArchive: () => void;
  onRefresh: () => void;
}

export const AISuggestionContextMenu: React.FC<AISuggestionContextMenuProps> = ({
  disabled,
  onArchive,
  onRefresh,
}) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
    <Box sx={{
      display: 'flex',
      gap: 1,
      '& .MuiButton-root': {
        color: 'grey.400',
        textTransform: 'none',
        minWidth: 0,
        padding: '3px 8px',
        '&:hover': {
          backgroundColor: 'rgba(255, 255, 255, 0.12)',
        },
      },
    }}>
      <Button size="small" onClick={onArchive} disabled={disabled}>
        spam
      </Button>
    </Box>
    <Tooltip title="Regenerate Suggestions">
      <IconButton size="small" onClick={onRefresh} disabled={disabled} sx={{ color: 'grey.400' }}>
        <RefreshIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  </Box>
);

export default AISuggestionContextMenu; 