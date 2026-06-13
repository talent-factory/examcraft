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
import { PromptCategory, PromptVisibility } from '../../types/prompt';
import { useAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../types/auth';
import MarkdownRenderer from '../MarkdownRenderer';
import TagAutocomplete from '../shared/TagAutocomplete';
import { tagsApi, type Tag, type TagValue, isPendingTag } from '../../api/tagsApi';

/** TF-397: a prompt's managed tags arrive as {id, name}; lift them into the
 * TagValue shape the shared TagAutocomplete works with. */
const toTagValue = (t: { id: number; name: string }): Tag => ({
  id: t.id,
  name: t.name,
  scope: 'global',
  kind: 'prompt',
  institution_id: null,
  usage_count: 0,
  is_archived: false,
  is_own: false,
});

/** TF-397: initialData tags can come from a loaded prompt as {id, name}, or from
 * the Prompt-Wizard's "Edit in Editor" path as plain name strings (suggested
 * tags that aren't managed Tag rows yet). Strings — and objects without a real
 * id — become PendingTags so they are created on save instead of being silently
 * dropped (toTagValue would otherwise yield {id: undefined, name: undefined}). */
const toInitialTagValue = (t: string | { id?: number; name: string }): TagValue => {
  if (typeof t === 'string') return { __pending: true as const, name: t };
  if (typeof t.id === 'number') return toTagValue({ id: t.id, name: t.name });
  return { __pending: true as const, name: t.name };
};

/** Extract a user-friendly error message from Axios/FastAPI errors. */
function extractErrorMessage(
  err: unknown,
  fallback: string,
  labels: { validationError: string; fieldDefault: string; invalidDefault: string; useCaseRequired: string }
): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (err.response?.status === 422 && detail) {
      const details = Array.isArray(detail) ? detail : [detail];
      const messages = details.map((d: unknown) => {
        if (typeof d === 'object' && d !== null && 'msg' in d) {
          const entry = d as { loc?: unknown; msg?: unknown; message?: unknown };
          const loc = Array.isArray(entry.loc) ? entry.loc : [];
          const field = (loc.slice(1).join('.')) || labels.fieldDefault;
          const msg = String(entry.msg || entry.message || labels.invalidDefault);
          if (field === 'use_case' && msg.includes('match pattern')) {
            return labels.useCaseRequired;
          }
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
  const { user, hasRole } = useAuth();
  // TF-410: who may pick which visibility tier (mirrors the backend guard).
  const isSuperuser = !!user?.is_superuser;
  const isAdmin = isSuperuser || hasRole(UserRole.ADMIN);

  const USE_CASE_LABELS: Record<string, string> = {
    'question_generation': t('admin.promptEditor.useCaseGeneral'),
    'question_generation_single_choice': t('admin.promptEditor.useCaseMultipleChoice'),
    'question_generation_open_ended': t('admin.promptEditor.useCaseOpenEnded'),
    'question_generation_true_false': t('admin.promptEditor.useCaseTrueFalse'),
    'chatbot': t('admin.promptEditor.useCaseChatbot'),
    'evaluation': t('admin.promptEditor.useCaseEvaluation'),
  };

  const errorLabels = {
    validationError: t('admin.promptEditor.validationError'),
    fieldDefault: t('admin.promptEditor.fieldDefault'),
    invalidDefault: t('admin.promptEditor.invalidDefault'),
    useCaseRequired: t('admin.promptEditor.useCaseRequired'),
  };

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  // TF-397: managed prompt-tags selected via the autocomplete (Tag | PendingTag).
  const [selectedTags, setSelectedTags] = useState<TagValue[]>([]);

  const [formData, setFormData] = useState<Partial<Prompt>>({
    name: '',
    content: '',
    description: '',
    category: PromptCategory.SYSTEM_PROMPT,
    use_case: '',
    tags: [],
    is_active: false,
    // TF-410: new prompts default to the most private tier.
    visibility: PromptVisibility.PRIVATE,
    is_institution_default: false
  });

  const loadPrompt = useCallback(async () => {
    if (!promptId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await promptsApi.getPrompt(promptId);
      setFormData(data);
      setSelectedTags((data.tags ?? []).map(toTagValue));
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
      if (initialData.tags) {
        // initialData may come from the wizard with tags as name strings.
        const rawTags = initialData.tags as Array<string | { id?: number; name: string }>;
        setSelectedTags(rawTags.map(toInitialTagValue));
      }
    }
  }, [promptId, initialData]);

  const handleSave = async () => {
    if (!formData.name || !formData.content || !formData.category || !formData.use_case) {
      setError(t('admin.promptEditor.validationRequired'));
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      // TF-397: resolve selected tags into managed tag_ids. Pending (inline-typed)
      // tags are created as global kind='prompt' tags first, then linked by id.
      const pending = selectedTags.filter(isPendingTag);
      const existing = selectedTags.filter((tg): tg is Tag => !isPendingTag(tg));
      const created = await Promise.all(
        pending.map((p) => tagsApi.createTag(p.name, 'global', 'prompt'))
      );
      const tag_ids = Array.from(
        new Set([...existing.map((tg) => tg.id), ...created.map((tg) => tg.id)])
      );

      if (promptId) {
        const result = await promptsApi.updatePrompt(promptId, {
          content: formData.content,
          description: formData.description,
          category: formData.category,
          use_case: formData.use_case,
          tag_ids,
          // TF-410: tier changes (permission-checked server-side).
          visibility: formData.visibility,
          is_institution_default: formData.is_institution_default,
        });
        const versionBumped = result.version > (formData.version ?? 1);
        setFormData(result);
        setSelectedTags((result.tags ?? []).map(toTagValue));
        setSuccess(versionBumped
          ? t('admin.promptEditor.successVersionCreated', { version: result.version })
          : t('admin.promptEditor.successUpdated')
        );
      } else {
        await promptsApi.createPrompt({
          name: formData.name,
          content: formData.content,
          category: formData.category,
          use_case: formData.use_case,
          description: formData.description,
          is_active: formData.is_active ?? false,
          tag_ids,
          // TF-410: chosen visibility tier (permission-checked server-side).
          visibility: formData.visibility,
          is_institution_default: formData.is_institution_default,
        });
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
            <FormControl fullWidth sx={{ mb: 3 }} required error={!!error && !formData.use_case}>
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
                {Object.entries(USE_CASE_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Visibility tier (TF-410) */}
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel id="visibility-label">
                {t('admin.promptEditor.visibilityLabel')}
              </InputLabel>
              <Select
                labelId="visibility-label"
                value={formData.visibility ?? PromptVisibility.PRIVATE}
                label={t('admin.promptEditor.visibilityLabel')}
                disabled={saving}
                onChange={(e: SelectChangeEvent) =>
                  setFormData({
                    ...formData,
                    visibility: e.target.value as PromptVisibility,
                    // institution_default is only valid for the institution tier
                    is_institution_default:
                      e.target.value === PromptVisibility.INSTITUTION
                        ? formData.is_institution_default
                        : false,
                  })
                }
              >
                <MenuItem value={PromptVisibility.PRIVATE}>
                  {t('admin.promptEditor.visibilityPrivate')}
                </MenuItem>
                <MenuItem value={PromptVisibility.INSTITUTION}>
                  {t('admin.promptEditor.visibilityInstitution')}
                </MenuItem>
                {isSuperuser && (
                  <MenuItem value={PromptVisibility.SYSTEM}>
                    {t('admin.promptEditor.visibilitySystem')}
                  </MenuItem>
                )}
              </Select>
            </FormControl>

            {/* Institution default — admin-only, institution tier only (TF-410) */}
            {isAdmin && formData.visibility === PromptVisibility.INSTITUTION && (
              <FormControlLabel
                sx={{ mb: 2, display: 'block' }}
                control={
                  <Switch
                    checked={!!formData.is_institution_default}
                    disabled={saving}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        is_institution_default: e.target.checked,
                      })
                    }
                  />
                }
                label={t('admin.promptEditor.institutionDefaultLabel')}
              />
            )}

            {/* Tags — TF-397: managed prompt-tags via autocomplete (select or inline-create) */}
            <Box sx={{ mb: 3 }}>
              <TagAutocomplete
                value={selectedTags}
                onChange={setSelectedTags}
                disabled={saving}
                label={t('admin.promptEditor.tagsLabel')}
                kind="prompt"
                deferCreation
              />
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
