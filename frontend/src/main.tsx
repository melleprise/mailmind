import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { AppThemeProvider } from './contexts/ThemeContext';
import { HelmetProvider } from 'react-helmet-async';
import i18n from './i18n'; // Import i18next configuration AND the instance
import { I18nextProvider } from 'react-i18next'; // Import the provider
import { queryClient } from './lib/queryClient'; // Import from the new file

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppThemeProvider>
            <AuthProvider>
              <I18nextProvider i18n={i18n}> {/* Wrap App with the provider */}
                <App />
              </I18nextProvider>
            </AuthProvider>
          </AppThemeProvider>
        </BrowserRouter>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </HelmetProvider>
  </React.StrictMode>
); 