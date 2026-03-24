import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
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
import axios from 'axios';
import { promptsApi, Prompt } from '../../api/promptsApi';
import { PromptCategory } from '../../types/prompt';
import MarkdownRenderer from '../MarkdownRenderer';

/** Extract a user-friendly error message from Axios/FastAPI errors. */
function extractErrorMessage(
  err: unknown,
  fallback: string,
  labels: { validationError: string; fieldDefault: string; invalidDefault: string }
): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (err.response?.status === 422 && detail) {
      const details = Array.isArray(detail) ? detail : [detail];
      const messages = details.map((d: unknown) => {
        if (typeof d === 'object' && d !== null && 'msg' in d) {
          const entry = d as { loc?: unknown; msg?: unknown; message?: unknown };
          const field = (Array.isArray(entry.loc) ? entry.loc.slice(1).join('.') : '') || labels.fieldDefault;
          const msg = String(entry.msg || entry.message || labels.invalidDefault);
          return `${field}: ${msg}`;
        }
        return String(d);
      });
      return `${labels.validationError}: ${messages.join(', ')}`;
    }
    if (detail) {
      return String(detail);
    }
  }
  return err instanceof Error ? err.message : fallback;
}

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
  const { t } = useTranslation();

  const USE_CASE_LABELS: Record<string, string> = {
    'question_generation': t('admin.promptEditor.useCaseGeneral'),
    'question_generation_multiple_choice': t('admin.promptEditor.useCaseMultipleChoice'),
    'question_generation_open_ended': t('admin.promptEditor.useCaseOpenEnded'),
    'question_generation_true_false': t('admin.promptEditor.useCaseTrueFalse'),
    'chatbot': t('admin.promptEditor.useCaseChatbot'),
    'evaluation': t('admin.promptEditor.useCaseEvaluation'),
  };

  const errorLabels = {
    validationError: t('admin.promptEditor.validationError'),
    fieldDefault: t('admin.promptEditor.fieldDefault'),
    invalidDefault: t('admin.promptEditor.invalidDefault'),
  };

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
    } catch (err: unknown) {
      setError(extractErrorMessage(err, t('admin.promptEditor.failedLoad'), errorLabels));
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
      setError(t('admin.promptEditor.validationRequired'));
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
          ? t('admin.promptEditor.successVersionCreated', { version: result.version })
          : t('admin.promptEditor.successUpdated')
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
        setSuccess(t('admin.promptEditor.successCreated'));
      }

      setTimeout(() => {
        onSave?.();
      }, 1500);
    } catch (err: unknown) {
      setError(extractErrorMessage(err, t('admin.promptEditor.failedSave'), errorLabels));
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
          {promptId ? t('admin.promptEditor.titleEdit') : t('admin.promptEditor.titleCreate')}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Cancel />}
            onClick={onCancel}
            disabled={saving}
          >
            {t('admin.promptEditor.btnCancel')}
          </Button>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <Save />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? t('admin.promptEditor.btnSaving') : t('admin.promptEditor.btnSave')}
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
              {t('admin.promptEditor.sectionDetails')}
            </Typography>

            {/* Name */}
            <TextField
              fullWidth
              label={t('admin.promptEditor.fieldName')}
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder={t('admin.promptEditor.fieldNamePlaceholder')}
              sx={{ mb: 3 }}
              required
            />

            {/* Description */}
            <TextField
              fullWidth
              label={t('admin.promptEditor.fieldDescription')}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder={t('admin.promptEditor.fieldDescriptionPlaceholder')}
              sx={{ mb: 3 }}
            />

            {/* Content Editor with Tabs */}
            <Box sx={{ mb: 3 }}>
              <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
                <Tab icon={<Code />} label={t('admin.promptEditor.tabEdit')} />
                <Tab icon={<Preview />} label={t('admin.promptEditor.tabPreview')} />
              </Tabs>

              <Box sx={{ mt: 2 }}>
                {activeTab === 0 ? (
                  <TextField
                    fullWidth
                    multiline
                    rows={16}
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    placeholder={t('admin.promptEditor.contentPlaceholder')}
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
                        {t('admin.promptEditor.noContent')}
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
              {t('admin.promptEditor.sectionCategorization')}
            </Typography>

            {/* Category */}
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>{t('admin.promptEditor.categoryLabel')}</InputLabel>
              <Select
                value={formData.category}
                label={t('admin.promptEditor.categoryLabel')}
                onChange={(e: SelectChangeEvent) =>
                  setFormData({ ...formData, category: e.target.value as any })
                }
              >
                <MenuItem value="system_prompt">{t('admin.promptEditor.categorySystem')}</MenuItem>
                <MenuItem value="user_prompt">{t('admin.promptEditor.categoryUser')}</MenuItem>
                <MenuItem value="few_shot_example">{t('admin.promptEditor.categoryFewShot')}</MenuItem>
                <MenuItem value="template">{t('admin.promptEditor.categoryTemplate')}</MenuItem>
              </Select>
            </FormControl>

            {/* Use Case - Fragetyp Dropdown */}
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel id="use-case-label">{t('admin.promptEditor.useCaseLabel')}</InputLabel>
              <Select
                labelId="use-case-label"
                id="use-case-select"
                value={formData.use_case || ''}
                label={t('admin.promptEditor.useCaseLabel')}
                onChange={(e: SelectChangeEvent) =>
                  setFormData({ ...formData, use_case: e.target.value })
                }
              >
                <MenuItem value="">
                  <em>{t('admin.promptEditor.useCaseNone')}</em>
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
                {t('admin.promptEditor.tagsLabel')}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <TextField
                  size="small"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={t('admin.promptEditor.tagPlaceholder')}
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
              label={t('admin.promptEditor.activeLabel')}
            />
          </Paper>

          {/* Version History (only for existing prompts) */}
          {promptId && (
            <Paper elevation={2} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                <History sx={{ verticalAlign: 'middle', mr: 1 }} />
                {t('admin.promptEditor.versionHistoryTitle')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('admin.promptEditor.currentVersion', { version: formData.version })}
              </Typography>
              <Button
                variant="outlined"
                fullWidth
                onClick={() => console.log('Show versions', promptId)}
              >
                {t('admin.promptEditor.btnShowVersions')}
              </Button>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Container>
  );
};
