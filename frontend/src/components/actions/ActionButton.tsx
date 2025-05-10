import React from 'react';
import { Paper } from '@mui/material';

interface ActionButtonProps {
  icon: React.ReactElement;
  label: string;
  onClick?: () => void;
  sx?: object;
}

const actionButtonStyles = {
  flexGrow: 1,
  p: 1.5,
  overflow: 'hidden',
  border: '1px solid',
  borderColor: 'divider',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-start',
  gap: 1,
  borderRadius: 1,
  boxShadow: 'none',
  transition: 'background 0.2s',
  minHeight: 48,
  maxHeight: 56,
  minWidth: 0,
  width: '100%',
  fontSize: '1rem',
  fontWeight: 500,
  lineHeight: 1.5,
  textAlign: 'left',
  backgroundColor: 'background.paper',
  color: 'common.white',
  '& span': {
    fontSize: '1rem',
    fontWeight: 500,
    lineHeight: 1.5,
    color: 'common.white',
    display: 'flex',
    alignItems: 'center',
  },
  '& svg': {
    color: 'primary.main',
    fontSize: 24,
    verticalAlign: 'middle',
    display: 'inline-flex',
    alignItems: 'center',
  },
  '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' }
};

export const ActionButton: React.FC<ActionButtonProps> = ({ icon, label, onClick, sx }) => (
  <Paper
    elevation={0}
    sx={{ ...actionButtonStyles, ...sx }}
    onClick={onClick}
  >
    {icon}
    <span>{label}</span>
  </Paper>
); 