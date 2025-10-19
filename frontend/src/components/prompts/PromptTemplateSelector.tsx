import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  CircularProgress,
  Alert,
  Collapse,
  IconButton,
  SelectChangeEvent,
  Paper,
  Divider
} from '@mui/material';
import {
  ExpandMore,
  ExpandLess,
  Info,
  Visibility
} from '@mui/icons-material';
import { promptsApi } from '../../api/promptsApi';
import { PromptPreview } from './PromptPreview';
import { TemplateVariablesEditor } from './TemplateVariablesEditor';
import { useDebounce } from '../../hooks/useDebounce';
import { QuestionType } from '../../types/prompt';
import type {
  Prompt,
  PromptTemplateSelectorProps
} from '../../types/prompt';

/**
 * PromptTemplateSelector Component
 * 
 * Allows users to select a prompt template for a specific question type.
 * Displays available prompts in a dropdown and shows a preview of the selected prompt.
 */
export const PromptTemplateSelector: React.FC<PromptTemplateSelectorProps> = ({
  questionType,
  selectedPromptId,
  onPromptSelect,
  onVariablesChange,
  autoFilledVariables = {},
  disabled = false,
  showPreview = true
}) => {
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const [livePreviewExpanded, setLivePreviewExpanded] = useState(true);
  const [templateVariables, setTemplateVariables] = useState<string[]>([]);
  const [variableValues, setVariableValues] = useState<Record<string, any>>({});
  const [renderedPreview, setRenderedPreview] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Debounce variable values to avoid too many API calls
  const debouncedVariableValues = useDebounce(variableValues, 800);

  // Fetch prompts for this question type
  const {
    data: prompts = [],
    isLoading,
    error
  } = useQuery<Prompt[]>({
    queryKey: ['prompts', questionType],
    queryFn: () => promptsApi.getPromptsForQuestionType(questionType),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch template variables when prompt is selected
  const {
    data: variablesData,
    isLoading: variablesLoading
  } = useQuery({
    queryKey: ['prompt-variables', selectedPromptId],
    queryFn: () => selectedPromptId ? promptsApi.extractTemplateVariables(selectedPromptId) : null,
    enabled: !!selectedPromptId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Update template variables when data changes
  useEffect(() => {
    if (variablesData?.variables) {
      setTemplateVariables(variablesData.variables);
    } else {
      setTemplateVariables([]);
    }
  }, [variablesData]);

  // Fetch live preview when variable values change (debounced)
  useEffect(() => {
    const fetchLivePreview = async () => {
      // Only fetch if we have a prompt selected and variables
      if (!selectedPromptId || templateVariables.length === 0) {
        setRenderedPreview(null);
        return;
      }

      // Merge auto-filled variables with user-provided variables
      const allVariables = {
        ...autoFilledVariables,
        ...debouncedVariableValues
      };

      // Check if we have values for at least some variables
      const hasValues = Object.keys(allVariables).length > 0;
      if (!hasValues) {
        setRenderedPreview(null);
        return;
      }

      try {
        setPreviewLoading(true);
        setPreviewError(null);

        const response = await promptsApi.renderPromptPreview({
          prompt_id: selectedPromptId,
          variables: allVariables,
          strict: false // Don't require all variables
        });

        setRenderedPreview(response.rendered_content);
      } catch (err) {
        setPreviewError(err instanceof Error ? err.message : 'Fehler beim Rendern der Vorschau');
        setRenderedPreview(null);
      } finally {
        setPreviewLoading(false);
      }
    };

    fetchLivePreview();
  }, [selectedPromptId, debouncedVariableValues, templateVariables, autoFilledVariables]);

  // Auto-select first prompt if none selected and prompts available
  useEffect(() => {
    if (!selectedPromptId && prompts.length > 0 && !disabled) {
      onPromptSelect(prompts[0].id);
    }
  }, [prompts, selectedPromptId, disabled, onPromptSelect]);

  // Handle prompt selection change
  const handlePromptChange = (event: SelectChangeEvent<string>) => {
    const promptId = event.target.value;
    onPromptSelect(promptId === 'none' ? null : promptId);
    // Reset variable values when prompt changes
    setVariableValues({});
    if (onVariablesChange) {
      onVariablesChange({});
    }
  };

  // Handle variable values change
  const handleVariablesChange = (values: Record<string, any>) => {
    setVariableValues(values);
    if (onVariablesChange) {
      onVariablesChange(values);
    }
  };

  // Get question type label
  const getQuestionTypeLabel = (type: QuestionType): string => {
    const labels: Record<QuestionType, string> = {
      [QuestionType.MULTIPLE_CHOICE]: 'Multiple Choice',
      [QuestionType.OPEN_ENDED]: 'Offene Frage',
      [QuestionType.TRUE_FALSE]: 'Richtig/Falsch'
    };
    return labels[type] || type;
  };

  // Loading state
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2 }}>
        <CircularProgress size={20} />
        <Typography variant="body2" color="text.secondary">
          Lade Prompts für {getQuestionTypeLabel(questionType)}...
        </Typography>
      </Box>
    );
  }

  // Error state
  if (error) {
    return (
      <Alert severity="error">
        Fehler beim Laden der Prompts: {(error as Error).message}
      </Alert>
    );
  }

  // No prompts available
  if (prompts.length === 0) {
    return (
      <Alert severity="info" icon={<Info />}>
        Keine Prompts für {getQuestionTypeLabel(questionType)} verfügbar.
        Bitte erstellen Sie zuerst einen Prompt in der Prompt Library.
      </Alert>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Prompt Selection Dropdown */}
      <FormControl fullWidth size="small" disabled={disabled}>
        <InputLabel id={`prompt-select-label-${questionType}`}>
          Prompt-Template für {getQuestionTypeLabel(questionType)}
        </InputLabel>
        <Select
          labelId={`prompt-select-label-${questionType}`}
          id={`prompt-select-${questionType}`}
          value={selectedPromptId || 'none'}
          label={`Prompt-Template für ${getQuestionTypeLabel(questionType)}`}
          onChange={handlePromptChange}
        >
          {/* Default option */}
          <MenuItem value="none">
            <em>Standard-Prompt verwenden</em>
          </MenuItem>

          {/* Available prompts */}
          {prompts.map((prompt: Prompt) => (
            <MenuItem key={prompt.id} value={prompt.id}>
              <Box sx={{ display: 'flex', flexDirection: 'column', py: 0.5 }}>
                <Typography variant="body2">
                  {prompt.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  v{prompt.version} • {prompt.usage_count || 0} Verwendungen
                  {prompt.description && ` • ${prompt.description.substring(0, 50)}${prompt.description.length > 50 ? '...' : ''}`}
                </Typography>
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Template Variables Editor */}
      {selectedPromptId && templateVariables.length > 0 && (
        <Box sx={{ mt: 1 }}>
          <TemplateVariablesEditor
            variables={templateVariables}
            values={variableValues}
            onChange={handleVariablesChange}
            autoFilledVariables={autoFilledVariables}
            loading={variablesLoading}
            compact={true}
            collapsible={true}
            defaultCollapsed={false}
          />
        </Box>
      )}

      {/* Live Preview of Rendered Prompt */}
      {selectedPromptId && templateVariables.length > 0 && renderedPreview && (
        <Paper elevation={1} sx={{ p: 2, mt: 2 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              mb: livePreviewExpanded ? 2 : 0
            }}
            onClick={() => setLivePreviewExpanded(!livePreviewExpanded)}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Visibility fontSize="small" color="primary" />
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Live-Vorschau (gerendert)
              </Typography>
              {previewLoading && <CircularProgress size={16} />}
            </Box>
            <IconButton size="small">
              {livePreviewExpanded ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Box>

          <Collapse in={livePreviewExpanded}>
            {previewError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {previewError}
              </Alert>
            )}

            {renderedPreview && (
              <Box>
                <Divider sx={{ mb: 2 }} />
                <Box
                  sx={{
                    p: 2,
                    bgcolor: 'grey.50',
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'grey.300',
                    maxHeight: 400,
                    overflow: 'auto',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}
                >
                  {renderedPreview}
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Diese Vorschau zeigt den Prompt mit den eingegebenen Variablen.
                </Typography>
              </Box>
            )}
          </Collapse>
        </Paper>
      )}

      {/* Prompt Preview (Collapsible) */}
      {showPreview && selectedPromptId && (
        <Box>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              py: 1,
              '&:hover': {
                bgcolor: 'action.hover'
              }
            }}
            onClick={() => setPreviewExpanded(!previewExpanded)}
          >
            <Typography variant="body2" fontWeight="medium">
              Prompt-Vorschau
            </Typography>
            <IconButton size="small">
              {previewExpanded ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Box>

          <Collapse in={previewExpanded}>
            <Box sx={{ mt: 1 }}>
              <PromptPreview
                promptId={selectedPromptId}
                showMetadata={true}
                showUsageStats={true}
                compact={false}
              />
            </Box>
          </Collapse>
        </Box>
      )}

      {/* Helper Text */}
      {!selectedPromptId && (
        <Typography variant="caption" color="text.secondary">
          Kein Prompt ausgewählt - es wird der Standard-Prompt verwendet.
        </Typography>
      )}
    </Box>
  );
};

export default PromptTemplateSelector;

