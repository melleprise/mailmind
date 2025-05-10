import React from 'react';
import { Box, Paper } from '@mui/material';
import {
  Reply as ReplyIcon,
  ForwardToInbox as ForwardToInboxIcon,
  Link as LinkIcon,
  Report as ReportIcon,
  MoveToInbox as MoveToInboxIcon,
} from '@mui/icons-material';
import { ActionButton } from '../actions/ActionButton';

// --- Style kopiert von AISuggestions.tsx ---
const actionButtonStyles = {
  flexGrow: 1,
  p: 1.5,
  overflow: 'hidden',
  border: '1px solid',
  borderColor: 'divider',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: 1,
  borderRadius: 1, // Rounded corners like buttons
  '&:hover': {
    borderColor: 'primary.main',
    bgcolor: 'action.hover'
  }
};
// --- Ende Styles ---

interface ActionButtonsViewProps {
  selectedEmailId: number | null;
  setEmailAction: (emailId: number, action: string | null) => void;
  isExpanded: boolean;
  onExpandRequest: () => void;
}

// Import für Dummy Input
import { AIAgentInput } from './AIAgentInput';

export const ActionButtonsView: React.FC<ActionButtonsViewProps> = ({
  selectedEmailId,
  setEmailAction,
  isExpanded,
  onExpandRequest,
}) => {
  const handleActionClick = (action: string | null) => {
    if (selectedEmailId) {
      setEmailAction(selectedEmailId, action);
    }
  };

  return (
    // Outer Box for flex layout and padding bottom
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Box for the buttons with scrolling and gap */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: 1, overflowY: 'auto' }}>
        <ActionButton icon={<ReplyIcon />} label="Antworten" onClick={() => handleActionClick('reply')} />
        <ActionButton icon={<ForwardToInboxIcon />} label="Weiterleiten" onClick={() => console.log('Action: Weiterleiten')} />
        <ActionButton icon={<ReportIcon />} label="Als Spam markieren" onClick={() => console.log('Action: Spam')} />
        <ActionButton icon={<MoveToInboxIcon />} label="Automatisch verschieben" onClick={() => console.log('Action: Verschieben')} />
        <ActionButton icon={<LinkIcon />} label="Link 1 öffnen" onClick={() => console.log('Action: Link 1')} />
        <ActionButton icon={<LinkIcon />} label="Link 2 öffnen" onClick={() => console.log('Action: Link 2')} />
      </Box>
      {/* Dummy Input Area at the bottom */}
      <Box sx={{ flexShrink: 0, mt: 1 /* Abstand nach oben */ }}>
        <AIAgentInput isExpanded={isExpanded} onExpandRequest={onExpandRequest} />
      </Box>
    </Box>
  );
}; 