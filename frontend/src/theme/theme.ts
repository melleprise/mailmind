import { createTheme, ThemeOptions } from '@mui/material/styles';

// Base options shared between light and dark themes
const baseThemeOptions: ThemeOptions = {
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 500,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 500,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 500,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 500,
    },
    h5: {
      fontSize: '1rem',
      fontWeight: 500,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 500,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)', // Consider adjusting shadow for dark mode
        },
      },
    },
    // Component overrides might need theme-specific adjustments below
  },
};

// Light theme specific options
export const lightThemeOptions: ThemeOptions = {
  ...baseThemeOptions,
  palette: {
    mode: 'light',
    primary: {
      main: '#673ab7', // Example Light Primary
      light: '#9a67ea',
      dark: '#320b86',
    },
    secondary: {
      main: '#f50057', // Example Light Secondary
      light: '#ff5983',
      dark: '#bb002f',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
    text: {
      primary: 'rgba(0, 0, 0, 0.87)',
      secondary: 'rgba(0, 0, 0, 0.6)',
    },
    error: {
      main: '#f44336',
    },
    success: {
      main: '#2eb750',
    },
  },
  components: {
    ...baseThemeOptions.components,
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
          backgroundColor: '#ffffff', // Light App Bar
          color: '#111',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          '&.Mui-selected': {
            backgroundColor: 'rgba(103, 58, 183, 0.1)', // Use light primary
          },
          '&.Mui-selected:hover': {
            backgroundColor: 'rgba(103, 58, 183, 0.2)', // Use light primary
          },
          '&:hover': {
            backgroundColor: 'rgba(0, 0, 0, 0.04)',
          },
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: 'rgba(0, 0, 0, 0.12)', // Standard light divider
        },
      },
    },
    MuiAvatar: {
      styleOverrides: {
        root: {
          backgroundColor: '#673ab7', // Example Light Avatar background
        },
      },
    },
     MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)', // Light mode shadow
        },
      },
    },
  },
};

// Dark theme specific options (Based on original theme.ts)
export const darkThemeOptions: ThemeOptions = {
  ...baseThemeOptions,
  palette: {
    mode: 'dark',
    primary: {
      main: '#be85ff',
      light: '#d5b0ff',
      dark: '#9a67e0',
    },
    secondary: {
      main: '#7c55d6',
      light: '#9f7de8',
      dark: '#5c3eb8',
    },
    background: {
      default: '#121212', // Common dark background
      paper: '#1e1e1e',   // Common dark paper
    },
    text: {
        primary: '#ffffff',
        secondary: 'rgba(255, 255, 255, 0.7)',
    },
    error: {
      main: '#f44336',
    },
    success: {
      main: '#2eb750',
    },
  },
  components: {
     ...baseThemeOptions.components,
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          // Style autofill specifically for dark mode
          '& input:-webkit-autofill': {
            WebkitBoxShadow: '0 0 0 100px #303030 inset !important', // Dark gray background
            WebkitTextFillColor: '#fff !important', // White text
            caretColor: '#fff !important', // White caret
            borderRadius: 'inherit', // Inherit border radius
          },
          // Firefox autofill
          '& input:-moz-autofill': {
            boxShadow: '0 0 0 100px #303030 inset !important',
            filter: 'none',
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.5)', // Adjusted shadow for dark
          backgroundColor: '#1e1e1e', // Dark App Bar
          color: '#fff',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          '&.Mui-selected': {
            backgroundColor: 'rgba(190, 133, 255, 0.1)', // Original dark selection
          },
          '&.Mui-selected:hover': {
            backgroundColor: 'rgba(190, 133, 255, 0.2)', // Original dark selection hover
          },
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.08)', // Dark hover
          },
        },
      },
    },
     MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: 'rgba(255, 255, 255, 0.12)', // Standard dark divider
        },
      },
    },
     MuiAvatar: {
      styleOverrides: {
        root: {
          backgroundColor: '#be85ff', // Original dark avatar
        },
      },
    },
     MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          backgroundColor: '#1e1e1e',
          boxShadow: '0 2px 8px rgba(0,0,0,0.4)', // Adjusted dark shadow
        },
      },
    },
    MuiOutlinedInput: { // Override for Outlined TextField
      styleOverrides: {
        root: ({ theme }) => ({
           // Ensure the background matches the paper color in dark mode
          backgroundColor: '#303030', // Use the autofill background color for consistency
          // Prevent background change on hover/focus if needed
          '&:hover .MuiOutlinedInput-notchedOutline': {
            // borderColor: theme.palette.primary.light, // Example customization
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
             // borderColor: theme.palette.primary.main, // Example customization
          },
          // Ensure adornments have the same background implicitly
          '& .MuiInputAdornment-root': {
              backgroundColor: 'inherit', // Inherit from root
          }
        }),
      }
    }
  },
}; 