import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Autocomplete,
  Box,
  Button,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  OutlinedInput,
  Select,
  SelectChangeEvent,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  DocumentListParams,
  DocumentTag,
  MimeFamily,
  StatusGroup,
  ViewMode,
  VisibilityFilter,
} from '../../types/document';
import { useDebounce } from '../../hooks/useDebounce';

interface DocumentLibraryToolbarProps {
  params: DocumentListParams;
  view: ViewMode;
  availableTags: DocumentTag[];
  onChange: (key: keyof DocumentListParams | 'view', value: unknown) => void;
  onReset: () => void;
}

export default function DocumentLibraryToolbar({
  params,
  view,
  availableTags,
  onChange,
  onReset,
}: DocumentLibraryToolbarProps) {
  const { t } = useTranslation();

  // --- local search state with debounce ---
  const [localQ, setLocalQ] = useState(params.q ?? '');
  const debouncedQ = useDebounce(localQ, 300);

  useEffect(() => {
    onChange('q', debouncedQ || undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ]);

  // Keep local state in sync when params.q is cleared externally (e.g. chip delete)
  const [prevParamsQ, setPrevParamsQ] = useState(params.q);
  if (params.q !== prevParamsQ) {
    setPrevParamsQ(params.q);
    if (!params.q && localQ) {
      setLocalQ('');
    }
  }

  // --- visibility ---
  const handleVisibilityChange = (e: SelectChangeEvent<string>) => {
    onChange('visibility', (e.target.value as VisibilityFilter) || undefined);
  };

  // --- status ---
  const handleStatusChange = (e: SelectChangeEvent<StatusGroup[]>) => {
    onChange('status', e.target.value as StatusGroup[]);
  };

  // --- mime_family ---
  const handleMimeFamilyChange = (e: SelectChangeEvent<MimeFamily[]>) => {
    onChange('mime_family', e.target.value as MimeFamily[]);
  };

  // --- tags autocomplete ---
  const selectedTags = (availableTags ?? []).filter((tag) =>
    (params.tag_ids ?? []).includes(tag.id),
  );

  // --- view toggle ---
  const handleViewChange = (_: React.MouseEvent, next: ViewMode | null) => {
    if (next) onChange('view', next);
  };

  // --- active filter chips ---
  const visibilityLabel =
    params.visibility === 'own'
      ? t('components.documentLibrary.toolbar.visibilityOwn', 'Eigene')
      : t('components.documentLibrary.toolbar.visibilityShared', 'Geteilte');

  const chips: React.ReactNode[] = [];

  if (params.visibility) {
    chips.push(
      <Chip
        key="visibility"
        label={`${t('components.documentLibrary.toolbar.labelVisibility', 'Sichtbarkeit')}: ${visibilityLabel}`}
        size="small"
        onDelete={() => onChange('visibility', undefined)}
      />,
    );
  }

  (params.status ?? []).forEach((s) => {
    chips.push(
      <Chip
        key={`status-${s}`}
        label={`${t('components.documentLibrary.toolbar.labelStatus', 'Status')}: ${t(`components.documentLibrary.toolbar.statusGroups.${s}`, s)}`}
        size="small"
        onDelete={() =>
          onChange(
            'status',
            (params.status ?? []).filter((x) => x !== s),
          )
        }
      />,
    );
  });

  (params.mime_family ?? []).forEach((m) => {
    chips.push(
      <Chip
        key={`mime-${m}`}
        label={`${t('components.documentLibrary.toolbar.labelType', 'Typ')}: ${t(`components.documentLibrary.toolbar.mimeFamilies.${m}`, m)}`}
        size="small"
        onDelete={() =>
          onChange(
            'mime_family',
            (params.mime_family ?? []).filter((x) => x !== m),
          )
        }
      />,
    );
  });

  (params.tag_ids ?? []).forEach((id) => {
    const tag = (availableTags ?? []).find((t) => t.id === id);
    const label = tag ? tag.name : `#${id}`;
    chips.push(
      <Chip
        key={`tag-${id}`}
        label={label}
        size="small"
        onDelete={() =>
          onChange(
            'tag_ids',
            (params.tag_ids ?? []).filter((x) => x !== id),
          )
        }
      />,
    );
  });

  if (params.q) {
    chips.push(
      <Chip
        key="q"
        label={`„${params.q}"`}
        size="small"
        onDelete={() => {
          onChange('q', undefined);
          setLocalQ('');
        }}
      />,
    );
  }

  const showReset = chips.length >= 2;

  return (
    <Box>
      {/* Controls row */}
      <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="center" sx={{ mb: 1 }}>
        {/* 1. Search */}
        <TextField
          size="small"
          placeholder={t('components.documentLibrary.toolbar.searchPlaceholder', 'Suchen…')}
          value={localQ}
          onChange={(e) => setLocalQ(e.target.value)}
          sx={{ minWidth: 180 }}
        />

        {/* 2. Visibility single-select */}
        <FormControl size="small" sx={{ minWidth: 130 }}>
          <InputLabel>{t('components.documentLibrary.toolbar.visibility', 'Sichtbarkeit')}</InputLabel>
          <Select
            value={params.visibility ?? ''}
            label={t('components.documentLibrary.toolbar.visibility', 'Sichtbarkeit')}
            onChange={handleVisibilityChange}
          >
            <MenuItem value="">{t('components.documentLibrary.toolbar.visibilityAll', 'Alle')}</MenuItem>
            <MenuItem value="own">{t('components.documentLibrary.toolbar.visibilityOwn', 'Eigene')}</MenuItem>
            <MenuItem value="shared">{t('components.documentLibrary.toolbar.visibilityShared', 'Geteilte')}</MenuItem>
          </Select>
        </FormControl>

        {/* 3. Status multi-select */}
        <FormControl size="small" sx={{ minWidth: 130 }}>
          <InputLabel>{t('components.documentLibrary.toolbar.status', 'Status')}</InputLabel>
          <Select<StatusGroup[]>
            multiple
            value={params.status ?? []}
            label={t('components.documentLibrary.toolbar.status', 'Status')}
            onChange={handleStatusChange}
            input={<OutlinedInput label={t('components.documentLibrary.toolbar.status', 'Status')} />}
          >
            {(['uploaded', 'processing', 'processed', 'error'] as StatusGroup[]).map((s) => (
              <MenuItem key={s} value={s}>
                {t(`components.documentLibrary.toolbar.statusGroups.${s}`, s)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* 4. Type multi-select */}
        <FormControl size="small" sx={{ minWidth: 130 }}>
          <InputLabel>{t('components.documentLibrary.toolbar.type', 'Typ')}</InputLabel>
          <Select<MimeFamily[]>
            multiple
            value={params.mime_family ?? []}
            label={t('components.documentLibrary.toolbar.type', 'Typ')}
            onChange={handleMimeFamilyChange}
            input={<OutlinedInput label={t('components.documentLibrary.toolbar.type', 'Typ')} />}
          >
            {(['pdf', 'word', 'markdown', 'text', 'chat'] as MimeFamily[]).map((m) => (
              <MenuItem key={m} value={m}>
                {t(`components.documentLibrary.toolbar.mimeFamilies.${m}`, m)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* 5. Tags autocomplete */}
        <Autocomplete
          multiple
          size="small"
          options={availableTags ?? []}
          getOptionLabel={(o) => o.name}
          isOptionEqualToValue={(a, b) => a.id === b.id}
          value={selectedTags}
          onChange={(_, selected) => onChange('tag_ids', selected.map((t) => t.id))}
          sx={{ minWidth: 180 }}
          renderInput={(inputProps) => (
            <TextField
              {...inputProps}
              label={t('components.documentLibrary.toolbar.tags', 'Tags')}
            />
          )}
        />

        {/* 6. View-mode toggle */}
        <ToggleButtonGroup
          exclusive
          value={view}
          onChange={handleViewChange}
          size="small"
        >
          <ToggleButton value="cards">
            {t('components.documentLibrary.toolbar.viewCards', 'Karten')}
          </ToggleButton>
          <ToggleButton value="list">
            {t('components.documentLibrary.toolbar.viewList', 'Liste')}
          </ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {/* Active filter chip row */}
      {chips.length > 0 && (
        <Stack direction="row" spacing={0.5} flexWrap="wrap" alignItems="center">
          {chips}
          {showReset && (
            <Button size="small" onClick={onReset}>
              {t('components.documentLibrary.toolbar.resetAll', 'Alle zurücksetzen')}
            </Button>
          )}
        </Stack>
      )}
    </Box>
  );
}
