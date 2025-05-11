import React from 'react';
import { Link as RouterLink, useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Link,
  Avatar,
  IconButton,
  Menu,
  MenuItem,
  useTheme as useMuiTheme
} from '@mui/material';
import {
  Mail as MailIcon,
  LightbulbOutlined as LightbulbIcon,
  FolderOutlined as FolderIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Dashboard as DashboardIcon,
  DashboardOutlined as DashboardOutlinedIcon,
  PersonAddOutlined as PersonAddOutlinedIcon,
  AssignmentIndOutlined as AssignmentIndOutlinedIcon,
  GroupAddOutlined as GroupAddOutlinedIcon,
  BusinessOutlined as BusinessOutlinedIcon,
  MonetizationOnOutlined as MonetizationOnOutlinedIcon,
  TrendingUpOutlined as TrendingUpOutlinedIcon,
  FlagOutlined as FlagOutlinedIcon,
  StarOutlined as StarOutlinedIcon
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

const Navbar: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const { mode, toggleTheme } = useTheme();
  const muiTheme = useMuiTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleClose();
    logout();
  };

  const handleSettings = () => {
    handleClose();
    navigate('/settings');
  };

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        bgcolor: muiTheme.palette.background.paper,
        borderBottom: '1px solid',
        borderColor: muiTheme.palette.divider,
      }}
    >
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          {isAuthenticated ? (
            <>
              <IconButton 
                component={RouterLink} 
                to="/leads" 
                sx={{ p: 0, mr: 6, my: 1.5 }}
              >
                <MonetizationOnOutlinedIcon 
                  sx={{ 
                    color: location.pathname.startsWith('/leads') 
                      ? 'primary.main' 
                      : 'text.secondary' 
                  }} 
                />
              </IconButton>
              <IconButton 
                component={RouterLink}
                to={"/mail"} 
                sx={{ p: 0, mr: 4, my: 1.5 }}
              >
                <MailIcon 
                  sx={{ 
                    color: location.pathname === '/' || location.pathname === '/mail' || location.pathname === '/dashboard'
                      ? 'primary.main' 
                      : 'text.secondary' 
                  }} 
                />
              </IconButton>
              <IconButton
                component={RouterLink}
                to="/aisearch"
                sx={{ color: 'text.secondary', my: 1.5, ml: 1 }}
                title="AI Search"
              >
                <FolderIcon 
                  sx={{ 
                    color: location.pathname.startsWith('/aisearch') 
                      ? 'primary.main' 
                      : 'text.secondary' 
                  }} 
                />
              </IconButton>
            </>
          ) : (
            <>
              <IconButton 
                component={RouterLink}
                to="/" 
                sx={{ p: 0, mr: 4, my: 1.5 }}
              >
                <MailIcon 
                  sx={{ color: 'primary.main' }} 
                />
              </IconButton>
              <Typography variant="h6" sx={{ color: 'text.primary', fontWeight: 700, ml: 0 }}>
                mailmind
              </Typography>
            </>
          )}
        </Box>

        <Box sx={{ flexGrow: 1 }} />

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 1 }}>
          <IconButton
            onClick={toggleTheme}
            color="inherit"
            sx={{ color: 'text.secondary' }}
            title={`Toggle ${mode === 'light' ? 'dark' : 'light'} mode`}
          >
            {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
          </IconButton>

          {isAuthenticated && (
            <IconButton
              component={RouterLink}
              to="/settings"
              sx={{ color: 'text.secondary' }}
              title="Settings"
            >
              <SettingsIcon />
            </IconButton>
          )}
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {isAuthenticated ? (
            <>
              <IconButton
                size="large"
                aria-label="account of current user"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                onClick={handleMenu}
                color="inherit"
              >
                <Avatar
                  sx={{
                    bgcolor: 'primary.main',
                    width: 32,
                    height: 32,
                  }}
                >
                  {user?.email.charAt(0).toUpperCase()}
                </Avatar>
              </IconButton>
              <Menu
                id="menu-appbar"
                anchorEl={anchorEl}
                anchorOrigin={{
                  vertical: 'bottom',
                  horizontal: 'right',
                }}
                keepMounted
                transformOrigin={{
                  vertical: 'top',
                  horizontal: 'right',
                }}
                open={open}
                onClose={handleClose}
                PaperProps={{
                  sx: {
                    backgroundColor: 'background.paper',
                    color: 'text.primary',
                  }
                }}
              >
                <MenuItem disabled sx={{ opacity: '1 !important' }}>
                  <Typography variant="body2" sx={{ fontWeight: 500, color: 'text.primary' }}>
                    {user?.email}
                  </Typography>
                </MenuItem>
                <MenuItem onClick={handleLogout} sx={{ color: 'text.secondary' }}>
                  <LogoutIcon sx={{ mr: 1 }} /> Logout
                </MenuItem>
              </Menu>
            </>
          ) : (
            <>
              <Button
                variant="text"
                component={RouterLink}
                to="/login"
                sx={{ color: 'text.secondary' }}
              >
                Login
              </Button>
              <Button
                variant="contained"
                component={RouterLink}
                to="/register"
              >
                Register
              </Button>
            </>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar; 