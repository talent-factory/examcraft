import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Typography,
  Paper,
  Alert,
  CircularProgress,
  Collapse,
  IconButton,
  Chip,
  Stack,
  Tooltip
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Info as InfoIcon
} from '@mui/icons-material';

export interface TemplateVariablesEditorProps {
  /**
   * List of variable names extracted from the prompt template
   */
  variables: string[];

  /**
   * Current variable values
   */
  values: Record<string, any>;

  /**
   * Callback when variable values change
   */
  onChange: (values: Record<string, any>) => void;

  /**
   * Variables that are automatically filled from the form
   * These will be hidden from the editor
   */
  autoFilledVariables?: Record<string, any>;

  /**
   * Whether the editor is in loading state
   */
  loading?: boolean;

  /**
   * Error message to display
   */
  error?: string;

  /**
   * Whether to show the editor in compact mode
   */
  compact?: boolean;

  /**
   * Whether the editor is collapsible
   */
  collapsible?: boolean;

  /**
   * Initial collapsed state (only if collapsible=true)
   */
  defaultCollapsed?: boolean;
}

/**
 * TemplateVariablesEditor Component
 * 
 * Provides dynamic input fields for template variables with validation.
 * Supports auto-detection of variable types and provides helpful placeholders.
 */
export const TemplateVariablesEditor: React.FC<TemplateVariablesEditorProps> = ({
  variables,
  values,
  onChange,
  autoFilledVariables = {},
  loading = false,
  error,
  compact = false,
  collapsible = false,
  defaultCollapsed = false
}) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [localValues, setLocalValues] = useState<Record<string, any>>(values);

  // Filter out auto-filled variables from the list
  const editableVariables = variables.filter(
    varName => !Object.keys(autoFilledVariables).includes(varName)
  );

  // Sync local values with prop values
  useEffect(() => {
    setLocalValues(values);
  }, [values]);

  // Handle value change for a specific variable
  const handleValueChange = (variableName: string, value: any) => {
    const newValues = {
      ...localValues,
      [variableName]: value
    };
    setLocalValues(newValues);
    onChange(newValues);
  };

  // Infer variable type from name
  const inferVariableType = (name: string): 'number' | 'text' => {
    const numberKeywords = ['count', 'number', 'num', 'amount', 'quantity', 'limit', 'max', 'min'];
    const lowerName = name.toLowerCase();
    
    if (numberKeywords.some(keyword => lowerName.includes(keyword))) {
      return 'number';
    }
    
    return 'text';
  };

  // Get placeholder text for a variable
  const getPlaceholder = (name: string): string => {
    const placeholders: Record<string, string> = {
      'context': 'Document context will be inserted here',
      'topic': 'e.g., Python Programming',
      'difficulty': 'easy, medium, or hard',
      'language': 'de or en',
      'count': 'e.g., 5',
      'question_count': 'e.g., 10',
      'bloom_level': '1-6',
      'question_type': 'multiple_choice, open_ended, true_false'
    };
    
    return placeholders[name.toLowerCase()] || `Enter ${name}`;
  };

  // Get helper text for a variable
  const getHelperText = (name: string): string | undefined => {
    const helpers: Record<string, string> = {
      'context': 'Automatically filled from selected documents',
      'difficulty': 'Choose: easy, medium, or hard',
      'language': 'Choose: de (Deutsch) or en (English)',
      'bloom_level': 'Bloom\'s Taxonomy level (1=Remember, 6=Create)'
    };
    
    return helpers[name.toLowerCase()];
  };

  // Check if variable is auto-filled (shouldn't be edited by user)
  const isAutoFilled = (name: string): boolean => {
    return Object.keys(autoFilledVariables).includes(name);
  };

  // Don't show editor if all variables are auto-filled
  if (editableVariables.length === 0) {
    return null;
  }

  const content = (
    <Box>
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
          <CircularProgress size={24} />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!loading && (
        <Stack spacing={2}>
          {editableVariables.map((variableName) => {
            const type = inferVariableType(variableName);
            const placeholder = getPlaceholder(variableName);
            const helperText = getHelperText(variableName);
            const currentValue = localValues[variableName] ?? '';

            return (
              <Box key={variableName}>
                <TextField
                  fullWidth
                  label={variableName}
                  type={type}
                  value={currentValue}
                  onChange={(e) => handleValueChange(variableName, e.target.value)}
                  placeholder={placeholder}
                  helperText={helperText}
                  disabled={loading}
                  size={compact ? 'small' : 'medium'}
                />
              </Box>
            );
          })}
        </Stack>
      )}
    </Box>
  );

  if (!collapsible) {
    return (
      <Paper elevation={1} sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
          Zusätzliche Template-Variablen
        </Typography>
        {content}
      </Paper>
    );
  }

  return (
    <Paper elevation={1} sx={{ p: 2 }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer'
        }}
        onClick={() => setCollapsed(!collapsed)}
      >
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
          Zusätzliche Template-Variablen ({editableVariables.length})
        </Typography>
        <IconButton size="small">
          {collapsed ? <ExpandMoreIcon /> : <ExpandLessIcon />}
        </IconButton>
      </Box>

      <Collapse in={!collapsed}>
        <Box sx={{ mt: 2 }}>
          {content}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default TemplateVariablesEditor;

