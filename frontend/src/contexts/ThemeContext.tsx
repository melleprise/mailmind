import React, { createContext, useState, useMemo, useContext, ReactNode, useEffect } from 'react';
import { ThemeProvider as MuiThemeProvider, PaletteMode } from '@mui/material';
import { createTheme } from '@mui/material';
import { lightThemeOptions, darkThemeOptions } from '../theme/theme'; // Adjust path if necessary

interface ThemeContextType {
  toggleTheme: () => void;
  mode: PaletteMode;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface AppThemeProviderProps {
  children: ReactNode;
}

export const AppThemeProvider: React.FC<AppThemeProviderProps> = ({ children }) => {
  const [mode, setMode] = useState<PaletteMode>(() => {
    // Get initial mode from localStorage or default to 'light'
    const savedMode = localStorage.getItem('themeMode') as PaletteMode;
    return savedMode || 'light';
  });

  useEffect(() => {
    // Save mode to localStorage whenever it changes
    localStorage.setItem('themeMode', mode);
    // Optional: Add/remove a class to the body for global non-MUI styles
    document.body.classList.remove('light', 'dark');
    document.body.classList.add(mode);
  }, [mode]);

  const toggleTheme = () => {
    setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
  };

  // Create the theme object based on the current mode
  const theme = useMemo(() => createTheme(mode === 'light' ? lightThemeOptions : darkThemeOptions), [mode]);

  const contextValue = useMemo(() => ({ toggleTheme, mode }), [toggleTheme, mode]);


  return (
    <ThemeContext.Provider value={contextValue}>
      <MuiThemeProvider theme={theme}>
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within an AppThemeProvider');
  }
  return context;
}; 