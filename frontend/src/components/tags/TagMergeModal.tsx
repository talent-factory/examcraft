import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Typography,
  Box,
  Chip,
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import { type Tag } from '../../api/tagsApi';

interface TagMergeModalProps {
  open: boolean;
  selectedTags: Tag[];
  onConfirm: (sourceIds: number[], targetId: number) => Promise<void>;
  onClose: () => void;
}

const TagMergeModal: React.FC<TagMergeModalProps> = ({
  open,
  selectedTags,
  onConfirm,
  onClose,
}) => {
  const { t } = useTranslation();
  const [targetId, setTargetId] = useState<number | ''>('');
  const [loading, setLoading] = useState(false);

  const targetTag = selectedTags.find((tag) => tag.id === targetId);
  const sourcesToArchive = selectedTags.filter((tag) => tag.id !== targetId);
  const migratedQuestions = sourcesToArchive.reduce((sum, tag) => sum + tag.usage_count, 0);

  const handleConfirm = async () => {
    if (!targetId) return;
    setLoading(true);
    try {
      await onConfirm(
        sourcesToArchive.map((tag) => tag.id),
        targetId as number
      );
      onClose();
    } catch {
      // Swallow here only to keep the modal open for a retry instead of
      // leaving an unhandled rejection — the caller's onError already
      // surfaced the failure via the parent's error state.
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t('components.tags.mergeTitle')}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {t('components.tags.mergeIntro')}
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 3 }}>
          {selectedTags.map((tag) => (
            <Chip
              key={tag.id}
              label={`#${tag.name} (${tag.usage_count})`}
              size="small"
              color="secondary"
              variant="outlined"
            />
          ))}
        </Box>
        <FormControl fullWidth>
          <InputLabel>{t('components.tags.mergeTarget')}</InputLabel>
          <Select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value as number)}
            label={t('components.tags.mergeTarget')}
          >
            {selectedTags.map((tag) => (
              <MenuItem key={tag.id} value={tag.id}>
                #{tag.name} ({t('components.tags.mergeOptionUsage', { count: tag.usage_count })})
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        {targetId && targetTag && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {migratedQuestions === 0 ? (
              <>{t('components.tags.mergeNone')} </>
            ) : (
              <>
                {t('components.tags.mergeMigrate', {
                  count: migratedQuestions,
                  target: `#${targetTag.name}`,
                })}{' '}
              </>
            )}
            {sourcesToArchive.map((tag, i) => (
              <React.Fragment key={tag.id}>
                {i > 0 && ', '}
                <strong>#{tag.name}</strong>
              </React.Fragment>
            ))}{' '}
            {t('components.tags.mergeArchiveTail', { count: sourcesToArchive.length })}
          </Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          {t('components.tags.cancel')}
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          disabled={!targetId || loading}
          color="error"
        >
          {t('components.tags.merge')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TagMergeModal;
