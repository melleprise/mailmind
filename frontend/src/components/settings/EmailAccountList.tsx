import React from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Typography,
  Paper,
  CircularProgress,
  Tooltip
} from '@mui/material';
import { Delete as DeleteIcon, Edit as EditIcon, Sync as SyncIcon } from '@mui/icons-material';

// Interface aus dem Service wiederverwenden (oder neu definieren/importieren)
interface EmailAccount {
  id: number;
  name: string;
  email: string;
  provider: string;
  // ... weitere Felder bei Bedarf ...
}

interface EmailAccountListProps {
  accounts: EmailAccount[];
  loading: boolean;
  error: string | null;
  syncingAccountId: number | null; // ID des gerade synchronisierenden Kontos
  onDelete: (id: number) => void; // Callback für Löschen
  onEdit: (account: EmailAccount) => void; // Callback für Bearbeiten (optional)
  onSync: (id: number) => void; // Callback für Sync
}

const EmailAccountList: React.FC<EmailAccountListProps> = ({ 
  accounts, 
  loading, 
  error, 
  syncingAccountId,
  onDelete, 
  onEdit, 
  onSync
}) => {

  if (loading) {
    return (
      <Paper sx={{ p: 2, textAlign: 'center' }}>
        <CircularProgress />
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography color="error">Error loading accounts: {error}</Typography>
      </Paper>
    );
  }

  if (accounts.length === 0) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography>No email accounts added yet.</Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ /* mt: 3 removed */ }}> 
      <Typography 
        variant="h6" 
        sx={{ px: 2, pt: 1, pb: 1, mb: 1, borderBottom: '1px solid', borderColor: 'divider' }} // Reduced vertical padding, added margin-bottom
      >
        Connected Accounts
      </Typography>
      <List dense> {/* dense für kompaktere Darstellung */} 
        {accounts.map((account) => (
          <ListItem 
            key={account.id} 
            divider /* Trennlinie zwischen Einträgen */
          >
            <ListItemText
              primary={account.name || account.email} // Zeige Name oder E-Mail
              secondary={account.name ? account.email : null} // Zeige E-Mail als sekundär, wenn Name vorhanden
            />
            <ListItemSecondaryAction sx={{ opacity: 1 /* Immer sichtbar */ }}> 
              {/* Sync Indicator (nicht mehr klickbar) */}
              {syncingAccountId === account.id ? (
                <Tooltip title="Syncing in progress...">
                   <CircularProgress size={24} sx={{ mr: 1 }} />
                </Tooltip>
              ) : (
                <Tooltip title="Jetzt synchronisieren">
                   <span>
                     <IconButton
                       edge="end"
                       aria-label="sync-status"
                       sx={{ mr: 1 }}
                       onClick={() => onSync(account.id)}
                       disabled={!!syncingAccountId}
                     >
                        <SyncIcon />
                     </IconButton>
                   </span>
                </Tooltip>
              )}

              <Tooltip title="Edit Account (not implemented)">
                <span> {/* Span für Tooltip bei deaktiviertem Button */} 
                  <IconButton edge="end" aria-label="edit" onClick={() => onEdit(account)} disabled>
                     <EditIcon />
                  </IconButton>
                </span>
              </Tooltip>
              <Tooltip title="Delete Account">
                 <IconButton 
                   edge="end" 
                   aria-label="delete" 
                   onClick={() => onDelete(account.id)} 
                   disabled={syncingAccountId === account.id} // Optional: Während Sync dieses Kontos deaktivieren
                   sx={{ ml: 1 }}
                 >
                    <DeleteIcon color="error" />
                 </IconButton>
              </Tooltip>
            </ListItemSecondaryAction>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};

export default EmailAccountList; 