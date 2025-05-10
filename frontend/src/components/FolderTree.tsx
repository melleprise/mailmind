import React from 'react';
// Korrekte Imports für RichTreeView
import { RichTreeView } from '@mui/x-tree-view/RichTreeView';
// TreeItem wird nicht direkt benötigt, wenn 'items' Prop verwendet wird
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
// FolderIcon kann optional für custom rendering verwendet werden, erstmal entfernt
import { FolderItem as FolderItemType } from '../services/api'; // Type importieren
import { Box, Typography } from '@mui/material';

interface FolderTreeProps {
  folders: FolderItemType[];
  onFolderSelect?: (folderPath: string) => void; // Optional callback für Ordnerauswahl
}

// Helper Funktion, um unsere Datenstruktur in das von RichTreeView erwartete Format umzuwandeln
const transformFoldersToTreeData = (folders: FolderItemType[]): { id: string; label: string; children?: any[] }[] => {
  return folders.map(folder => ({
    id: folder.full_path, // Verwende full_path als eindeutige ID
    label: folder.name,   // Verwende name als Label
    // Rekursiv für Kinder umwandeln, falls vorhanden
    children: folder.children ? transformFoldersToTreeData(folder.children) : undefined,
  }));
};


// Rekursive Funktion wird nicht mehr benötigt
// const renderTree = (nodes: FolderItemType[], onFolderSelect?: (folderPath: string) => void): JSX.Element[] => { ... };

const FolderTree: React.FC<FolderTreeProps> = ({ folders, onFolderSelect }) => {
  if (!folders || folders.length === 0) {
    return null; // Nichts anzeigen, wenn keine Ordner da sind
  }

  // Daten transformieren
  const treeData = transformFoldersToTreeData(folders);

  return (
    <RichTreeView
      items={treeData} // Transformierte Daten übergeben
      aria-label="folder tree"
      defaultCollapseIcon={<ExpandMoreIcon />}
      defaultExpandIcon={<ChevronRightIcon />}
      // Callback, wenn ein Item ausgewählt wird
      onItemSelectionToggle={(event, itemId, isSelected) => {
        // Wir wollen nur bei einfacher Auswahl (nicht bei multi-select) reagieren
        if (isSelected) {
             onFolderSelect?.(itemId); 
        }
      }}
      // SX Anpassungen, ggf. an RichTreeView Slots anpassen
      sx={{ 
        flexGrow: 1, 
        maxHeight: '200px', // Maximale Höhe, ggf. anpassen
        overflowY: 'auto', 
        width: '100%',
         // Styling über Slots anpassen, falls nötig (Beispiel)
         // '& .MuiTreeItem-label': {
         //   fontSize: '0.875rem',
         //   py: 0.5, 
         // },
      }}
    />
  );
};

export default FolderTree; 