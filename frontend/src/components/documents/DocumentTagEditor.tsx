import React, { useState } from 'react';
import Autocomplete, { createFilterOptions } from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import { useTranslation } from 'react-i18next';
import { Document, DocumentTag, DocumentVisibility } from '../../types/document';
import { DocumentService } from '../../services/DocumentService';

interface DocumentTagEditorProps {
  document: Document;
  availableTags: DocumentTag[];
  canEdit: boolean;
  // TF-399: whether the current user owns the document. Non-owners may still
  // attach/detach their own `user`-scope (personal) tags to any visible
  // document, but may not touch shared `institution`/`global` assignments.
  isOwner: boolean;
  onChanged: (updated: Document) => void;
}

// Allow freeSolo entries (plain strings for new tags) mixed with DocumentTag objects.
type TagOrString = DocumentTag | string;

const filter = createFilterOptions<DocumentTag>();

const DocumentTagEditor: React.FC<DocumentTagEditorProps> = ({
  document,
  availableTags,
  canEdit,
  isOwner,
  onChanged,
}) => {
  const { t } = useTranslation();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentTags: DocumentTag[] = document.tags ?? [];

  // TF-382: An `institution`-scope tag may only be attached to an
  // `INSTITUTION`-visible document (backend rule in utils/document_tags.py).
  // On a private document such tags are a dead end — selecting one fails with
  // a 400. Detect them so we can disable the option up front instead of letting
  // the user pick something that can never attach.
  const isInstitutionBlocked = (option: TagOrString): boolean =>
    typeof option !== 'string' &&
    option.scope === 'institution' &&
    document.visibility !== DocumentVisibility.INSTITUTION;

  // TF-399: a non-owner may only manage their own `user`-scope (personal) tags.
  // Shared `institution`/`global` assignments stay owner-only (the backend
  // returns 403), so disable those options up front for non-owners.
  const isOwnerOnlyBlocked = (option: TagOrString): boolean =>
    typeof option !== 'string' && !isOwner && option.scope !== 'user';

  const handleChange = async (
    _event: React.SyntheticEvent,
    newValue: TagOrString[],
  ) => {
    if (!canEdit) return;
    setError(null);
    setSaving(true);

    // Track the latest known document state across all mutations and emit a
    // single `onChanged` at the end. Each attach call returns the document with
    // its FULL current tag set (authoritative), so we let the last server
    // response win rather than interleaving optimistic updates — which, if a
    // change both removed and added tags, could otherwise surface an
    // intermediate (and on some backends inconsistent) tag list to the parent.
    let latest: Document = document;
    let mutated = false;
    try {
      // 1. Handle removals: existing tags not present in newValue. Detach
      //    returns no body, so apply the removal optimistically to `latest`.
      const removedTags = currentTags
        .filter(
          (existing) =>
            !newValue.some(
              (v) => typeof v !== 'string' && v.id === existing.id,
            ),
        )
        // TF-399: a non-owner may only detach their own personal assignments;
        // shared tags stay owner-only (defence in depth — the chip's delete
        // affordance is already hidden for them in renderTags).
        .filter((existing) => isOwner || existing.is_personal === true);
      for (const tag of removedTags) {
        await DocumentService.detachDocumentTag(document.id, tag.id);
        latest = {
          ...latest,
          tags: (latest.tags ?? []).filter((x) => x.id !== tag.id),
        };
        mutated = true;
      }

      // 2. Handle additions: new DocumentTag entries not already in currentTags
      const addedTags = newValue.filter(
        (v): v is DocumentTag =>
          typeof v !== 'string' &&
          !currentTags.some((existing) => existing.id === v.id) &&
          // TF-399: a non-owner may only attach their own `user`-scope tags.
          (isOwner || v.scope === 'user'),
      );
      for (const tag of addedTags) {
        latest = await DocumentService.attachDocumentTags(document.id, [tag.id]);
        mutated = true;
      }

      // 3. Handle freeSolo new tags (plain strings)
      const newStringTags = newValue.filter((v): v is string => typeof v === 'string');
      for (const name of newStringTags) {
        const trimmed = name.trim();
        if (!trimmed) continue;
        const created = await DocumentService.createDocumentTag(trimmed, 'user');
        latest = await DocumentService.attachDocumentTags(document.id, [created.id]);
        mutated = true;
      }

      if (mutated) onChanged(latest);
    } catch (err) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? (err as Error).message
          : String(err),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Autocomplete<DocumentTag, true, false, true>
        multiple
        freeSolo
        options={availableTags}
        value={currentTags}
        disabled={!canEdit || saving}
        getOptionLabel={(option) =>
          typeof option === 'string' ? option : option.name
        }
        isOptionEqualToValue={(a, b) => a.id === b.id}
        getOptionDisabled={(option) =>
          isInstitutionBlocked(option) || isOwnerOnlyBlocked(option)
        }
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          return filtered;
        }}
        renderTags={(tagValue, getTagProps) =>
          tagValue.map((option, index) => {
            const { key, onDelete, ...tagProps } = getTagProps({ index });
            const isPersonal =
              typeof option !== 'string' && option.is_personal === true;
            // Personal assignments render as outlined/primary chips; a non-owner
            // can only remove those (shared chips lose their delete affordance).
            const removable = isOwner || isPersonal;
            return (
              <Chip
                key={key}
                {...tagProps}
                label={typeof option === 'string' ? option : option.name}
                size="small"
                variant={isPersonal ? 'outlined' : 'filled'}
                color={isPersonal ? 'primary' : 'default'}
                onDelete={canEdit && removable ? onDelete : undefined}
              />
            );
          })
        }
        renderOption={(props, option) => {
          // MUI 5.18 injects `key` into `props`; spreading it warns, so pull it out.
          const { key, ...optionProps } = props as typeof props & {
            key?: React.Key;
          };
          return (
            <li key={key} {...optionProps}>
              <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                <span>
                  {typeof option === 'string' ? option : option.name}
                </span>
                {isInstitutionBlocked(option) && (
                  <Typography variant="caption" color="text.secondary">
                    {t(
                      'components.documentLibrary.tagEditor.institutionTagDisabled',
                      'Nur für institutionsweit geteilte Dokumente',
                    )}
                  </Typography>
                )}
                {isOwnerOnlyBlocked(option) &&
                  !isInstitutionBlocked(option) && (
                    <Typography variant="caption" color="text.secondary">
                      {t(
                        'components.documentLibrary.tagEditor.ownerOnlyTagDisabled',
                        'Geteilte Tags kann nur der Eigentümer ändern',
                      )}
                    </Typography>
                  )}
              </Box>
            </li>
          );
        }}
        onChange={handleChange}
        renderInput={(params) => (
          <TextField
            {...params}
            label={t('components.documentLibrary.tagEditor.label', 'Tags')}
            size="small"
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <>
                  {saving && <CircularProgress size={16} />}
                  {params.InputProps.endAdornment}
                </>
              ),
            }}
          />
        )}
      />
      {canEdit && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ mt: 0.5, display: 'block' }}
        >
          {t(
            'components.documentLibrary.tagEditor.createHint',
            'Neuen Tag erstellen: einfach tippen und mit Enter bestätigen.',
          )}
        </Typography>
      )}
      {error && (
        <Typography color="error" variant="caption" sx={{ mt: 0.5, display: 'block' }}>
          {error}
        </Typography>
      )}
    </>
  );
};

export default DocumentTagEditor;
