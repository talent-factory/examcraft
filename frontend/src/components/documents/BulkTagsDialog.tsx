import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Box,
  CircularProgress,
} from '@mui/material';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import { useTranslation } from 'react-i18next';
import { DocumentTag } from '../../types/document';

interface BulkTagsDialogProps {
  open: boolean;
  availableTags: DocumentTag[];
  saving?: boolean;
  onClose: () => void;
  onApply: (mode: 'add' | 'remove', tagIds: number[]) => void;
}

/**
 * Dialog for bulk tag add/remove across selected documents (TF-355 Phase 3).
 * Lets the user pick add vs. remove mode plus which existing tags to act on.
 */
const BulkTagsDialog: React.FC<BulkTagsDialogProps> = ({
  open,
  availableTags,
  saving = false,
  onClose,
  onApply,
}) => {
  const { t } = useTranslation();
  const [mode, setMode] = useState<'add' | 'remove'>('add');
  const [selectedTags, setSelectedTags] = useState<DocumentTag[]>([]);

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const handleApply = () => {
    onApply(mode, selectedTags.map((tag) => tag.id));
  };

  // Reset local state when the dialog opens
  React.useEffect(() => {
    if (open) {
      setMode('add');
      setSelectedTags([]);
    }
  }, [open]);

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>
        {t('components.documentLibrary.bulk.tagsDialogTitle', 'Tags bearbeiten')}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2, mt: 1 }}>
          <FormControl component="fieldset">
            <FormLabel component="legend">
              {t('components.documentLibrary.bulk.tagsMode', 'Aktion')}
            </FormLabel>
            <RadioGroup
              row
              value={mode}
              onChange={(e) => setMode(e.target.value as 'add' | 'remove')}
            >
              <FormControlLabel
                value="add"
                control={<Radio />}
                disabled={saving}
                label={t('components.documentLibrary.bulk.tagsAdd', 'Hinzufügen')}
              />
              <FormControlLabel
                value="remove"
                control={<Radio />}
                disabled={saving}
                label={t('components.documentLibrary.bulk.tagsRemove', 'Entfernen')}
              />
            </RadioGroup>
          </FormControl>
        </Box>

        <Autocomplete
          multiple
          options={availableTags}
          value={selectedTags}
          disabled={saving}
          getOptionLabel={(option) => option.name}
          isOptionEqualToValue={(a, b) => a.id === b.id}
          onChange={(_event, newValue) => setSelectedTags(newValue)}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t('components.documentLibrary.bulk.tagsSelect', 'Tags auswählen')}
              size="small"
            />
          )}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={saving}>
          {t('components.documentLibrary.cancel', 'Abbrechen')}
        </Button>
        <Button
          variant="contained"
          onClick={handleApply}
          disabled={saving || selectedTags.length === 0}
        >
          {saving ? (
            <CircularProgress size={20} />
          ) : (
            t('components.documentLibrary.bulk.tagsApply', 'Anwenden')
          )}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BulkTagsDialog;
