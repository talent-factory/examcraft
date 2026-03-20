import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Grid,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  SelectChangeEvent,
  Switch,
  FormControlLabel
} from '@mui/material';
import { Save, Cancel, Preview, Code, History } from '@mui/icons-material';
import { promptsApi, Prompt } from '../../api/promptsApi';
import { PromptCategory } from '../../types/prompt';
import MarkdownRenderer from '../MarkdownRenderer';

// Use Case Labels für UI — values must match the stored format (question_generation_<type>)
const USE_CASE_LABELS: Record<string, string> = {
  'question_generation': 'Fragengenerierung (allgemein)',
  'question_generation_multiple_choice': 'Multiple Choice',
  'question_generation_open_ended': 'Offene Frage',
  'question_generation_true_false': 'Wahr/Falsch',
  'chatbot': 'Chatbot',
  'evaluation': 'Bewertung',
};

interface PromptEditorProps {
  promptId?: string;
  initialData?: Partial<Prompt>;
  onSave?: () => void;
  onCancel?: () => void;
}

export const PromptEditor: React.FC<PromptEditorProps> = ({
  promptId,
  initialData,
  onSave,
  onCancel
}) => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [tagInput, setTagInput] = useState('');

  const [formData, setFormData] = useState<Partial<Prompt>>({
    name: '',
    content: '',
    description: '',
    category: PromptCategory.SYSTEM_PROMPT,
    use_case: '',
    tags: [],
    is_active: false
  });

  const loadPrompt = useCallback(async () => {
    if (!promptId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await promptsApi.getPrompt(promptId);
      setFormData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden des Prompts');
    } finally {
      setLoading(false);
    }
  }, [promptId]);

  useEffect(() => {
    if (promptId) {
      loadPrompt();
    }
  }, [promptId, loadPrompt]);

  useEffect(() => {
    if (!promptId && initialData) {
      setFormData(prev => ({ ...prev, ...initialData }));
    }
  }, [promptId, initialData]);

  const handleSave = async () => {
    if (!formData.name || !formData.content || !formData.category) {
      setError('Name, Content und Category sind Pflichtfelder');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      if (promptId) {
        const result = await promptsApi.updatePrompt(promptId, formData);
        const versionBumped = result.version > (formData.version ?? 1);
        setFormData(result);
        setSuccess(versionBumped
          ? `Neue Version v${result.version} erstellt`
          : 'Prompt erfolgreich aktualisiert'
        );
      } else {
        // Type assertion after validation
        const newPrompt = {
          name: formData.name,
          content: formData.content,
          category: formData.category,
          use_case: formData.use_case,
          description: formData.description,
          tags: formData.tags || [],
          is_active: formData.is_active ?? false
        } as Omit<Prompt, 'id' | 'version' | 'created_at' | 'updated_at' | 'usage_count'>;

        await promptsApi.createPrompt(newPrompt);
        setSuccess('Prompt erfolgreich erstellt');
      }

      setTimeout(() => {
        onSave?.();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern');
    } finally {
      setSaving(false);
    }
  };

  const addTag = () => {
    if (tagInput && !formData.tags?.includes(tagInput)) {
      setFormData({
        ...formData,
        tags: [...(formData.tags || []), tagInput]
      });
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setFormData({
      ...formData,
      tags: formData.tags?.filter(t => t !== tag)
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1">
          {promptId ? 'Prompt bearbeiten' : 'Neuer Prompt'}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Cancel />}
            onClick={onCancel}
            disabled={saving}
          >
            Abbrechen
          </Button>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <Save />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Speichern...' : 'Speichern'}
          </Button>
        </Box>
      </Box>

      {/* Success/Error Messages */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Main Editor */}
        <Grid item xs={12} lg={8}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Prompt Details
            </Typography>

            {/* Name */}
            <TextField
              fullWidth
              label="Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="z.B. system_prompt_question_generation"
              sx={{ mb: 3 }}
              required
            />

            {/* Description */}
            <TextField
              fullWidth
              label="Beschreibung"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Kurze Beschreibung des Prompts"
              sx={{ mb: 3 }}
            />

            {/* Content Editor with Tabs */}
            <Box sx={{ mb: 3 }}>
              <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
                <Tab icon={<Code />} label="Bearbeiten" />
                <Tab icon={<Preview />} label="Vorschau" />
              </Tabs>

              <Box sx={{ mt: 2 }}>
                {activeTab === 0 ? (
                  <TextField
                    fullWidth
                    multiline
                    rows={16}
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    placeholder="Prompt Content (unterstützt {variable} Syntax)"
                    sx={{
                      '& textarea': {
                        fontFamily: 'monospace',
                        fontSize: '0.9rem'
                      }
                    }}
                    required
                  />
                ) : (
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 3,
                      minHeight: 400,
                      bgcolor: 'grey.50',
                      overflow: 'auto'
                    }}
                  >
                    {formData.content ? (
                      <MarkdownRenderer content={formData.content} />
                    ) : (
                      <Typography color="text.secondary" fontStyle="italic">
                        Keine Inhalte
                      </Typography>
                    )}
                  </Paper>
                )}
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} lg={4}>
          {/* Kategorisierung */}
          <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Kategorisierung
            </Typography>

            {/* Category */}
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Kategorie</InputLabel>
              <Select
                value={formData.category}
                label="Kategorie"
                onChange={(e: SelectChangeEvent) =>
                  setFormData({ ...formData, category: e.target.value as any })
                }
              >
                <MenuItem value="system_prompt">System Prompt</MenuItem>
                <MenuItem value="user_prompt">User Prompt</MenuItem>
                <MenuItem value="few_shot_example">Few-Shot Example</MenuItem>
                <MenuItem value="template">Template</MenuItem>
              </Select>
            </FormControl>

            {/* Use Case - Fragetyp Dropdown */}
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel id="use-case-label">Use Case (Fragetyp)</InputLabel>
              <Select
                labelId="use-case-label"
                id="use-case-select"
                value={formData.use_case || ''}
                label="Use Case (Fragetyp)"
                onChange={(e: SelectChangeEvent) =>
                  setFormData({ ...formData, use_case: e.target.value })
                }
              >
                <MenuItem value="">
                  <em>Kein spezifischer Use Case</em>
                </MenuItem>
                {Object.entries(USE_CASE_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Tags */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Tags
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <TextField
                  size="small"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Neuer Tag"
                  sx={{ flexGrow: 1 }}
                />
                <Button onClick={addTag} variant="outlined" size="small">
                  +
                </Button>
              </Box>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {formData.tags?.map(tag => (
                  <Chip
                    key={tag}
                    label={tag}
                    onDelete={() => removeTag(tag)}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Box>
            </Box>

            {/* Active Toggle */}
            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
              }
              label="Aktiv"
            />
          </Paper>

          {/* Version History (only for existing prompts) */}
          {promptId && (
            <Paper elevation={2} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                <History sx={{ verticalAlign: 'middle', mr: 1 }} />
                Version History
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Aktuelle Version: v{formData.version}
              </Typography>
              <Button
                variant="outlined"
                fullWidth
                onClick={() => console.log('Show versions', promptId)}
              >
                Versionen anzeigen
              </Button>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Container>
  );
};
