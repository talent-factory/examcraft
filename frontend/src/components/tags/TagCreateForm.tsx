import React, { useState, useMemo } from 'react';
import { Box, TextField, Button, Alert, Paper, Typography, FormControlLabel, Switch } from '@mui/material';
import { Unarchive } from '@mui/icons-material';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { tagsApi } from '../../api/tagsApi';
import { useAuth } from '../../contexts/AuthContext';
import { apiDetail, translateError } from '../../errors';

export interface ExistingTagInfo {
  id: number;
  name: string;
  is_archived: boolean;
  scope: 'global' | 'institution';
}

interface Props {
  existingTags: ExistingTagInfo[];
}

const TagCreateForm: React.FC<Props> = ({ existingTags }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isSuperuser = user?.is_superuser === true;
  const [name, setName] = useState('');
  const [isGlobal, setIsGlobal] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const existingMatch = useMemo(
    () => existingTags.find(
      (tag) => tag.name.toLowerCase() === name.trim().toLowerCase() &&
             tag.scope === (isGlobal ? 'global' : 'institution')
    ) ?? null,
    [existingTags, name, isGlobal],
  );

  const createMutation = useMutation({
    mutationFn: (tagName: string) => tagsApi.createTag(tagName, isGlobal ? 'global' : 'institution'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
      setName('');
      setCreateError(null);
    },
    onError: (err) =>
      setCreateError(apiDetail(err) ?? translateError(err, t, 'components.tags.createErrorFallback')),
  });

  const unarchiveMutation = useMutation({
    mutationFn: (id: number) => tagsApi.unarchiveTag(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
      setName('');
    },
    onError: (err) =>
      setCreateError(apiDetail(err) ?? translateError(err, t, 'components.tags.restoreFailed')),
  });

  const handleCreate = () => {
    const trimmed = name.trim();
    if (!trimmed || existingMatch) return;
    createMutation.mutate(trimmed);
  };

  return (
    <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
      <Typography
        variant="overline"
        color="primary"
        sx={{ display: 'block', mb: 1, fontWeight: 600, lineHeight: 1.5 }}
      >
        {t('components.tags.createTitle')}
      </Typography>

      {isSuperuser && (
        <FormControlLabel
          sx={{ mb: 1 }}
          control={
            <Switch
              size="small"
              checked={isGlobal}
              onChange={(e) => setIsGlobal(e.target.checked)}
            />
          }
          label={
            <Typography variant="caption" color={isGlobal ? 'primary' : 'text.secondary'}>
              {t('components.tags.globalTag')}
            </Typography>
          }
        />
      )}

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          size="small"
          placeholder={t('components.tags.namePlaceholder')}
          value={name}
          onChange={(e) => { setName(e.target.value); setCreateError(null); }}
          onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          sx={{ flex: 1 }}
          error={!!createError}
          helperText={createError ?? undefined}
        />
        <Button
          variant="contained"
          size="small"
          onClick={handleCreate}
          disabled={!name.trim() || !!existingMatch || createMutation.isPending}
          sx={{ whiteSpace: 'nowrap' }}
        >
          {t('components.tags.createButton')}
        </Button>
      </Box>

      {existingMatch && !existingMatch.is_archived && (
        <Alert severity="warning" sx={{ mt: 1, py: 0.5 }}>
          {t('components.tags.existsPrefix')} <strong>#{existingMatch.name}</strong> {t('components.tags.existsSuffix')}
        </Alert>
      )}

      {existingMatch?.is_archived && (
        <Alert severity="info" sx={{ mt: 1, py: 0.5 }}>
          <Box>
            {t('components.tags.existsPrefix')} <strong>#{existingMatch.name}</strong> {t('components.tags.archivedSuffix')}
            <Box sx={{ mt: 1 }}>
              <Button
                variant="contained"
                size="small"
                startIcon={<Unarchive />}
                onClick={() => unarchiveMutation.mutate(existingMatch.id)}
                disabled={unarchiveMutation.isPending}
              >
                {t('components.tags.restore')}
              </Button>
            </Box>
          </Box>
        </Alert>
      )}
    </Paper>
  );
};

export default TagCreateForm;
