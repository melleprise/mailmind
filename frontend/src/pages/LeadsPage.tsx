import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Button,
  Avatar,
  Divider,
  IconButton,
  CircularProgress,
  TextField,
  Alert,
  List,
  ListItem,
  ListItemText,
  Paper,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  Refresh as RefreshIcon,
  Archive as ArchiveIcon,
  Send as SendIcon,
  Sync as SyncIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { api as apiClient } from '../services/api';
import { ActionButton } from '../components/actions/ActionButton';
import { AIAgentInput } from '../components/AISuggestions/AIAgentInput';
import { ReplyLeadView } from '../components/ReplyLeadView';

interface LeadProject {
  id: number;
  project_id: string;
  title: string;
  company: string;
  location: string;
  remote: boolean;
  end_date: string;
  last_updated: string;
  skills: string[];
  url: string;
  applications: number;
  provider: string;
  logo_url: string;
  hourly_rate?: string;
  created_at: string;
  description?: string;
}

interface PaginatedLeadResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: LeadProject[];
}

// WebSocket-URL: Für lokale Entwicklung localhost, für Docker-Container backend
const WS_BASE = import.meta.env.VITE_WS_BASE_URL || (window.location.hostname === 'localhost' ? 'ws://localhost:8000' : 'ws://backend:8000');
const WS_URL = WS_BASE + '/ws/leads/';
const CRAWL4AI_API =
  import.meta.env.VITE_CRAWL4AI_API_URL ||
  (window.location.hostname === 'localhost'
    ? 'http://localhost:11235'
    : 'http://crawl4ai:11235');

const LeadsPage: React.FC = () => {
  const [leads, setLeads] = useState<LeadProject[]>([]);
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalLeads, setTotalLeads] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [selectedLead, setSelectedLead] = useState<LeadProject | null>(null);
  const [leadAction, setLeadAction] = useState<string | null>(null);
  const [isListCollapsed, setIsListCollapsed] = useState(false);
  const [isDetailExpanded, setIsDetailExpanded] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);
  const detailRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const { token, user } = useAuth();

  // WebSocket-Initialisierung
  useEffect(() => {
    if (!token) {
      console.warn('[WebSocket] Kein Token vorhanden, keine Verbindung aufgebaut.');
      return;
    }
    let ws: WebSocket;
    let reconnectTries = 0;
    function connectWS() {
      const wsUrlWithToken = WS_URL + '?token=' + encodeURIComponent(token!);
      ws = new window.WebSocket(wsUrlWithToken);
      wsRef.current = ws;
      setLoading(true);
      ws.onopen = () => {
        reconnectTries = 0;
        setError(null);
        // Kein automatischer get_leads-Request mehr
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'leads_init' || data.type === 'leads_updated') {
            setLeads(data.projects.map((p: any, idx: number) => ({ ...p, id: idx + 1 })));
            setTotalLeads(data.pagination?.total || 0);
            setHasMore((data.pagination?.page || 1) * (data.pagination?.page_size || 20) < (data.pagination?.total || 0));
            setCurrentPage(data.pagination?.page || 1);
            setLoading(false);
            if (data.projects.length > 0 && !selectedLeadId) {
              setSelectedLeadId(data.projects[0].id);
              setSelectedLead(data.projects[0]);
            }
          } else if (data.type === 'error') {
            setError(data.detail || 'Unbekannter Fehler');
            setLoading(false);
          } else if (data.type === 'lead_details') {
            // Optional: Details-Handling
            setSelectedLead(data.details);
          }
        } catch (e) {
          setError('Fehler beim Verarbeiten der WebSocket-Daten');
          setLoading(false);
        }
      };
      ws.onerror = () => {
        setError('WebSocket-Fehler');
        setLoading(false);
      };
      ws.onclose = () => {
        setLoading(false);
        if (reconnectTries < 5) {
          reconnectTries++;
          reconnectTimeout.current = setTimeout(connectWS, 1000 * reconnectTries);
        } else {
          setError('WebSocket-Verbindung getrennt. Bitte Seite neu laden.');
        }
      };
    }
    connectWS();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
  }, [token]);

  // Sync-Button → Seite 1 neu laden
  const handleSync = useCallback(async () => {
    setLoading(true);
    setError(null);
    const userId = user && user.id;
    console.log('[Sync] Button gedrückt. user:', user, 'userId:', userId, 'token:', token);
    if (!token) {
      setError('Kein Auth-Token vorhanden!');
      console.warn('[Sync] Kein Auth-Token vorhanden!');
      return;
    }
    // Crawl-Trigger an Backend
    if (userId) {
      try {
        const response = await fetch(`${CRAWL4AI_API}/crawl-freelance-sync`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Token ${token}`,
            'X-User-Id': userId.toString(),
          },
        });
        console.log('[Sync] Response Status:', response.status);
        const text = await response.text();
        console.log('[Sync] Response Body:', text);
        if (!response.ok) {
          setError('Fehler beim Starten des Crawls: ' + text);
        }
      } catch (e) {
        setError('Fehler beim Starten des Crawls');
        console.error('[Sync] Fehler beim Crawl-Request:', e);
      }
    } else {
      console.warn('[Sync] Kein user.id vorhanden!');
    }
    wsRef.current?.send(JSON.stringify({ type: 'get_leads', page: 1, page_size: 20 }));
  }, [user, token]);

  // Pagination (Mehr laden)
  const handleLoadMore = useCallback(() => {
    if (hasMore && !loading) {
      setLoading(true);
      wsRef.current?.send(JSON.stringify({ type: 'get_leads', page: currentPage + 1, page_size: 20 }));
    }
  }, [hasMore, loading, currentPage]);

  // Lead auswählen (optional: Details nachladen)
  const handleSelectLead = useCallback((id: number) => {
    setSelectedLeadId(id);
    const selected = leads.find(lead => lead.id === id) || null;
    setSelectedLead(selected);
    // Optional: Details nachladen
    // wsRef.current?.send(JSON.stringify({ type: 'lead_details', project_id: selected?.project_id }));
  }, [leads]);

  // Click-Handler für horizontales Toggle-Verhalten
  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (detailRef.current && detailRef.current.contains(target)) {
        setIsListCollapsed(false);
        setIsDetailExpanded(false);
      } else if (listRef.current && !listRef.current.contains(target) && detailRef.current && !detailRef.current.contains(target)) {
        setIsListCollapsed(true);
        setIsDetailExpanded(true);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Lead-Bewerben-Funktion (Placeholder)
  const handleApply = useCallback((id: number) => {
    setLeadAction('reply');
  }, []);

  // Lead-Ignorieren-Funktion (Placeholder)  
  const handleIgnore = useCallback((id: number) => {
    console.log(`Lead ${id} ignoriert`);
    // Hier Logik für Ignorieren implementieren
  }, []);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'row',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Linke Spalte: Lead-Liste */}
      <Box
        ref={listRef}
        sx={{
          width: isListCollapsed ? '60px' : '300px',
          minWidth: isListCollapsed ? '60px' : '300px',
          flexShrink: 0,
          height: '100%',
          borderRight: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
          bgcolor: 'background.paper',
          alignItems: isListCollapsed ? 'center' : 'stretch',
          transition: (theme) => theme.transitions.create(['width', 'min-width'], { duration: theme.transitions.duration.enteringScreen, easing: theme.transitions.easing.easeInOut }),
          cursor: isListCollapsed ? 'pointer' : 'default',
        }}
        onClick={() => {
          if (isListCollapsed) {
            setIsListCollapsed(false);
            setIsDetailExpanded(false);
          }
        }}
      >
        <Box sx={{ position: 'relative', p: isListCollapsed ? 0.5 : 1, borderBottom: '1px solid', borderColor: 'divider', flexShrink: 0, textAlign: isListCollapsed ? 'center' : 'left' }}>
          <Typography variant="h6" sx={{ fontSize: isListCollapsed ? '1.2rem' : '1.5rem', display: isListCollapsed ? 'none' : 'block' }}>Freelance Projekte</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ display: isListCollapsed ? 'none' : 'block' }}>
            {totalLeads} Projekte gefunden
          </Typography>
          {!isListCollapsed && (
            <Tooltip title="Synchronisieren">
              <span style={{ position: 'absolute', right: 16, top: 16, zIndex: 2 }}>
                {loading ? <CircularProgress size={24} /> : <IconButton onClick={handleSync} size="small"><SyncIcon /></IconButton>}
              </span>
            </Tooltip>
          )}
          {isListCollapsed && (
            <Box sx={{ width: 36, height: 36, borderRadius: '50%', bgcolor: 'primary.main', mx: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 500, fontSize: '0.8rem', p: 0 }}>
              {totalLeads}
            </Box>
          )}
        </Box>
        <Box sx={{ flexGrow: 1, width: '100%', overflowY: 'auto' }}>
          <List disablePadding>
            {leads.map((lead) => (
              <ListItem
                key={lead.id}
                button
                selected={selectedLeadId === lead.id}
                onClick={() => handleSelectLead(lead.id)}
                sx={{
                  justifyContent: isListCollapsed ? 'center' : 'flex-start',
                  px: isListCollapsed ? 0 : 2,
                  py: isListCollapsed ? 1 : 1.5,
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                  '&.Mui-selected': { bgcolor: 'action.selected' },
                  '&.Mui-selected:hover': { bgcolor: 'action.selected' },
                  transition: (theme) => theme.transitions.create(['padding', 'justify-content'], { duration: theme.transitions.duration.shortest })
                }}
                disablePadding
              >
                {isListCollapsed ? (
                  <Tooltip title={lead.company + ' – ' + lead.title} placement="right">
                    <Box sx={{ width: 32, height: 32, borderRadius: '50%', bgcolor: '#666', mx: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 500, fontSize: '1rem' }}>
                      {lead.company.charAt(0)}
                    </Box>
                  </Tooltip>
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
                    <Typography variant="body2" color="primary.main" sx={{ fontWeight: 'bold', mb: 0.5 }} noWrap>
                      {lead.company}
                    </Typography>
                    <Typography variant="body2" color="primary.main" sx={{ fontWeight: 'medium', mb: 0.5 }} noWrap>
                      {lead.title}
                    </Typography>
                    <Typography variant="caption" color="text.primary" noWrap>
                      {lead.location} {lead.remote ? '(Remote)' : ''} • {lead.hourly_rate || 'Kein Preis angegeben'}
                    </Typography>
                  </Box>
                )}
              </ListItem>
            ))}
            {!hasMore && !loading && leads.length > 0 && (
              <ListItem sx={{ justifyContent: 'center', py: isListCollapsed ? 1 : 2 }}>
                <Typography variant="caption" color="text.secondary">Ende der Liste</Typography>
              </ListItem>
            )}
          </List>
        </Box>
      </Box>

      {/* Rechte Spalte: Lead-Details */}
      <Box
        ref={detailRef}
        sx={{
          flexGrow: 1,
          width: 'auto',
          height: '100%',
          overflowY: 'auto',
          bgcolor: 'background.paper',
          borderRight: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
          transition: (theme) => theme.transitions.create(['margin-left', 'margin-right'], { duration: theme.transitions.duration.enteringScreen, easing: theme.transitions.easing.easeInOut })
        }}
      >
        {selectedLead ? (
          <Box sx={{ p: 1, flexGrow: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Box>
                <Typography variant="h5" gutterBottom>
                  {selectedLead.title}
                </Typography>
                <Typography variant="subtitle1" color="text.secondary" gutterBottom>
                  {selectedLead.company} - {selectedLead.location} {selectedLead.remote ? '(Remote)' : ''}
                </Typography>
                {selectedLead.hourly_rate && (
                  <Typography variant="body2" color="text.secondary">
                    Stundensatz: {selectedLead.hourly_rate}
                  </Typography>
                )}
              </Box>
              
              <Box>
                <Avatar src={selectedLead.logo_url || ''} alt={selectedLead.company}>
                  {selectedLead.company.charAt(0)}
                </Avatar>
              </Box>
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Projektbeschreibung
              </Typography>
              <Typography variant="body1" style={{ whiteSpace: 'pre-line' }}>
                {selectedLead.description || 'Keine Beschreibung verfügbar.'}
              </Typography>
            </Box>
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Skills
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {selectedLead.skills.map((skill, index) => (
                  <Box
                    key={index}
                    sx={{
                      backgroundColor: 'action.selected',
                      borderRadius: 1,
                      px: 1.5,
                      py: 0.5,
                    }}
                  >
                    <Typography variant="body2">{skill}</Typography>
                  </Box>
                ))}
              </Box>
            </Box>
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary">
                Bewerbungen: {selectedLead.applications}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Provider: {selectedLead.provider}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Enddatum: {selectedLead.end_date ? new Date(selectedLead.end_date).toLocaleDateString() : 'Nicht angegeben'}
              </Typography>
            </Box>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Typography variant="body1" color="text.secondary">
              Kein Projekt ausgewählt
            </Typography>
          </Box>
        )}
      </Box>

      {/* Rechte Spalte: Aktionen */}
      <Box
        sx={{
          width: isDetailExpanded ? '50%' : '300px',
          minWidth: isDetailExpanded ? '400px' : '300px',
          maxWidth: '60%',
          flexShrink: 0,
          height: '100%',
          bgcolor: 'background.paper',
          display: 'flex',
          flexDirection: 'column',
          borderLeft: '1px solid',
          borderColor: 'divider',
          overflow: 'hidden',
          transition: (theme) => theme.transitions.create(['width', 'min-width', 'max-width'], { duration: theme.transitions.duration.enteringScreen, easing: theme.transitions.easing.easeInOut })
        }}
      >
        {selectedLead ? (
          leadAction === 'reply' ? (
            <Box sx={{ p: 1, height: '100%' }}>
              <ReplyLeadView
                selectedEmailId={selectedLead.id}
                suggestions={[]}
                originalSender={selectedLead.company}
                currentEmailDetail={null}
                isExpanded={true}
                onExpandRequest={() => {}}
                onUpdateSuggestion={async () => {}}
                loading={false}
                setEmailAction={() => setLeadAction(null)}
                handleInternalRefresh={() => {}}
              />
            </Box>
          ) : (
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 1 }}>
              <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: 1, overflowY: 'auto' }}>
                <ActionButton
                  icon={<ThumbUpIcon fontSize="medium" />}
                  label="Bewerben"
                  onClick={() => handleApply(selectedLead.id)}
                />
                <ActionButton
                  icon={<ThumbDownIcon fontSize="medium" />}
                  label="Ignorieren"
                  onClick={() => handleIgnore(selectedLead.id)}
                />
                <ActionButton
                  icon={<RefreshIcon fontSize="medium" />}
                  label="Zum Original"
                  onClick={() => window.open(selectedLead.url, '_blank')}
                />
              </Box>
              <Box sx={{ flexShrink: 0, mt: 1 }}>
                <AIAgentInput isExpanded={true} onExpandRequest={() => {}} />
              </Box>
            </Box>
          )
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Typography variant="body1" color="text.secondary">
              Kein Projekt ausgewählt
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default LeadsPage; 