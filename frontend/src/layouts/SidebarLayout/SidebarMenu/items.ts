import type { ReactNode } from 'react';

import AnalyticsTwoToneIcon from '@mui/icons-material/AnalyticsTwoTone';
import HealthAndSafetyTwoToneIcon from '@mui/icons-material/HealthAndSafetyTwoTone';
import AssignmentIndTwoToneIcon from '@mui/icons-material/AssignmentIndTwoTone';
// import AccountTreeTwoToneIcon from '@mui/icons-material/AccountTreeTwoTone';
// import StorefrontTwoToneIcon from '@mui/icons-material/StorefrontTwoTone';
import VpnKeyTwoToneIcon from '@mui/icons-material/VpnKeyTwoTone';
// import ErrorTwoToneIcon from '@mui/icons-material/ErrorTwoTone';
// import DesignServicesTwoToneIcon from '@mui/icons-material/DesignServicesTwoTone';
// import SupportTwoToneIcon from '@mui/icons-material/SupportTwoTone';
// import ReceiptTwoToneIcon from '@mui/icons-material/ReceiptTwoTone';
// import BackupTableTwoToneIcon from '@mui/icons-material/BackupTableTwoTone';
// import SmartToyTwoToneIcon from '@mui/icons-material/SmartToyTwoTone';
import SettingsTwoToneIcon from '@mui/icons-material/SettingsTwoTone';
import MailTwoToneIcon from '@mui/icons-material/MailTwoTone';
import ForumTwoToneIcon from '@mui/icons-material/ForumTwoTone';
import AccountBoxTwoToneIcon from '@mui/icons-material/AccountBoxTwoTone';
import ListAltTwoToneIcon from '@mui/icons-material/ListAltTwoTone';
import DescriptionTwoToneIcon from '@mui/icons-material/DescriptionTwoTone';

import i18n from 'src/i18n'; // Import i18n instance

// Helper function to get translated text
const _i18n = { t: i18n.t };

export interface MenuItem {
  link?: string;
  icon?: ReactNode;
  badge?: string;
  badgeTooltip?: string;
  items?: MenuItem[];
  name: string;
}

export interface MenuItems {
  items: MenuItem[];
  heading: string;
}

const menuItems: MenuItems[] = [
  {
    heading: _i18n.t('General'),
    items: [
      // ... other top-level items like Inbox ...
      {
        name: _i18n.t('Inbox'),
        link: '/inbox',
        icon: MailTwoToneIcon // Example icon
      },
      // ... other items ...
    ]
  },
  {
    heading: _i18n.t('Management'), // Or another appropriate heading
    items: [
       {
         name: _i18n.t('Settings'),
         icon: SettingsTwoToneIcon,
         items: [
           {
             name: _i18n.t('MailMind Account'),
             link: '/settings/account',
             icon: AccountBoxTwoToneIcon
           },
           {
             name: _i18n.t('Email Accounts'),
             link: '/settings/accounts',
             icon: MailTwoToneIcon
           },
           {
             name: _i18n.t('API Credentials'),
             link: '/settings/credentials',
             icon: VpnKeyTwoToneIcon
           },
           {
             name: _i18n.t('Prompts'),
             icon: ForumTwoToneIcon,
             items: [
               {
                 name: _i18n.t('Templates'),
                 link: '/settings/prompts',
                 icon: DescriptionTwoToneIcon
               },
               {
                 name: _i18n.t('Protocol'),
                 link: '/settings/prompts/protocol',
                 icon: ListAltTwoToneIcon
               }
             ]
           }
         ]
       }
    ]
  }
  // ... other sections ...
];

export default menuItems; 