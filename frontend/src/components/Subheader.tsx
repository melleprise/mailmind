import React, { useState } from 'react';
import { 
  Box, 
  IconButton, 
  Toolbar, 
  useTheme, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel, 
  Typography, 
  CircularProgress 
} from '@mui/material';
import {
  Search as SearchIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { emailAccounts } from '../services/api'; // API-Funktion importieren
import { queryKeys } from '../lib/queryKeys'; // Query Keys importieren
import FolderTree from './FolderTree'; // FolderTree importieren
import { FolderItem } from '../services/api'; // FolderItem Interface importieren

const Subheader: React.FC = () => {
  const theme = useTheme();
  const [selectedAccount, setSelectedAccount] = useState<string | number>('all');

  // E-Mail-Konten abrufen
  const { data: accounts, isLoading, error } = useQuery<EmailAccount[], Error>({
    queryKey: [queryKeys.emailAccounts],
    queryFn: emailAccounts.list,
  });

  // Query für Ordnerstruktur, abhängig vom ausgewählten Konto
  const { 
    data: folders, 
    isLoading: isLoadingFolders, 
    error: errorFolders, 
    refetch: refetchFolders // Manuelles Neuladen ermöglichen
  } = useQuery<FolderItem[], Error>({
    queryKey: [queryKeys.emailAccounts, 'folders', selectedAccount],
    queryFn: () => {
      if (typeof selectedAccount === 'number') {
        return emailAccounts.getFolders(selectedAccount);
      }
      return Promise.resolve([]); // Leeres Array zurückgeben, wenn 'all' ausgewählt ist
    },
    enabled: typeof selectedAccount === 'number', // Nur aktivieren, wenn eine ID ausgewählt ist
    staleTime: 5 * 60 * 1000, // Daten für 5 Minuten als frisch betrachten
  });

  const handleAccountChange = (event: any) => {
    const newSelectedValue = event.target.value as string | number;
    setSelectedAccount(newSelectedValue);
    // Ordner werden automatisch neu geladen, da queryKey sich ändert oder enabled wird
  };

  return (
    <Box
      sx={{
        bgcolor: theme.palette.background.paper,
        borderBottom: '1px solid',
        borderColor: theme.palette.divider,
        position: 'sticky',
        top: '64px', 
        zIndex: theme.zIndex.appBar - 1,
      }}
    >
      <Toolbar variant="dense">
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}> {/* Increased gap */} 
          {/* Dropdown für E-Mail-Konten */}
          <FormControl size="small" sx={{ minWidth: 250 }}>
            {/* <InputLabel id="account-select-label">Account</InputLabel> */} {/* Optional: Label */} 
            <Select
              labelId="account-select-label"
              id="account-select"
              value={selectedAccount}
              onChange={handleAccountChange}
              // label="Account" // Optional: Label
              displayEmpty // Zeigt den Wert auch an, wenn er "leer" ist (wie 'all')
              variant="outlined" // Oder 'standard' / 'filled'
              sx={{ 
                color: 'text.secondary', 
                '.MuiOutlinedInput-notchedOutline': { border: 0 }, // Rahmen entfernen
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { border: 0 }, // Rahmen im Fokus entfernen
                '&:hover .MuiOutlinedInput-notchedOutline': { border: 0 }, // Rahmen beim Hover entfernen
                '.MuiSelect-icon': { color: 'text.secondary' } // Farbe des Dropdown-Pfeils
              }}
            >
              <MenuItem value="all">
                <em>All Accounts</em>
              </MenuItem>
              {isLoading && <MenuItem disabled><CircularProgress size={20} /></MenuItem>}
              {error && <MenuItem disabled><Typography color="error" variant="caption">Error loading</Typography></MenuItem>}
              {accounts?.data && Array.isArray(accounts.data) && accounts.data.map((account) => (
                <MenuItem key={account.id} value={account.id}>
                  {account.name || account.email} {/* Namen oder E-Mail anzeigen */}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Such-Icon bleibt */}
          <IconButton
            // onClick={/* Logik für Suche */} 
            sx={{ color: 'text.secondary' }}
            title="Search"
          >
            <SearchIcon />
          </IconButton>
        </Box>
      </Toolbar>
      {/* Bereich für Ordnerstruktur (Platzhalter) */}
      {/* Zeige Loading/Error oder FolderTree nur an, wenn ein spezifisches Konto gewählt ist */}
      {typeof selectedAccount === 'number' && (
        <Box sx={{ p: 1, borderTop: '1px solid', borderColor: 'divider' }}>
          {isLoadingFolders && <CircularProgress size={20} sx={{ display: 'block', mx: 'auto' }} />}
          {errorFolders && 
            <Typography color="error" variant="caption" sx={{ display: 'block', textAlign: 'center' }}>
              Error loading folders: {errorFolders.message}
            </Typography>}
          {/* {!isLoadingFolders && !errorFolders && folders && ( */} 
          {/*   <FolderTree folders={folders} /> */} 
          {/* )} */}
          {/* Leerer Zustand, falls keine Ordner gefunden wurden (aber kein Fehler) */}
          {!isLoadingFolders && !errorFolders && folders && folders.length === 0 && (
             <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center' }}>
                No folders found for this account.
             </Typography>
          )}
        </Box>
      )}
    </Box>
  );
};

export default Subheader; 