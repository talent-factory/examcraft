import React, { useState } from 'react';
import Autocomplete, { createFilterOptions } from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import { useTranslation } from 'react-i18next';
import { Document, DocumentTag } from '../../types/document';
import { DocumentService } from '../../services/DocumentService';

interface DocumentTagEditorProps {
  document: Document;
  availableTags: DocumentTag[];
  canEdit: boolean;
  onChanged: (updated: Document) => void;
}

// Allow freeSolo entries (plain strings for new tags) mixed with DocumentTag objects.
type TagOrString = DocumentTag | string;

const filter = createFilterOptions<DocumentTag>();

const DocumentTagEditor: React.FC<DocumentTagEditorProps> = ({
  document,
  availableTags,
  canEdit,
  onChanged,
}) => {
  const { t } = useTranslation();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentTags: DocumentTag[] = document.tags ?? [];

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
      const removedTags = currentTags.filter(
        (existing) =>
          !newValue.some(
            (v) => typeof v !== 'string' && v.id === existing.id,
          ),
      );
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
          !currentTags.some((existing) => existing.id === v.id),
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
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          return filtered;
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
      {error && (
        <Typography color="error" variant="caption" sx={{ mt: 0.5, display: 'block' }}>
          {error}
        </Typography>
      )}
    </>
  );
};

export default DocumentTagEditor;
