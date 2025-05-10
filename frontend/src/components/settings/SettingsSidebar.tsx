import React, { useState } from 'react';
import {
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Paper,
  Typography,
  Collapse
} from '@mui/material';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import EmailIcon from '@mui/icons-material/Email';
import KeyIcon from '@mui/icons-material/Key';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import PersonIcon from '@mui/icons-material/Person'; // Example for specific account
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import VpnKeyIcon from '@mui/icons-material/VpnKey'; // Icon for specific credential
import DescriptionIcon from '@mui/icons-material/Description';
import ListAltIcon from '@mui/icons-material/ListAlt';
import SettingsIcon from '@mui/icons-material/Settings'; // Example, adjust if needed
import PsychologyIcon from '@mui/icons-material/Psychology'; // Icon for Knowledge
import BuildIcon from '@mui/icons-material/Build'; // Icon for Actions
import EditIcon from '@mui/icons-material/Edit';
import SyncIcon from '@mui/icons-material/Sync';
import MonetizationOnOutlinedIcon from '@mui/icons-material/MonetizationOnOutlined';
import WorkOutlineIcon from '@mui/icons-material/WorkOutline';

// Assuming EmailAccount interface is defined elsewhere or passed
interface EmailAccount {
  id: number;
  name: string;
  email: string;
}

// Placeholder for API Credential interface
interface ApiCredential {
  id: string; // e.g., 'groq' or a generated ID
  name: string; // e.g., 'Groq'
}

interface SettingsSidebarProps {
  accounts: EmailAccount[];
  selectedSection: string;
  onSelectSection: (section: string) => void;
}

// Define constants for section keys
const SECTION_MAILMIND_ACCOUNT = 'mailmind_account';
const SECTION_EMAIL_ACCOUNTS = 'email_accounts';
const SECTION_EMAIL_ACCOUNT_ADD = 'email_account_add';
const SECTION_API_CREDENTIALS = 'api_credentials';
// Keys for the now top-level prompt sections
const SECTION_PROMPT_TEMPLATES = 'prompts_templates'; 
const SECTION_PROMPT_PROTOCOL = 'prompts_protocol'; 
const SECTION_KNOWLEDGE = 'knowledge'; 
const SECTION_ACTIONS = 'actions';     
const SECTION_LEADS = 'leads';
const SECTION_LEADS_FREELANCE = 'leads_freelance';

const SettingsSidebar: React.FC<SettingsSidebarProps> = ({
  accounts,
  selectedSection,
  onSelectSection,
}) => {
  const [emailAccountsOpen, setEmailAccountsOpen] = useState(false);
  const [apiCredentialsOpen, setApiCredentialsOpen] = useState(false);

  // Placeholder for API credentials data
  const apiCredentials: ApiCredential[] = [
    { id: 'groq', name: 'Groq' },
    { id: 'google_gemini', name: 'Google Gemini' }, // Added Google Gemini
  ];

  const handleEmailAccountsClick = () => {
    setEmailAccountsOpen(!emailAccountsOpen);
    setApiCredentialsOpen(false);
  };

  const handleApiCredentialsClick = () => {
    setApiCredentialsOpen(!apiCredentialsOpen);
    setEmailAccountsOpen(false);
  };

  // NEW handler for top-level, non-collapsible items
  const handleTopLevelSelect = (sectionKey: string) => {
    setEmailAccountsOpen(false); // Close email menu
    setApiCredentialsOpen(false); // Close API menu
    onSelectSection(sectionKey); // Call the original selection handler
  };

  // Basic sections - Define the static top-level items separately
  const staticMenuItems = [
    { key: SECTION_MAILMIND_ACCOUNT, text: 'MailMind Account', icon: <AccountCircleIcon /> },
    { key: SECTION_PROMPT_TEMPLATES, text: 'Templates', icon: <DescriptionIcon /> },
    { key: SECTION_KNOWLEDGE, text: 'Knowledge', icon: <PsychologyIcon /> },
    { key: SECTION_ACTIONS, text: 'Actions', icon: <BuildIcon /> },
    { key: SECTION_LEADS, text: 'Leads', icon: <MonetizationOnOutlinedIcon />, children: [
      { key: SECTION_LEADS_FREELANCE, text: 'freelance.de', icon: <ListAltIcon /> }
    ] },
    { key: SECTION_PROMPT_PROTOCOL, text: 'Protocol', icon: <ListAltIcon /> },
  ];

  return (
    <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
      <List component="nav" dense>
        {/* MailMind Account (uses handleTopLevelSelect) */}
        <ListItemButton
          key={SECTION_MAILMIND_ACCOUNT}
          selected={selectedSection === SECTION_MAILMIND_ACCOUNT}
          onClick={() => handleTopLevelSelect(SECTION_MAILMIND_ACCOUNT)} 
        >
          <ListItemIcon sx={{ minWidth: 36 }}><AccountCircleIcon /></ListItemIcon>
          <ListItemText primary="MailMind Account" />
        </ListItemButton>

        {/* Email Accounts (Collapsible) */}
        <React.Fragment key={SECTION_EMAIL_ACCOUNTS}>
          <ListItemButton onClick={handleEmailAccountsClick} selected={selectedSection.startsWith('email_account_')}> 
            <ListItemIcon sx={{ minWidth: 36 }}><EmailIcon /></ListItemIcon>
            <ListItemText primary="Email Accounts" />
            {emailAccountsOpen ? <ExpandLess /> : <ExpandMore />} 
          </ListItemButton>
          <Collapse in={emailAccountsOpen} timeout="auto" unmountOnExit>
            <List component="div" disablePadding dense>
              <ListItemButton 
                sx={{ pl: 4 }}
                selected={selectedSection === 'email_account_add'}
                onClick={() => onSelectSection('email_account_add')}
              >
                <ListItemIcon sx={{ minWidth: 36 }}><AddCircleOutlineIcon fontSize="small" /></ListItemIcon>
                <ListItemText primary="Add Account" primaryTypographyProps={{ variant: 'body2' }}/>
              </ListItemButton>
              {accounts.map((account) => (
                <ListItemButton
                  key={`account-edit-${account.id}`}
                  selected={selectedSection === `email_account_edit_${account.id}`}
                  onClick={() => onSelectSection(`email_account_edit_${account.id}`)}
                  sx={{ pl: 4 }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}><PersonIcon fontSize="small" /></ListItemIcon>
                  <ListItemText primary={account.name || account.email} primaryTypographyProps={{ variant: 'body2', noWrap: true }}/>
                </ListItemButton>
              ))}
            </List>
          </Collapse>
        </React.Fragment>

        {/* API Credentials (Collapsible) */}
        <React.Fragment key={SECTION_API_CREDENTIALS}>
          <ListItemButton onClick={handleApiCredentialsClick} selected={selectedSection.startsWith('api_credential_')}> 
            <ListItemIcon sx={{ minWidth: 36 }}><KeyIcon /></ListItemIcon>
            <ListItemText primary="API Credentials" />
            {apiCredentialsOpen ? <ExpandLess /> : <ExpandMore />} 
          </ListItemButton>
          <Collapse in={apiCredentialsOpen} timeout="auto" unmountOnExit>
            <List component="div" disablePadding dense>
              {apiCredentials.map((cred) => (
                <ListItemButton
                  key={`api-cred-edit-${cred.id}`}
                  selected={selectedSection === `api_credential_edit_${cred.id}`}
                  onClick={() => onSelectSection(`api_credential_edit_${cred.id}`)}
                  sx={{ pl: 4 }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}><VpnKeyIcon fontSize="small" /></ListItemIcon>
                  <ListItemText primary={cred.name} primaryTypographyProps={{ variant: 'body2', noWrap: true }}/>
                </ListItemButton>
              ))}
            </List>
          </Collapse>
        </React.Fragment>

        {/* Static Top-Level Items (using handleTopLevelSelect) */}
        {staticMenuItems.map((item) => {
          if (item.key === SECTION_MAILMIND_ACCOUNT) return null;
          if (item.key === SECTION_LEADS) {
            return (
              <React.Fragment key={item.key}>
                <ListItem disablePadding>
                  <ListItemButton onClick={() => handleTopLevelSelect(item.key)} selected={selectedSection === item.key}>
                    <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.text} />
                  </ListItemButton>
                </ListItem>
                {/* Unterpunkt für freelance.de */}
                <ListItem disablePadding sx={{ pl: 4 }}>
                  <ListItemButton onClick={() => handleTopLevelSelect(SECTION_LEADS_FREELANCE)} selected={selectedSection === SECTION_LEADS_FREELANCE} sx={{ pl: 4 }}>
                    <ListItemIcon sx={{ minWidth: 36 }}><WorkOutlineIcon /></ListItemIcon>
                    <ListItemText primary="freelance.de" />
                  </ListItemButton>
                </ListItem>
              </React.Fragment>
            );
          }
          return (
            <ListItem disablePadding key={item.key}>
              <ListItemButton onClick={() => handleTopLevelSelect(item.key)} selected={selectedSection === item.key}>
                <ListItemIcon sx={{ minWidth: 36 }}> 
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} /> 
              </ListItemButton>
            </ListItem>
          );
        })}

      </List>
    </Paper>
  );
};

export default SettingsSidebar; 