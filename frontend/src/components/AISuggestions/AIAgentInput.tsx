import React, { useState, useEffect, useRef, useCallback } from 'react';
import { TextField, Button, Box, CircularProgress } from '@mui/material';
import { useEmailStore } from '../../stores/emailStore'; // Import store to get selectedEmailId

interface DummyActionInputProps {
    isExpanded: boolean;
    onExpandRequest: () => void;
}

const GENERIC_DUMMY_ACTION_KEY = 'mailmind_dummyAction_generic';

export const AIAgentInput: React.FC<DummyActionInputProps> = ({ isExpanded, onExpandRequest }) => {
    const selectedEmailId = useEmailStore((state) => state.selectedEmail?.id ?? null);
    const localStorageKey = selectedEmailId ? `mailmind_dummyAction_${selectedEmailId}` : GENERIC_DUMMY_ACTION_KEY;

    // Initialize state directly from localStorage
    const [dummyText, setDummyText] = useState(() => {
        // console.log(`[DummyActionInput] Initializing state. Key: ${localStorageKey}`);
        const savedText = localStorage.getItem(localStorageKey);
        // console.log(`[DummyActionInput] Initial load from localStorage: '${savedText}'`);
        return savedText !== null ? savedText : "";
    });

    // Ref to track if the key has changed, to re-trigger initial load if needed
    const previousKeyRef = useRef(localStorageKey);

    // Effect to re-initialize state if localStorageKey changes (e.g., email selection changes)
    useEffect(() => {
        if (localStorageKey !== previousKeyRef.current) {
            // console.log(`[DummyActionInput] localStorageKey changed from ${previousKeyRef.current} to ${localStorageKey}. Re-initializing state.`);
            const savedText = localStorage.getItem(localStorageKey);
            // console.log(`[DummyActionInput] Re-load from localStorage: '${savedText}'`);
            setDummyText(savedText !== null ? savedText : "");
            previousKeyRef.current = localStorageKey;
        }
    }, [localStorageKey]);

    // Effect for SAVING to localStorage (runs when dummyText or localStorageKey changes)
    useEffect(() => {
        // console.log(`[DummyActionInput] SAVE EFFECT. Key: ${localStorageKey}, Value: '${dummyText}'`);
        localStorage.setItem(localStorageKey, dummyText);
    }, [dummyText, localStorageKey]);

    const handleDummyChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        // console.log("[DummyActionInput] handleDummyChange. New value:", event.target.value);
        setDummyText(event.target.value);
    };

    const handleDummyClick = () => {
        console.log("Dummy action triggered with text:", dummyText);
        // Optional: Clear localStorage after action?
        // localStorage.removeItem(localStorageKey);
        // setDummyText(""); // Clear input after action
    };

    const handleDummyKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            event.preventDefault();
            handleDummyClick();
        }
    };

    // console.log(`[DummyActionInput] Rendering with dummyText: '${dummyText}'`); // Log current render value

    return (
        <Box
            sx={{
                mt: 'auto', // Pushes to bottom if parent is flex column
                display: 'flex',
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                position: 'relative',
            }}
        >
            <TextField
                fullWidth
                multiline
                minRows={3}
                maxRows={8}
                placeholder="what do you want to do?"
                variant="outlined"
                value={dummyText}
                onClick={(e) => {
                    e.stopPropagation();
                    if (!isExpanded) {
                        onExpandRequest();
                    }
                }}
                onChange={handleDummyChange}
                onKeyDown={handleDummyKeyDown}
                sx={{
                    maxHeight: '30vh',
                    overflow: 'auto',
                    '& .MuiInputBase-root': { alignItems: 'flex-start', p: 1.5 },
                    '& textarea': { overflow: 'auto !important' }
                }}
            />
            <Button
                size="small"
                variant="outlined"
                onClick={handleDummyClick}
                disabled={dummyText.trim() === ''}
                sx={{
                    position: 'absolute',
                    bottom: 8,
                    right: 8,
                    minWidth: 0,
                    padding: '2px 6px',
                    color: 'grey.400',
                    borderColor: 'grey.700',
                    '&:hover': {
                        backgroundColor: 'rgba(255, 255, 255, 0.08)',
                        borderColor: 'grey.600',
                    }
                }}
            >
                do it
            </Button>
        </Box>
    );
}; 