import React, { useRef, useEffect, useCallback } from 'react';
import {
  Box,
  Avatar,
  List,
  ListItem,
  ListItemButton,
  ListItemAvatar,
  ListItemText,
  Badge,
  Typography,
  CircularProgress,
  Tooltip,
  Stack,
} from '@mui/material';
import AttachmentIcon from '@mui/icons-material/Attachment';
import { EmailListItem } from '../services/api';

export interface EmailListProps {
  emails: EmailListItem[];
  selectedEmailId: number | null;
  onSelectEmail: (id: number | null) => void;
  onLoadMore: () => void;
  hasMore: boolean;
  loadingMore: boolean;
  isCollapsed?: boolean;
  displayMode?: 'simple' | 'detailed';
}

export const EmailList: React.FC<EmailListProps> = ({
  emails,
  selectedEmailId,
  onSelectEmail,
  onLoadMore,
  hasMore,
  loadingMore,
  isCollapsed = false,
  displayMode = 'simple',
}) => {
  const itemRefs = useRef<Map<number, HTMLLIElement | null>>(new Map());
  const listContainerRef = useRef<HTMLUListElement | null>(null);
  const observerSentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (selectedEmailId !== null) {
      const selectedItemRef = itemRefs.current.get(selectedEmailId);
      if (selectedItemRef) {
        // console.log(`[EmailList] Scrolling email ID ${selectedEmailId} into view.`);
        selectedItemRef.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
      }
    }
  }, [selectedEmailId]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const firstEntry = entries[0];
        if (firstEntry.isIntersecting && hasMore && !loadingMore) {
          console.log("[EmailList] Sentinel intersected, calling onLoadMore.");
          onLoadMore();
        }
      },
      {
        // root: listContainerRef.current, // Remove root, observe based on viewport
        threshold: 0.1
      }
    );

    const currentSentinel = observerSentinelRef.current;
    if (currentSentinel) {
      observer.observe(currentSentinel);
    }

    return () => {
      if (currentSentinel) {
        observer.unobserve(currentSentinel);
      }
      observer.disconnect();
    };
  }, [onLoadMore, hasMore, loadingMore]);

  const getInitials = (address: string): string => {
    if (!address) return '?';
    const namePart = address.split('@')[0];
    return namePart.length > 0 ? namePart[0].toUpperCase() : '?';
  };

  const formatTimestamp = useCallback((timestamp: string | null): string => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffInSeconds = (now.getTime() - date.getTime()) / 1000;
    const diffInDays = Math.floor(diffInSeconds / (60 * 60 * 24));

    if (isNaN(date.getTime())) {
      return ''; // Ungültiges Datum
    }

    // Heute: Zeige Uhrzeit (HH:MM)
    if (diffInDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    }
    // Letzte 7 Tage: Zeige Wochentag (z.B. "Mo")
    if (diffInDays < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    }
    // Älter: Zeige Datum (TT.MM.JJ)
    return date.toLocaleDateString([], { day: '2-digit', month: '2-digit', year: 'numeric' });
  }, []);

  const renderDetailedSecondaryText = (email: EmailListItem) => {
    const maxRecipientsToShow = 2;
    const recipients = email.to_addresses || [];
    const displayRecipients = recipients.slice(0, maxRecipientsToShow).join(', ');
    const remainingRecipients = recipients.length > maxRecipientsToShow ? ` +${recipients.length - maxRecipientsToShow}` : '';
    
    return (
      <Stack direction="column" spacing={0.25}>
        <Typography
          component="span"
          variant="body2"
          color="text.primary"
          noWrap
          sx={{ fontWeight: !email.is_read ? 'bold' : 'normal', display: 'block' }}
        >
          {email.subject || '(no subject)'}
        </Typography>
        {recipients.length > 0 && (
            <Tooltip title={recipients.join(', ')} placement="bottom-start">
                <Typography
                  component="span"
                  variant="caption"
                  color="text.secondary"
                  noWrap
                  sx={{ display: 'block' }}
                 >
                    To: {displayRecipients}{remainingRecipients}
                 </Typography>
            </Tooltip>
        )}
        <Typography
          component="span"
          variant="body2"
          color="text.secondary"
          noWrap
          sx={{ display: 'block', fontStyle: 'italic', mt: 0.25 }}
        >
          {email.short_summary || '...'}
        </Typography>
      </Stack>
    );
  };

  return (
    <List
      ref={listContainerRef}
      sx={{
        width: '100%',
        p: 0,
        flexGrow: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
        position: 'relative',
      }}
    >
      {emails.map((email) => (
        <ListItemButton
          component="li"
          key={email.id}
          ref={(el) => { itemRefs.current.set(email.id, el as HTMLLIElement | null); }}
          onClick={() => onSelectEmail(email.id)}
          selected={selectedEmailId === email.id}
          sx={{
            borderBottom: '1px solid',
            borderColor: 'divider',
            py: isCollapsed ? 1 : (displayMode === 'detailed' ? 1.5 : 1),
            px: isCollapsed ? 0 : 2,
            justifyContent: isCollapsed && displayMode === 'simple' ? 'center' : 'flex-start', 
            alignItems: displayMode === 'simple' && !isCollapsed ? 'center' : 'flex-start',
            '&.Mui-selected': {
              bgcolor: 'action.selected',
            },
            '&.Mui-selected:hover': {
              bgcolor: 'action.selected',
            }
          }}
        >
          {/* === SIMPLE MODE RENDERING === */}
          {displayMode === 'simple' && (
            <>
              {/* Only show Avatar/Badge when collapsed in simple mode */}
              {isCollapsed && (
                <ListItemAvatar sx={{ 
                    mt: 0, 
                    minWidth: 'auto',
                    mr: 0 // No margin when collapsed
                   }}>
                  <Badge
                    variant="dot"
                    color="primary"
                    invisible={email.is_read}
                    anchorOrigin={{
                      vertical: 'top',
                      horizontal: 'left',
                    }}
                    sx={{
                      '& .MuiBadge-dot': {
                        border: `2px solid white`,
                      },
                    }}
                  >
                    <Avatar sx={{ bgcolor: 'gray', width: 36, height: 36 }}>
                      {getInitials(email.from_address)}
                    </Avatar>
                  </Badge>
                </ListItemAvatar>
              )}
              {/* Show Text when not collapsed in simple mode */}
              {!isCollapsed && (
                <ListItemText
                  primary={email.from_name || email.from_address.split('@')[1] || email.from_address}
                  secondary={email.short_summary || email.subject}
                  primaryTypographyProps={{
                    variant: 'body2',
                    fontWeight: !email.is_read ? 600 : 400,
                    noWrap: true,
                    color: 'text.primary',
                  }}
                  secondaryTypographyProps={{
                    noWrap: true,
                    variant: 'body2',
                    color: 'text.secondary',
                    mt: 0.5,
                  }}
                />
              )}
            </>
          )}

          {displayMode === 'detailed' && (
            <>
              <ListItemAvatar sx={{
                  mt: 0.5,
                  minWidth: 'auto',
                  mr: isCollapsed ? 0 : 1.5,
                 }}>
                 {!isCollapsed && (
                  <Badge
                    variant="dot"
                    color="primary"
                    invisible={email.is_read}
                    anchorOrigin={{
                      vertical: 'top',
                      horizontal: 'left',
                    }}
                    sx={{
                      '& .MuiBadge-dot': {
                        border: (theme) => `2px solid ${theme.palette.background.paper}`,
                        transform: 'scale(1.1) translate(-30%, -30%)',
                      },
                    }}
                  >
                    <Avatar sx={{ bgcolor: 'primary.light', width: 36, height: 36, fontSize: '1rem' }}>
                      {getInitials(email.from_address)}
                    </Avatar>
                  </Badge>
                 )}
                 {isCollapsed && (
                     <Avatar sx={{ bgcolor: '#5F35AE', width: 36, height: 36, fontSize: '1rem' }}>
                      {getInitials(email.from_address)}
                    </Avatar>
                 )}
              </ListItemAvatar>

              {!isCollapsed && (
                <Box sx={{ flexGrow: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', minWidth: 0 }}>
                  <ListItemText
                    primary={email.from_name || email.from_address.split('@')[0] || email.from_address}
                    secondary={renderDetailedSecondaryText(email)}
                    primaryTypographyProps={{
                      variant: 'body2',
                      fontWeight: !email.is_read ? 'bold' : 'normal',
                      noWrap: true,
                      color: 'text.primary',
                      mb: 0.25,
                    }}
                    secondaryTypographyProps={
                      { component: 'div', variant: 'body2', color: 'text.secondary' }
                    }
                    sx={{ my: 0, mr: 1 }}
                  />
                  <Stack direction="column" spacing={0.5} alignItems="flex-end" sx={{ flexShrink: 0, pt: 0.5 }}>
                      <Typography variant="caption" color="text.secondary" noWrap>
                        {formatTimestamp(email.received_at)}
                      </Typography>
                      {email.has_attachments && email.attachments && email.attachments.length > 0 && (
                        <Tooltip title={email.attachments.map(a => a.filename).join(', ')} placement="bottom-end">
                          <AttachmentIcon sx={{ fontSize: '0.875rem', color: 'text.secondary' }} />
                        </Tooltip>
                      )}
                  </Stack>
                </Box>
              )}
            </>
          )}
        </ListItemButton>
      ))}
      {loadingMore ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
          <CircularProgress size={24} />
        </Box>
      ) : !hasMore && emails.length > 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
          <Typography variant="caption" color="text.secondary">
            End of list
          </Typography>
        </Box>
      ) : null}
      {hasMore && !loadingMore && (
         <Box ref={observerSentinelRef} sx={{ height: '10px', width: '100%' }} />
      )}
    </List>
  );
};

export default EmailList; 