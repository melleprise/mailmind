import React from 'react';
import { SimpleTreeView } from '@mui/x-tree-view/SimpleTreeView';
import { TreeItem } from '@mui/x-tree-view/TreeItem';
import Checkbox from '@mui/material/Checkbox';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { FolderStructureSuggestion } from '../services/api';

interface SuggestionTreeViewProps {
  structure: FolderStructureSuggestion;
  selectedPaths: string[];
  onSelectionChange: (selectedPaths: string[]) => void;
  initialExpandedNodes: string[];
}

const SuggestionTreeView: React.FC<SuggestionTreeViewProps> = ({ 
  structure,
  selectedPaths,
  onSelectionChange,
  initialExpandedNodes
}) => {

  const handleToggle = (event: React.SyntheticEvent, nodeId: string) => {
    event.stopPropagation(); // Prevent node expansion/collapse on checkbox click
    const isSelected = selectedPaths.includes(nodeId);
    let newSelectedPaths = [...selectedPaths];

    const getDescendantPaths = (nodes: FolderStructureSuggestion, currentPath: string): string[] => {
      let paths: string[] = [];
      Object.entries(nodes).forEach(([key, value]) => {
        const nodePath = `${currentPath}/${key}`;
        paths.push(nodePath);
        if (value && typeof value === 'object' && Object.keys(value).length > 0) {
          paths = paths.concat(getDescendantPaths(value, nodePath));
        }
      });
      return paths;
    }
    
    const findNodeStructure = (nodes: FolderStructureSuggestion, targetPath: string): FolderStructureSuggestion | null => {
      const parts = targetPath.split('/');
      let currentLevel = nodes;
      for (const part of parts) {
        if (!currentLevel || !currentLevel[part]) {
          return null; // Path not found
        }
        currentLevel = currentLevel[part];
      }
      return currentLevel;
    }

    const nodeStructure = findNodeStructure(structure, nodeId);
    let descendants: string[] = [];
    if (nodeStructure && Object.keys(nodeStructure).length > 0) {
        descendants = getDescendantPaths(nodeStructure, nodeId);
    }

    if (isSelected) {
      newSelectedPaths = newSelectedPaths.filter(path => path !== nodeId && !descendants.includes(path));
    } else {
      newSelectedPaths = Array.from(new Set([...newSelectedPaths, nodeId, ...descendants]));
    }
    onSelectionChange(newSelectedPaths);
  };

  const renderTree = (nodes: FolderStructureSuggestion, currentPath: string = '') => {
    return Object.entries(nodes).map(([key, value]) => {
      const nodePath = currentPath ? `${currentPath}/${key}` : key;
      const isSelected = selectedPaths.includes(nodePath);
      
      const areSomeChildrenSelected = selectedPaths.some(path => path.startsWith(nodePath + '/') && path !== nodePath);
      const areAllChildrenSelected = Object.keys(value).length > 0 && 
        Object.entries(value).every(([childKey, childValue]) => 
          selectedPaths.includes(`${nodePath}/${childKey}`) 
        );
      const isIndeterminate = !isSelected && areSomeChildrenSelected;
      
      const hasChildren = Object.keys(value).length > 0;

      return (
        <TreeItem
          key={nodePath}
          nodeId={nodePath}
          itemId={nodePath}
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', p: 0.5, pr: 0 }}>
              <Checkbox
                checked={isSelected}
                indeterminate={isIndeterminate}
                onChange={(e) => handleToggle(e, nodePath)}
                onClick={(e) => e.stopPropagation()}
                size="small"
                sx={{ mr: 1, padding: 0 }}
              />
              <Typography variant="body2" sx={{ fontWeight: 'inherit', flexGrow: 1 }}>
                {key}
              </Typography>
            </Box>
          }
        >
          {hasChildren ? renderTree(value, nodePath) : null}
        </TreeItem>
      );
    });
  };

  return (
    <SimpleTreeView
      aria-label="suggestion-folder-tree"
      defaultExpandedItems={initialExpandedNodes}
      sx={{ height: 'auto', flexGrow: 1, overflowY: 'auto', border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1 }}
      multiSelect
    >
      {renderTree(structure)}
    </SimpleTreeView>
  );
};

export default SuggestionTreeView; 