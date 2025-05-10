import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
    AISuggestion,
    correctSuggestionField,
    isCorrectedSnippetResponse,
    updateAiSuggestion,
    refineTextDirectly,
} from '../services/api';
import { CorrectingState } from './types';

export const useAISuggestionHandlers = (
    suggestions: AISuggestion[],
    selectedEmailId: number | null,
    selectedSuggestionIndex: number | null,
    draftSubject: string,
    draftBody: string,
    onDraftSubjectChange: (newSubject: string) => void,
    onDraftBodyChange: (newBody: string) => void,
    isExpanded: boolean,
    onExpandRequest: () => void,
    onUpdateSuggestion: (id: string, data: Partial<Pick<AISuggestion, 'content' | 'suggested_subject'>>) => Promise<void>,
    subjectInputRef: React.RefObject<HTMLInputElement | HTMLTextAreaElement | null>,
    bodyTextareaRef: React.RefObject<HTMLInputElement | HTMLTextAreaElement | null>
) => {
    
    const [correctingStates, setCorrectingStates] = useState<CorrectingState>({});
    const [correctionError, setCorrectionError] = useState<string | null>(null);
    const [isRefining, setIsRefining] = useState<boolean>(false);
    const [refineError, setRefineError] = useState<string | null>(null);
    
    // Initialize internalCustomPrompt directly from localStorage
    const [internalCustomPrompt, setInternalCustomPrompt] = useState<string>(() => {
        if (selectedEmailId !== null) {
            const key = `mailmind_customPrompt_${selectedEmailId}`;
            const savedPrompt = localStorage.getItem(key);
            console.log(`[Hook] Initializing internalCustomPrompt for key ${key}. Found:`, savedPrompt);
            return savedPrompt !== null ? savedPrompt : "";
        }
        console.log("[Hook] Initializing internalCustomPrompt without selectedEmailId.");
        return ""; // Default if no selectedEmailId at mount
    }); 

    // Ref to track if the key has changed, to re-trigger initial load if needed
    const previousKeyRef = useRef(selectedEmailId ? `mailmind_customPrompt_${selectedEmailId}` : null);

    // Effect to re-initialize internalCustomPrompt if selectedEmailId changes
    useEffect(() => {
        const currentKey = selectedEmailId ? `mailmind_customPrompt_${selectedEmailId}` : null;
        if (currentKey !== previousKeyRef.current) {
            console.log(`[Hook] selectedEmailId (key for customPrompt) changed from ${previousKeyRef.current} to ${currentKey}. Re-initializing internalCustomPrompt.`);
            if (selectedEmailId !== null) {
                const savedPrompt = localStorage.getItem(currentKey!);
                console.log(`[Hook] Re-load internalCustomPrompt: '${savedPrompt}' for key ${currentKey}`);
                setInternalCustomPrompt(savedPrompt !== null ? savedPrompt : "");
            } else {
                setInternalCustomPrompt("");
            }
            previousKeyRef.current = currentKey;
        }
    }, [selectedEmailId]);

    // Effect for SAVING internalCustomPrompt to localStorage
    useEffect(() => {
        if (selectedEmailId !== null) {
            const key = `mailmind_customPrompt_${selectedEmailId}`;
            console.log(`[Hook] Saving internalCustomPrompt for key ${key}: '${internalCustomPrompt}'`);
            localStorage.setItem(key, internalCustomPrompt || ""); // Save even if empty string
        }
    }, [internalCustomPrompt, selectedEmailId]);

    // Wrapper for setCustomPrompt (used by ReplyView)
    const setCustomPromptWrapper = useCallback((value: React.SetStateAction<string>) => {
        const newValue = typeof value === 'function' ? value(internalCustomPrompt) : value;
        setInternalCustomPrompt(newValue);
    }, [internalCustomPrompt]);

    // Refs for debounce timers
    const contentDebounceTimerRef = useRef<number | null>(null);
    const subjectDebounceTimerRef = useRef<number | null>(null);

    // Cleanup timers on unmount or when selection changes
    useEffect(() => {
        return () => {
            if (contentDebounceTimerRef.current) clearTimeout(contentDebounceTimerRef.current);
            if (subjectDebounceTimerRef.current) clearTimeout(subjectDebounceTimerRef.current);
        };
    }, []); // Run only on mount/unmount

    useEffect(() => {
        // Clear timers when selected email changes and we reset selection
        if (contentDebounceTimerRef.current) clearTimeout(contentDebounceTimerRef.current);
        if (subjectDebounceTimerRef.current) clearTimeout(subjectDebounceTimerRef.current);
        // No longer resets text/index here
    }, [selectedEmailId, selectedSuggestionIndex]);

    // Debounced update logic
    const debounceUpdateBackend = useCallback((
        field: 'content' | 'suggested_subject',
        newValue: string,
        timerRef: React.MutableRefObject<number | null>
    ) => {
        if (timerRef.current) {
            clearTimeout(timerRef.current);
        }

        timerRef.current = window.setTimeout(() => {
            if (selectedSuggestionIndex !== null) {
                const originalSuggestion = suggestions[selectedSuggestionIndex];
                if (originalSuggestion) {
                    const originalValue = field === 'content'
                        ? originalSuggestion.content
                        : (originalSuggestion.suggested_subject || 'Suggested Reply');

                    if (newValue !== originalValue) {
                        console.log(`[AISuggestions Hook] Debounced BACKEND update for suggestion ${originalSuggestion.id}, field: ${field}`);
                        onUpdateSuggestion(originalSuggestion.id, { [field]: newValue })
                            .catch(err => {
                                console.error(`[AISuggestions Hook] Error during debounced BACKEND update for ${field}:`, err);
                            });
                    } else {
                        console.log(`[AISuggestions Hook] Debounced BACKEND update skipped for ${field}, value unchanged from original.`);
                    }
                }
            }
        }, 1000); // 1 second delay
    }, [selectedSuggestionIndex, suggestions, onUpdateSuggestion]);

    // Input Change Handlers
    const handleEditChange = useCallback((event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const newValue = event.target.value;
        onDraftBodyChange(newValue);
        debounceUpdateBackend('content', newValue, contentDebounceTimerRef);
    }, [onDraftBodyChange, debounceUpdateBackend]);

    const handleSubjectChange = useCallback((event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const newValue = event.target.value;
        onDraftSubjectChange(newValue);
        debounceUpdateBackend('suggested_subject', newValue, subjectDebounceTimerRef);
    }, [onDraftSubjectChange, debounceUpdateBackend]);

    // Correct Button Handler
    const handleCorrectClick = useCallback(async (
        // Field to correct is determined by focus
        field_to_correct: 'subject' | 'body', 
        selectedText?: string,
        selectionStart?: number,
        selectionEnd?: number
    ) => {
        if (!selectedEmailId) {
            console.warn("[AISuggestions Hook] Correct click without selectedEmailId.");
            setCorrectionError("Cannot correct: No email selected.");
            return;
        }

        const uniqueCorrectionKey = `direct_${selectedEmailId}_${field_to_correct}`;

        if (correctingStates[uniqueCorrectionKey]?.[field_to_correct]) return; // Bereits in Korrektur

        setCorrectingStates(prev => ({ 
            ...prev, 
            [uniqueCorrectionKey]: { ...prev[uniqueCorrectionKey], [field_to_correct]: true } 
        }));
        setCorrectionError(null);

        // Clear debounce timers
        if (contentDebounceTimerRef.current) clearTimeout(contentDebounceTimerRef.current);
        if (subjectDebounceTimerRef.current) clearTimeout(subjectDebounceTimerRef.current);
        
        try {
            const currentSubject = draftSubject;
            const currentBody = draftBody;

            // Fall 1: Volltextkorrektur (wenn kein Text markiert ist)
            if (!selectedText) {
                console.log(`[AISuggestions Hook] Correcting FULL field via refineTextDirectly: ${field_to_correct}`);
                
                const result = await refineTextDirectly(
                        "", // Kein custom_prompt für reine Korrektur
                        field_to_correct === 'subject' ? currentSubject : currentSubject, // Immer aktuellen Subject mitgeben für Kontext?
                        field_to_correct === 'body' ? currentBody : currentBody,     // Immer aktuellen Body mitgeben für Kontext?
                        true // Flag für reine Korrektur
                      );

                if (result && result.refined_subject !== undefined && result.refined_body !== undefined) {
                    if (field_to_correct === 'subject') {
                        onDraftSubjectChange(result.refined_subject || "");
                        console.log(`[AISuggestions Hook] Full Subject corrected via Direct API. Draft updated.`);
                    } else { // field_to_correct === 'body'
                        onDraftBodyChange(result.refined_body);
                        console.log(`[AISuggestions Hook] Full Body corrected via Direct API. Draft updated.`);
                    }
                } else {
                     console.warn(`[AISuggestions Hook] Direct Correction for full ${field_to_correct} did not return expected result.`);
                     setCorrectionError("Correction did not return expected result.");
                }
            } 
            // Fall 2: Snippet korrigieren (wenn Text markiert ist)
            else if (selectedText && selectionStart !== undefined && selectionEnd !== undefined) {
                console.log(`[AISuggestions Hook] Correcting SNIPPET in field: ${field_to_correct} via refineTextDirectly (using different prompt internally)`);
                
                // HINWEIS: Aktuell KANN refineTextDirectly KEINE Snippets. 
                // Wir MÜSSTEN DAFÜR eine neue API-Funktion/Endpoint oder Anpassung haben.
                // Temporär: Wir loggen eine Warnung und machen nichts.
                // TODO: Implement snippet correction via direct text API if needed.
                console.warn("[AISuggestions Hook] Snippet correction for draft text is not yet implemented via direct API.");
                setCorrectionError("Snippet correction for manually entered text is not supported yet.");

                // --- Auskommentierte Logik für potentielle Snippet-Korrektur über Direct API ---
                /*
                const result = await refineTextDirectly(
                    "", // Spezieller Prompt oder Flag für Snippet-Korrektur?
                    field_to_correct === 'subject' ? currentSubject : currentSubject, // Kontext
                    field_to_correct === 'body' ? currentBody : currentBody, // Kontext
                    true, // Korrektur
                    selectedText // Das zu korrigierende Snippet
                );
                // Verarbeitung des Ergebnisses (bräuchte angepasste API-Antwort)
                */
               // --- Ende auskommentierte Logik ---
                
            }

        } catch (error: any) {
            console.error("[AISuggestions Hook] Error during direct correction:", error);
            setCorrectionError(error?.response?.data?.detail || error.message || "Correction failed.");
        } finally {
            setCorrectingStates(prev => ({ 
                ...prev, 
                [uniqueCorrectionKey]: { ...prev[uniqueCorrectionKey], [field_to_correct]: false } 
            }));
        }
    }, [
        selectedEmailId, draftSubject, draftBody, correctingStates, 
        onDraftSubjectChange, onDraftBodyChange,
        subjectInputRef, bodyTextareaRef // Entferne Suggestion-bezogene Abhängigkeiten
    ]);

    // Refine Button Handler
    const handleRefineClick = useCallback(async () => {
        console.log("[AISuggestions Hook] Refine button clicked (direct text refine).");
        if (selectedEmailId === null) {
            console.warn("[AISuggestions Hook] Refine attempted without selected email ID.");
            setRefineError("Cannot refine: No email selected.");
            return;
        }

        if (internalCustomPrompt.trim() === "") {
            console.warn("[AISuggestions Hook] Refine attempted with empty prompt.");
            setRefineError("Cannot refine: Custom instructions are empty.");
            return;
        }

        setIsRefining(true);
        setRefineError(null); // Reset previous error

        try {
            console.log(`[AISuggestions Hook] Calling refineTextDirectly.`);
            const refinedResult = await refineTextDirectly(
                internalCustomPrompt,
                draftSubject,
                draftBody
            );

            console.log("[AISuggestions Hook] refineTextDirectly successful, response:", refinedResult);

            if (refinedResult && refinedResult.refined_body !== undefined && refinedResult.refined_subject !== undefined) {
                onDraftSubjectChange(refinedResult.refined_subject);
                onDraftBodyChange(refinedResult.refined_body);
                setInternalCustomPrompt(""); // Clear the prompt on success
            } else {
                console.error("[AISuggestions Hook] Refined text data is incomplete:", refinedResult);
                setRefineError("Failed to get complete refinement from server.");
            }

        } catch (error) {
            console.error("[AISuggestions Hook] Error during refineTextDirectly:", error);
            setRefineError("An error occurred while refining the text. Please try again.");
        } finally {
            setIsRefining(false);
        }
    }, [
        selectedEmailId,
        internalCustomPrompt,
        draftSubject,
        draftBody,
        onDraftSubjectChange,
        onDraftBodyChange,
        setInternalCustomPrompt,
    ]);

    return {
        correctingStates,
        correctionError,
        isRefining,
        handleCorrectClick,
        handleRefineClick,
        customPrompt: internalCustomPrompt,
        setCustomPrompt: setCustomPromptWrapper,
        refineError,
        setRefineError,
        handleEditChange,
        handleSubjectChange,
    };
}; 