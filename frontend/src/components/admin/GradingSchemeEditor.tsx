/**
 * GradingSchemeEditor — Dialog for creating/editing institution grading schemes.
 *
 * Live preview is computed locally in TS (same logic as the backend evaluator)
 * to avoid an extra round-trip on every keystroke.
 *
 * Config type is chosen via a radio group; the form section below it swaps
 * layout based on the selected type (linear / linear_segments / stepped).
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  FormHelperText,
  FormLabel,
  IconButton,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';

import {
  DISPLAY_FORMATS,
  GradingSchemeConfig,
  GradingSchemeCreate,
  GradingSchemeDisplayFormat,
  GradingSchemeOut,
  GradingSchemeUpdate,
  LinearConfig,
  LinearSegmentConfig,
  SteppedConfig,
} from '../../types/gradingScheme';
import { GradingSchemesService } from '../../services/gradingSchemesService';
import { ApiError } from '../../services/submissionsService';

// ---------------------------------------------------------------------------
// Local grade evaluator (mirrors backend grading_evaluator.py logic)
// Returns a grade label string or null when pct is out of range / config invalid.
// ---------------------------------------------------------------------------

function evaluateGrade(config: GradingSchemeConfig, pct: number): string | null {
  if (config.type === 'linear') {
    const { min_pct, max_pct, min_grade, max_grade, round_to } = config;
    if (pct < min_pct || pct > max_pct) return null;
    if (max_pct === min_pct) return String(min_grade);
    const raw = min_grade + ((pct - min_pct) / (max_pct - min_pct)) * (max_grade - min_grade);
    const r = round_to ?? 1;
    const grade = r > 0 ? Math.round(raw / r) * r : raw;
    return String(parseFloat(grade.toFixed(10)));
  }

  if (config.type === 'linear_segments') {
    const { segments, round_to } = config;
    const sorted = [...segments].sort((a, b) => a.from_pct - b.from_pct);
    for (const seg of sorted) {
      if (pct >= seg.from_pct && pct <= seg.to_pct) {
        const span = seg.to_pct - seg.from_pct;
        const raw =
          span === 0
            ? seg.from_grade
            : seg.from_grade +
              ((pct - seg.from_pct) / span) * (seg.to_grade - seg.from_grade);
        const r = round_to ?? 0.1;
        const grade = r > 0 ? Math.round(raw / r) * r : raw;
        return String(parseFloat(grade.toFixed(10)));
      }
    }
    return null;
  }

  if (config.type === 'stepped') {
    const sorted = [...config.steps].sort((a, b) => b.min_pct - a.min_pct);
    for (const step of sorted) {
      if (pct >= step.min_pct) return step.grade_label;
    }
    return null;
  }

  return null;
}

// ---------------------------------------------------------------------------
// Default configs per type
// ---------------------------------------------------------------------------

const DEFAULT_LINEAR: LinearConfig = {
  type: 'linear',
  min_pct: 0,
  max_pct: 100,
  min_grade: 0,
  max_grade: 20,
  round_to: 0.5,
  pass_grade_label: '10',
};

const DEFAULT_LINEAR_SEGMENTS: LinearSegmentConfig = {
  type: 'linear_segments',
  round_to: 0.1,
  pass_grade_label: '4.0',
  segments: [
    { from_pct: 0, to_pct: 50, from_grade: 1.0, to_grade: 4.0 },
    { from_pct: 50, to_pct: 100, from_grade: 4.0, to_grade: 6.0 },
  ],
};

const DEFAULT_STEPPED: SteppedConfig = {
  type: 'stepped',
  steps: [
    { min_pct: 92, grade_label: '1.0', is_passing: true },
    { min_pct: 81, grade_label: '2.0', is_passing: true },
    { min_pct: 67, grade_label: '3.0', is_passing: true },
    { min_pct: 50, grade_label: '4.0', is_passing: true },
    { min_pct: 0, grade_label: '5.0', is_passing: false },
  ],
};

type ConfigType = GradingSchemeConfig['type'];

function defaultConfigFor(type: ConfigType): GradingSchemeConfig {
  if (type === 'linear') return { ...DEFAULT_LINEAR };
  if (type === 'linear_segments') return {
    ...DEFAULT_LINEAR_SEGMENTS,
    segments: DEFAULT_LINEAR_SEGMENTS.segments.map(s => ({ ...s })),
  };
  return {
    ...DEFAULT_STEPPED,
    steps: DEFAULT_STEPPED.steps.map(s => ({ ...s })),
  };
}

// ---------------------------------------------------------------------------
// Sub-forms
// ---------------------------------------------------------------------------

interface LinearFormProps {
  config: LinearConfig;
  onChange: (c: LinearConfig) => void;
}

const LinearForm: React.FC<LinearFormProps> = ({ config, onChange }) => {
  const { t } = useTranslation();
  const upd = (patch: Partial<LinearConfig>) => onChange({ ...config, ...patch });
  const numField = (
    label: string,
    value: number | undefined,
    key: keyof LinearConfig,
    testId: string,
    required = false,
  ) => (
    <TextField
      size="small"
      label={label}
      type="number"
      inputProps={{ step: 'any', 'data-testid': testId }}
      value={value ?? ''}
      required={required}
      onChange={e => upd({ [key]: e.target.value === '' ? undefined : parseFloat(e.target.value) } as Partial<LinearConfig>)}
    />
  );

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={2}>
        {numField(t('admin.gradingSchemes.linearMinPct'), config.min_pct, 'min_pct', 'gs-linear-min-pct', true)}
        {numField(t('admin.gradingSchemes.linearMaxPct'), config.max_pct, 'max_pct', 'gs-linear-max-pct', true)}
      </Stack>
      <Stack direction="row" spacing={2}>
        {numField(t('admin.gradingSchemes.linearMinGrade'), config.min_grade, 'min_grade', 'gs-linear-min-grade', true)}
        {numField(t('admin.gradingSchemes.linearMaxGrade'), config.max_grade, 'max_grade', 'gs-linear-max-grade', true)}
      </Stack>
      <Stack direction="row" spacing={2}>
        {numField(t('admin.gradingSchemes.linearRoundTo'), config.round_to, 'round_to', 'gs-linear-round-to')}
        <TextField
          size="small"
          label={t('admin.gradingSchemes.linearPassGradeLabel')}
          value={config.pass_grade_label ?? ''}
          inputProps={{ 'data-testid': 'gs-linear-pass-label' }}
          onChange={e => upd({ pass_grade_label: e.target.value || undefined })}
        />
      </Stack>
    </Stack>
  );
};

interface LinearSegmentsFormProps {
  config: LinearSegmentConfig;
  onChange: (c: LinearSegmentConfig) => void;
}

const LinearSegmentsForm: React.FC<LinearSegmentsFormProps> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const upd = (patch: Partial<LinearSegmentConfig>) => onChange({ ...config, ...patch });

  const updateSeg = (idx: number, patch: Partial<LinearSegmentConfig['segments'][number]>) => {
    const segs = config.segments.map((s, i) => (i === idx ? { ...s, ...patch } : s));
    upd({ segments: segs });
  };

  const addSeg = () =>
    upd({
      segments: [
        ...config.segments,
        { from_pct: 0, to_pct: 100, from_grade: 1, to_grade: 6 },
      ],
    });

  const removeSeg = (idx: number) =>
    upd({ segments: config.segments.filter((_, i) => i !== idx) });

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={2}>
        <TextField
          size="small"
          label={t('admin.gradingSchemes.roundTo')}
          type="number"
          inputProps={{ step: 'any', 'data-testid': 'gs-seg-round-to' }}
          value={config.round_to ?? ''}
          onChange={e => upd({ round_to: e.target.value === '' ? undefined : parseFloat(e.target.value) })}
        />
        <TextField
          size="small"
          label={t('admin.gradingSchemes.passGradeLabel')}
          value={config.pass_grade_label ?? ''}
          inputProps={{ 'data-testid': 'gs-seg-pass-label' }}
          onChange={e => upd({ pass_grade_label: e.target.value || undefined })}
        />
      </Stack>

      <Typography variant="subtitle2">{t('admin.gradingSchemes.segmentsHeader')}</Typography>
      <Table size="small" data-testid="gs-segments-table">
        <TableHead>
          <TableRow>
            <TableCell>{t('admin.gradingSchemes.segmentFromPct')}</TableCell>
            <TableCell>{t('admin.gradingSchemes.segmentToPct')}</TableCell>
            <TableCell>{t('admin.gradingSchemes.segmentFromGrade')}</TableCell>
            <TableCell>{t('admin.gradingSchemes.segmentToGrade')}</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {config.segments.map((seg, idx) => (
            <TableRow key={idx}>
              {(['from_pct', 'to_pct', 'from_grade', 'to_grade'] as const).map(key => (
                <TableCell key={key}>
                  <TextField
                    size="small"
                    type="number"
                    inputProps={{ step: 'any', 'data-testid': `gs-seg-${idx}-${key}` }}
                    value={seg[key]}
                    sx={{ width: 80 }}
                    onChange={e =>
                      updateSeg(idx, { [key]: parseFloat(e.target.value) })
                    }
                  />
                </TableCell>
              ))}
              <TableCell>
                <IconButton
                  size="small"
                  onClick={() => removeSeg(idx)}
                  disabled={config.segments.length <= 1}
                  data-testid={`gs-seg-remove-${idx}`}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Button
        size="small"
        startIcon={<AddIcon />}
        onClick={addSeg}
        data-testid="gs-seg-add"
      >
        {t('admin.gradingSchemes.segmentAdd')}
      </Button>
    </Stack>
  );
};

interface SteppedFormProps {
  config: SteppedConfig;
  onChange: (c: SteppedConfig) => void;
}

const SteppedForm: React.FC<SteppedFormProps> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const upd = (patch: Partial<SteppedConfig>) => onChange({ ...config, ...patch });

  const updateStep = (idx: number, patch: Partial<SteppedConfig['steps'][number]>) => {
    const steps = config.steps.map((s, i) => (i === idx ? { ...s, ...patch } : s));
    upd({ steps });
  };

  const addStep = () =>
    upd({
      steps: [...config.steps, { min_pct: 0, grade_label: '', is_passing: false }],
    });

  const removeStep = (idx: number) =>
    upd({ steps: config.steps.filter((_, i) => i !== idx) });

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle2">{t('admin.gradingSchemes.stepsHeader')}</Typography>
      <Table size="small" data-testid="gs-steps-table">
        <TableHead>
          <TableRow>
            <TableCell>{t('admin.gradingSchemes.stepMinPct')}</TableCell>
            <TableCell>{t('admin.gradingSchemes.stepGradeLabel')}</TableCell>
            <TableCell>{t('admin.gradingSchemes.stepIsPassing')}</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {config.steps.map((step, idx) => (
            <TableRow key={idx}>
              <TableCell>
                <TextField
                  size="small"
                  type="number"
                  inputProps={{ step: 'any', 'data-testid': `gs-step-${idx}-min-pct` }}
                  value={step.min_pct}
                  sx={{ width: 80 }}
                  onChange={e => updateStep(idx, { min_pct: parseFloat(e.target.value) })}
                />
              </TableCell>
              <TableCell>
                <TextField
                  size="small"
                  inputProps={{ 'data-testid': `gs-step-${idx}-label` }}
                  value={step.grade_label}
                  sx={{ width: 100 }}
                  onChange={e => updateStep(idx, { grade_label: e.target.value })}
                />
              </TableCell>
              <TableCell>
                <Checkbox
                  size="small"
                  checked={step.is_passing}
                  inputProps={{ 'data-testid': `gs-step-${idx}-passing` } as React.InputHTMLAttributes<HTMLInputElement>}
                  onChange={e => updateStep(idx, { is_passing: e.target.checked })}
                />
              </TableCell>
              <TableCell>
                <IconButton
                  size="small"
                  onClick={() => removeStep(idx)}
                  disabled={config.steps.length <= 1}
                  data-testid={`gs-step-remove-${idx}`}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Button
        size="small"
        startIcon={<AddIcon />}
        onClick={addStep}
        data-testid="gs-step-add"
      >
        {t('admin.gradingSchemes.stepAdd')}
      </Button>
    </Stack>
  );
};

// ---------------------------------------------------------------------------
// Live preview
// ---------------------------------------------------------------------------

const PREVIEW_PCTS = [0, 25, 50, 75, 100];

interface LivePreviewProps {
  config: GradingSchemeConfig;
}

const LivePreview: React.FC<LivePreviewProps> = ({ config }) => {
  const { t } = useTranslation();
  return (
    <Box data-testid="gs-preview" sx={{ bgcolor: 'grey.50', borderRadius: 1, p: 1.5 }}>
      <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
        {t('admin.gradingSchemes.previewTitle')}
      </Typography>
      <Stack direction="row" spacing={2} flexWrap="wrap">
        {PREVIEW_PCTS.map(pct => {
          const grade = evaluateGrade(config, pct);
          return (
            <Box key={pct} data-testid={`gs-preview-${pct}`} sx={{ textAlign: 'center', minWidth: 48 }}>
              <Typography variant="caption" color="text.secondary">{pct}%</Typography>
              <Typography variant="body2" fontWeight="medium">
                {grade ?? '—'}
              </Typography>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface GradingSchemeEditorProps {
  open: boolean;
  scheme: GradingSchemeOut | null;
  onClose: () => void;
  onSaved: () => void;
}

const GradingSchemeEditor: React.FC<GradingSchemeEditorProps> = ({
  open,
  scheme,
  onClose,
  onSaved,
}) => {
  const { t } = useTranslation();
  const isEdit = scheme !== null;

  const [name, setName] = useState('');
  const [displayFormat, setDisplayFormat] = useState<GradingSchemeDisplayFormat>('numeric');
  const [isDefault, setIsDefault] = useState(false);
  const [configType, setConfigType] = useState<ConfigType>('linear');
  const [config, setConfig] = useState<GradingSchemeConfig>(defaultConfigFor('linear'));

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (scheme) {
      setName(scheme.name);
      setDisplayFormat(scheme.display_format);
      setIsDefault(scheme.is_default_for_institution);
      setConfigType(scheme.config.type);
      setConfig(scheme.config);
    } else {
      setName('');
      setDisplayFormat('numeric');
      setIsDefault(false);
      setConfigType('linear');
      setConfig(defaultConfigFor('linear'));
    }
    setError(null);
    setNameError(null);
  }, [open, scheme]);

  const handleConfigTypeChange = (type: ConfigType) => {
    setConfigType(type);
    setConfig(defaultConfigFor(type));
  };

  const validate = (): boolean => {
    if (!name.trim()) {
      setNameError(t('admin.gradingSchemes.validationNameRequired'));
      return false;
    }
    if (config.type === 'linear_segments' && config.segments.length === 0) {
      setError(t('admin.gradingSchemes.validationSegmentsRequired'));
      return false;
    }
    if (config.type === 'stepped' && config.steps.length === 0) {
      setError(t('admin.gradingSchemes.validationStepsRequired'));
      return false;
    }
    setNameError(null);
    setError(null);
    return true;
  };

  const handleSave = async () => {
    if (!validate()) return;
    setSaving(true);
    setError(null);
    try {
      if (isEdit && scheme) {
        const payload: GradingSchemeUpdate = {
          name: name.trim(),
          display_format: displayFormat,
          config,
          is_default_for_institution: isDefault,
        };
        await GradingSchemesService.update(scheme.id, payload);
      } else {
        const payload: GradingSchemeCreate = {
          name: name.trim(),
          display_format: displayFormat,
          config,
          is_default_for_institution: isDefault,
        };
        await GradingSchemesService.create(payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(
          isEdit
            ? t('admin.gradingSchemes.failedUpdate')
            : t('admin.gradingSchemes.failedCreate'),
        );
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      data-testid="gs-editor-dialog"
    >
      <DialogTitle>
        {isEdit
          ? t('admin.gradingSchemes.editorTitleEdit')
          : t('admin.gradingSchemes.editorTitleCreate')}
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={3} sx={{ pt: 1 }}>
          {error && (
            <Alert severity="error" data-testid="gs-editor-error">
              {error}
            </Alert>
          )}

          {/* Basic fields */}
          <TextField
            label={t('admin.gradingSchemes.fieldName')}
            value={name}
            required
            fullWidth
            error={!!nameError}
            helperText={nameError ?? undefined}
            inputProps={{ 'data-testid': 'gs-field-name' }}
            onChange={e => {
              setName(e.target.value);
              if (nameError) setNameError(null);
            }}
          />

          <FormControl size="small" sx={{ minWidth: 200 }}>
            <FormLabel>{t('admin.gradingSchemes.fieldDisplayFormat')}</FormLabel>
            <Select
              value={displayFormat}
              inputProps={{ 'data-testid': 'gs-field-display-format' }}
              onChange={e => setDisplayFormat(e.target.value as GradingSchemeDisplayFormat)}
            >
              {DISPLAY_FORMATS.map(fmt => (
                <MenuItem key={fmt} value={fmt}>
                  {t(`admin.gradingSchemes.displayFormat${fmt.charAt(0).toUpperCase() + fmt.slice(1).replace(/_([a-z])/g, (_, c) => c.toUpperCase())}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControlLabel
            control={
              <Switch
                checked={isDefault}
                onChange={e => setIsDefault(e.target.checked)}
                inputProps={{ 'data-testid': 'gs-field-is-default' } as React.InputHTMLAttributes<HTMLInputElement>}
              />
            }
            label={t('admin.gradingSchemes.fieldIsDefault')}
          />

          <Divider />

          {/* Config type selector */}
          <FormControl>
            <FormLabel data-testid="gs-config-type-label">
              {t('admin.gradingSchemes.configType')}
            </FormLabel>
            <RadioGroup
              value={configType}
              onChange={e => handleConfigTypeChange(e.target.value as ConfigType)}
              data-testid="gs-config-type-radio"
            >
              <FormControlLabel
                value="linear"
                control={<Radio size="small" />}
                label={t('admin.gradingSchemes.configTypeLinear')}
                data-testid="gs-config-type-linear"
              />
              <FormControlLabel
                value="linear_segments"
                control={<Radio size="small" />}
                label={t('admin.gradingSchemes.configTypeLinearSegments')}
                data-testid="gs-config-type-linear-segments"
              />
              <FormControlLabel
                value="stepped"
                control={<Radio size="small" />}
                label={t('admin.gradingSchemes.configTypeStepped')}
                data-testid="gs-config-type-stepped"
              />
            </RadioGroup>
            <FormHelperText />
          </FormControl>

          {/* Config sub-form */}
          {config.type === 'linear' && (
            <LinearForm config={config} onChange={setConfig} />
          )}
          {config.type === 'linear_segments' && (
            <LinearSegmentsForm config={config} onChange={setConfig} />
          )}
          {config.type === 'stepped' && (
            <SteppedForm config={config} onChange={setConfig} />
          )}

          <Divider />

          {/* Live preview */}
          <LivePreview config={config} />
        </Stack>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={saving} data-testid="gs-editor-cancel">
          {t('admin.gradingSchemes.btnCancel')}
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={saving}
          startIcon={saving ? <CircularProgress size={16} /> : undefined}
          data-testid="gs-editor-save"
        >
          {saving
            ? t('admin.gradingSchemes.btnSaving')
            : t('admin.gradingSchemes.btnSave')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default GradingSchemeEditor;
export { evaluateGrade };
