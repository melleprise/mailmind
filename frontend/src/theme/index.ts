import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3',
      light: '#64b5f6',
      dark: '#1976d2',
      contrastText: '#fff'
    },
    secondary: {
      main: '#8c8c8c',
      light: '#bdbdbd',
      dark: '#616161',
      contrastText: '#fff'
    },
    error: {
      main: '#f44336',
      light: '#e57373',
      dark: '#d32f2f',
      contrastText: '#fff'
    },
    warning: {
      main: '#ffc107',
      light: '#ffb74d',
      dark: '#f57c00',
      contrastText: '#fff'
    },
    info: {
      main: '#03a9f4',
      light: '#4fc3f7',
      dark: '#0288d1',
      contrastText: '#fff'
    },
    success: {
      main: '#00c853',
      light: '#69f0ae',
      dark: '#00a041',
      contrastText: '#fff'
    },
    grey: {
      50: '#fafafa',
      100: '#f5f5f5',
      200: '#eeeeee',
      300: '#e0e0e0',
      400: '#bdbdbd',
      500: '#9e9e9e',
      600: '#757575',
      700: '#616161',
      800: '#424242',
      900: '#212121',
    },
    background: {
      default: '#f8f9fa',
      paper: '#ffffff'
    },
    text: {
      primary: '#212121',
      secondary: '#757575',
      disabled: '#9e9e9e'
    },
    divider: 'rgba(0, 0, 0, 0.12)'
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: '8px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none'
          }
        }
      }
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: '12px',
          boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.05)'
        }
      }
    }
  }
}); 