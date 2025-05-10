import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemText,
  Typography,
  IconButton,
  CircularProgress,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { fetchEmails, toggleEmailFlag, EmailListItem, PaginatedResponse } from '../services/api';
import { useInView } from 'react-intersection-observer';

interface EmailListProps {
  onSelectEmail: (id: number | null) => void;
  selectedEmailId: number | null;
}

const EmailList: React.FC<EmailListProps> = ({ onSelectEmail, selectedEmailId }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const queryClient = useQueryClient();
  const [currentFolder, setCurrentFolder] = useState<string>('INBOX');

  const { ref, inView } = useInView({
    threshold: 0,
    triggerOnce: false,
  });

  const {
    data,
    error,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
    status,
  } = useInfiniteQuery<PaginatedResponse<EmailListItem>, Error>({
    queryKey: ['emails'],
    queryFn: ({ pageParam = 0 }) => fetchEmails({ offset: pageParam as number, limit: 20, folderName: 'INBOX' }),
    getNextPageParam: (lastPage, allPages) => {
      if (lastPage.next) {
        const currentOffset = allPages.flatMap(page => page.results).length;
        return currentOffset;
      }
      return undefined;
    },
    initialPageParam: 0,
  });

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const toggleFlagMutation = useMutation({ 
    mutationFn: toggleEmailFlag, 
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] }); 
    },
  });

  // Effect to select the first email on initial load
  useEffect(() => {
    // Check if data is loaded, not fetching, no email selected yet, and there are emails
    if (status === 'success' && !isFetching && selectedEmailId === null && data?.pages[0]?.results?.length > 0) {
      const firstEmailId = data.pages[0].results[0].id;
      if (firstEmailId) {
        onSelectEmail(firstEmailId);
      }
    }
    // Run this effect when data/status changes, or when selectedEmailId becomes null
  }, [status, data, isFetching, selectedEmailId, onSelectEmail]);

  const allEmails = data?.pages.flatMap(page => page.results) ?? [];
  const filteredEmails = allEmails.filter((email: EmailListItem) => 
    (email.subject?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
    (email.from_address?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
    (email.from_name?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
    (email.body_text?.toLowerCase() || '').includes(searchTerm.toLowerCase())
  );

  const handleEmailClick = (emailId: number) => {
    onSelectEmail(emailId);
  };

  const handleToggleFlag = (e: React.MouseEvent, emailId: number) => {
    e.stopPropagation();
    toggleFlagMutation.mutate(emailId);
  };

  if (status === 'pending') {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" sx={{ p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (status === 'error') {
    return (
      <Box p={3}>
        <Typography color="error">
          Error loading emails: {error.message}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ p: 1, borderBottom: '1px solid', borderColor: 'divider', flexShrink: 0 }}>
        <TextField
          fullWidth
          size="small"
          variant="outlined"
          placeholder="Search loaded emails..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        <List disablePadding>
          {filteredEmails.length === 0 && !isFetching && (
            <ListItem>
              <ListItemText primary="No emails found." />
            </ListItem>
          )}
          {filteredEmails.map((email: EmailListItem, index) => {
            const isLastElement = index === filteredEmails.length - 1;
            return (
              <ListItem
                ref={isLastElement ? ref : null}
                key={email.id}
                button
                selected={selectedEmailId === email.id}
                onClick={() => handleEmailClick(email.id)}
                sx={{ 
                  '&.Mui-selected': {
                    backgroundColor: 'action.selected',
                  },
                  '&.Mui-selected:hover': {
                    backgroundColor: 'action.selected',
                  },
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                }}
                disablePadding
              >
                <Box sx={{ p: 1.5, display: 'flex', width: '100%', alignItems: 'flex-start' }}>
                  <IconButton
                    size="small"
                    onClick={(e) => handleToggleFlag(e, email.id)}
                    sx={{ mr: 1, mt: -0.5 }}
                  >
                    {email.is_flagged ? (
                      <StarIcon color="primary" fontSize="small" />
                    ) : (
                      <StarBorderIcon fontSize="small" />
                    )}
                  </IconButton>
                  <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                      <Typography
                        variant="body2"
                        noWrap
                        color="primary.main"
                        sx={{ fontWeight: email.is_read ? 'normal' : 'bold', mr: 1 }}
                      >
                        {email.from_name || email.from_address}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" noWrap>
                        {format(new Date(email.sent_at), 'MMM d')}
                      </Typography>
                    </Box>
                    <Typography
                      variant="body2"
                      noWrap
                      color="primary.main"
                      sx={{ fontWeight: email.is_read ? 'normal' : 'bold', mb: 0.5 }}
                    >
                      {email.subject}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.primary"
                      noWrap
                      sx={{ display: 'block' }}
                    >
                      {email.body_text?.substring(0, 100)}
                    </Typography>
                  </Box>
                </Box>
              </ListItem>
            );
          })}
        </List>
        {isFetchingNextPage && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        {!hasNextPage && !isFetching && allEmails.length > 0 && (
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="caption" color="text.secondary">End of list</Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default EmailList; 