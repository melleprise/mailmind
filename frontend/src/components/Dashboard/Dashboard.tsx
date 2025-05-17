import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Grid, Paper, Typography } from '@mui/material';
import { AISuggestions } from '../AISuggestions/AISuggestions';
import { SearchComponent } from '../SearchComponent/SearchComponent';
import { MailTable } from '../MailTable/MailTable';
import { MailContent } from '../MailContent/MailContent';
import { Email } from '../../types/Email';
import { useAuth } from '../../context/AuthContext';

export const Dashboard: React.FC = () => {
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [isMailContentVisible, setIsMailContentVisible] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
  const [searchResults, setSearchResults] = useState<Email[]>([]);
  const [isLoadingSearch, setIsLoadingSearch] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const mailContentRef = useRef<HTMLDivElement>(null);
  const { token, accountId } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    console.log("[Dashboard WS Effect] Running effect. Token:", token, "Account ID:", accountId);

    if (!token || !accountId) {
      console.log("[Dashboard WS Effect] Token or Account ID is missing, ensuring WebSocket is closed.");
      if (wsRef.current) {
        console.log("[Dashboard WS Effect] Closing existing WebSocket connection due to missing token or accountId.");
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      return;
    }

    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
      console.log("[Dashboard WS Effect] WebSocket already connecting or open. Skipping connection attempt.");
      return;
    }

    console.log("[Dashboard WS Effect] Token and Account ID exist, proceeding to set up IMAP connection.");

    const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';
    const wsUrl = `${wsBaseUrl}/ws/imap/${accountId}/`;

    let isConnected = false;

    const connect = () => {
      const currentToken = localStorage.getItem('token');
      if (!currentToken) {
        console.error("[Dashboard WS Connect] Connection aborted: Token missing in localStorage just before connection attempt.");
        wsRef.current = null;
        return;
      }
       if (!accountId) {
         console.error("[Dashboard WS Connect] Connection aborted: Account ID missing just before connection attempt.");
         wsRef.current = null;
         return;
      }

      console.log(`[Dashboard WS Connect] Attempting IMAP WebSocket connection to ${wsUrl}...`);
      wsRef.current = new WebSocket(wsUrl);
      const ws = wsRef.current;

      ws.onopen = () => {
          console.log('[Dashboard IMAP WS Connect] IMAP WebSocket connection established.');
          isConnected = true;
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('[Dashboard IMAP WS Message]', message);

          if (message.type === 'email.new' && message.payload) {
             console.log('[Dashboard IMAP WS Handler] Received new email notification:', message.payload);
             setSearchResults(prev => {
               if (prev.some(e => e.id === message.payload.id)) return prev;
               return [message.payload, ...prev];
             });
          } else if (message.type === 'status' && message.status) {
             console.log(`[Dashboard IMAP WS Handler] Received status update: ${message.status}`, message.message || '');
          }
        } catch (error) {
          console.error('[Dashboard IMAP WS Message] Error parsing message:', error, 'Raw data:', event.data);
        }
      };

      ws.onerror = (error) => {
          console.error('[Dashboard IMAP WS Connect] IMAP WebSocket error:', error);
      };

      ws.onclose = (event) => {
          console.log(`[Dashboard IMAP WS Connect] IMAP WebSocket closed. Code: ${event.code}, Reason: ${event.reason}, Clean: ${event.wasClean}`);
          wsRef.current = null;
          isConnected = false;
          const shouldReconnect = token && accountId && event.code !== 1000;
          if (shouldReconnect) {
            if (!reconnectTimeoutRef.current) {
              console.log('[Dashboard IMAP WS Connect] Attempting WebSocket reconnect in 5 seconds...');
              reconnectTimeoutRef.current = setTimeout(() => {
                reconnectTimeoutRef.current = null;
                connect();
              }, 5000);
            }
          }
      };
    };

    connect();

    return () => {
      console.log('[Dashboard IMAP WS Effect Cleanup] Running useEffect cleanup...');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        console.log('[Dashboard IMAP WS Effect Cleanup] Closing IMAP WebSocket connection.');
        wsRef.current.close(1000, "Component unmounting");
        wsRef.current = null;
      }
    };
  }, [token, accountId, selectedEmail]);

  // --- WebSocket für allgemeine User-Events (email.new) ---
  useEffect(() => {
    if (!token) return;
    const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';
    const wsUrl = `${wsBaseUrl}/ws/general/?token=${encodeURIComponent(token)}`;
    console.log('[Dashboard GENERAL WS] Attempting connection to:', wsUrl);
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout | null = null;

    const connect = () => {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => {
        console.log('[Dashboard GENERAL WS] WebSocket connected.', wsUrl);
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
          reconnectTimeout = null;
        }
      };
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('[Dashboard GENERAL WS] Message received:', message);
          if (message.type === 'email.new' && message.payload) {
            setSearchResults(prev => {
              if (prev.some(e => e.id === message.payload.id)) {
                console.log('[Dashboard GENERAL WS] Email already exists in list, skipping:', message.payload.id);
                return prev;
              }
              console.log('[Dashboard GENERAL WS] Adding new email to list:', message.payload.id);
              return [message.payload, ...prev];
            });
          }
          if (message.type === 'email.refresh') {
            console.log('[Dashboard GENERAL WS] email.refresh empfangen, triggere Reload der E-Mail-Liste.');
            window.location.reload(); // oder: fetchEmails() aufrufen, wenn vorhanden
          }
        } catch (err) {
          console.error('[Dashboard GENERAL WS] Error parsing message:', err, event.data);
        }
      };
      ws.onerror = (err) => {
        console.error('[Dashboard GENERAL WS] WebSocket error:', err);
      };
      ws.onclose = (event) => {
        console.log(`[Dashboard GENERAL WS] WebSocket closed. Code: ${event.code}, Reason: ${event.reason}, Clean: ${event.wasClean}`);
        ws = null;
        if (event.code !== 1000 && !reconnectTimeout) {
          reconnectTimeout = setTimeout(connect, 5000);
        }
      };
    };
    connect();
    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close(1000, 'Component unmounting');
    };
  }, [token]);

  const handleSelectEmail = (email: Email | null) => {
    // ... (existing code)
  };

  // ... rest of the component ...
}; 