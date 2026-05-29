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

    try {
      // 1. Handle removals: existing tags not present in newValue
      const removedTags = currentTags.filter(
        (existing) =>
          !newValue.some(
            (v) => typeof v !== 'string' && v.id === existing.id,
          ),
      );
      let nextTags = currentTags;
      for (const tag of removedTags) {
        await DocumentService.detachDocumentTag(document.id, tag.id);
        nextTags = nextTags.filter((x) => x.id !== tag.id);
      }
      if (removedTags.length) onChanged({ ...document, tags: nextTags });

      // 2. Handle additions: new DocumentTag entries not already in currentTags
      const addedTags = newValue.filter(
        (v): v is DocumentTag =>
          typeof v !== 'string' &&
          !currentTags.some((existing) => existing.id === v.id),
      );
      for (const tag of addedTags) {
        const updated = await DocumentService.attachDocumentTags(document.id, [tag.id]);
        onChanged(updated);
      }

      // 3. Handle freeSolo new tags (plain strings)
      const newStringTags = newValue.filter((v): v is string => typeof v === 'string');
      for (const name of newStringTags) {
        const trimmed = name.trim();
        if (!trimmed) continue;
        const created = await DocumentService.createDocumentTag(trimmed, 'user');
        const updated = await DocumentService.attachDocumentTags(document.id, [created.id]);
        onChanged(updated);
      }
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
