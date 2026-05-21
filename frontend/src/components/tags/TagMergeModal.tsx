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
  const [targetId, setTargetId] = useState<number | ''>('');
  const [loading, setLoading] = useState(false);

  const targetTag = selectedTags.find((t) => t.id === targetId);
  const sourcesToArchive = selectedTags.filter((t) => t.id !== targetId);
  const migratedQuestions = sourcesToArchive.reduce((sum, t) => sum + t.usage_count, 0);

  const handleConfirm = async () => {
    if (!targetId) return;
    setLoading(true);
    try {
      await onConfirm(
        sourcesToArchive.map((t) => t.id),
        targetId as number
      );
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Tags zusammenführen</DialogTitle>
      <DialogContent>
        <Typography variant="body2" sx={{ mb: 2 }}>
          Welcher Tag soll übrig bleiben? Die anderen werden archiviert.
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 3 }}>
          {selectedTags.map((t) => (
            <Chip
              key={t.id}
              label={`#${t.name} (${t.usage_count})`}
              size="small"
              color="secondary"
              variant="outlined"
            />
          ))}
        </Box>
        <FormControl fullWidth>
          <InputLabel>Ziel-Tag (bleibt erhalten)</InputLabel>
          <Select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value as number)}
            label="Ziel-Tag (bleibt erhalten)"
          >
            {selectedTags.map((t) => (
              <MenuItem key={t.id} value={t.id}>
                #{t.name} ({t.usage_count} Fragen)
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        {targetId && targetTag && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {migratedQuestions === 0 ? (
              'Keine Fragen werden migriert. '
            ) : migratedQuestions === 1 ? (
              <>1 Frage wird auf <strong>#{targetTag.name}</strong> migriert. </>
            ) : (
              <>{migratedQuestions} Fragen werden auf <strong>#{targetTag.name}</strong> migriert. </>
            )}
            {sourcesToArchive.map((t, i) => (
              <React.Fragment key={t.id}>
                {i > 0 && ', '}
                <strong>#{t.name}</strong>
              </React.Fragment>
            ))}{' '}
            {sourcesToArchive.length === 1 ? 'wird' : 'werden'} archiviert.
          </Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Abbrechen
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          disabled={!targetId || loading}
          color="error"
        >
          Zusammenführen
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TagMergeModal;
