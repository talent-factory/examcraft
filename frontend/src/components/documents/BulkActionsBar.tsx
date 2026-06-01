import React from 'react';
import { Button, Paper, Stack, Typography } from '@mui/material';
import { Delete, Psychology } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

interface BulkActionsBarProps {
  count: number;
  canRag: boolean;
  onRagExam: () => void;
  onTags: () => void;
  onVisibility: () => void;
  onDelete: () => void;
}

/**
 * Action bar rendered above the document grid/list whenever one or more
 * documents are selected (TF-355 Phase 3, Task 4). Returns null when count=0.
 */
const BulkActionsBar: React.FC<BulkActionsBarProps> = ({
  count,
  canRag,
  onRagExam,
  onTags,
  onVisibility,
  onDelete,
}) => {
  const { t } = useTranslation();

  if (count <= 0) return null;

  return (
    <Paper variant="outlined" sx={{ p: 1, mb: 2 }}>
      <Stack direction="row" spacing={2} alignItems="center">
        <Typography variant="body2" color="text.secondary">
          {t('components.documentLibrary.bulk.selected', { count })}
        </Typography>

        <Button
          size="small"
          variant="contained"
          startIcon={<Psychology />}
          disabled={!canRag}
          onClick={onRagExam}
        >
          {t('components.documentLibrary.bulk.ragExam', 'RAG-Prüfung erstellen')}
        </Button>

        <Button size="small" variant="outlined" onClick={onTags}>
          {t('components.documentLibrary.bulk.tags', 'Tags…')}
        </Button>

        <Button size="small" variant="outlined" onClick={onVisibility}>
          {t('components.documentLibrary.bulk.visibility', 'Sichtbarkeit…')}
        </Button>

        <Button
          size="small"
          variant="outlined"
          color="error"
          startIcon={<Delete />}
          onClick={onDelete}
        >
          {t('components.documentLibrary.bulk.delete', 'Löschen')}
        </Button>
      </Stack>
    </Paper>
  );
};

export default BulkActionsBar;
