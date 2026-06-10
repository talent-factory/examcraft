import React, { useState } from 'react';
import {
  Box,
  TextField,
  MenuItem,
  Button,
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import type {
  FrameworkVisibility,
  FrameworkCreatePayload,
} from '../../types/competencyFramework';

export interface FrameworkFormValues {
  name: string;
  module_code: string;
  description: string;
  rendered_text: string;
  language: string;
  visibility: FrameworkVisibility;
}

interface Props {
  mode: 'create' | 'edit';
  initial?: Partial<FrameworkFormValues>;
  submitting?: boolean;
  onSubmit: (payload: FrameworkCreatePayload) => void;
  onCancel: () => void;
}

const EMPTY: FrameworkFormValues = {
  name: '',
  module_code: '',
  description: '',
  rendered_text: '',
  language: 'de',
  visibility: 'institution',
};

const CompetencyFrameworkForm: React.FC<Props> = ({
  mode,
  initial,
  submitting = false,
  onSubmit,
  onCancel,
}) => {
  const { t } = useTranslation();
  const [values, setValues] = useState<FrameworkFormValues>({ ...EMPTY, ...initial });

  const set = <K extends keyof FrameworkFormValues>(key: K, value: FrameworkFormValues[K]) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const canSubmit = values.name.trim().length > 0 && values.rendered_text.trim().length > 0;

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit({
      name: values.name.trim(),
      module_code: values.module_code.trim() || undefined,
      description: values.description.trim() || undefined,
      rendered_text: values.rendered_text,
      language: values.language,
      visibility: values.visibility,
    });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
      <TextField
        label={t('competencyFrameworks.form.name')}
        value={values.name}
        onChange={(e) => set('name', e.target.value)}
        required
        fullWidth
      />
      <TextField
        label={t('competencyFrameworks.form.moduleCode')}
        value={values.module_code}
        onChange={(e) => set('module_code', e.target.value)}
        fullWidth
        inputProps={{ maxLength: 20 }}
      />
      <TextField
        label={t('competencyFrameworks.form.description')}
        value={values.description}
        onChange={(e) => set('description', e.target.value)}
        fullWidth
        multiline
        minRows={2}
      />
      <TextField
        label={t('competencyFrameworks.form.renderedText')}
        value={values.rendered_text}
        onChange={(e) => set('rendered_text', e.target.value)}
        required
        fullWidth
        multiline
        minRows={8}
        helperText={t('competencyFrameworks.form.renderedTextHelper')}
      />
      <Box sx={{ display: 'flex', gap: 2 }}>
        <TextField
          select
          label={t('competencyFrameworks.form.visibility')}
          value={values.visibility}
          onChange={(e) => set('visibility', e.target.value as FrameworkVisibility)}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="institution">{t('competencyFrameworks.visibility.institution')}</MenuItem>
          <MenuItem value="private">{t('competencyFrameworks.visibility.private')}</MenuItem>
        </TextField>
        <TextField
          select
          label={t('competencyFrameworks.form.language')}
          value={values.language}
          onChange={(e) => set('language', e.target.value)}
          sx={{ minWidth: 120 }}
        >
          <MenuItem value="de">DE</MenuItem>
          <MenuItem value="en">EN</MenuItem>
          <MenuItem value="fr">FR</MenuItem>
          <MenuItem value="it">IT</MenuItem>
        </TextField>
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
        <Button onClick={onCancel} disabled={submitting}>
          {t('competencyFrameworks.form.cancel')}
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={!canSubmit || submitting}>
          {t('competencyFrameworks.form.save')}
        </Button>
      </Box>
    </Box>
  );
};

export default CompetencyFrameworkForm;
