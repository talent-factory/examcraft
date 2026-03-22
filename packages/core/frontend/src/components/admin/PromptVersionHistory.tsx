import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { ArrowBack, CheckCircle, Visibility, Restore } from '@mui/icons-material';
import { promptsApi, Prompt } from '../../api/promptsApi';
import MarkdownRenderer from '../MarkdownRenderer';

interface PromptVersionHistoryProps {
  promptName: string;
  onBack?: () => void;
}

export const PromptVersionHistory: React.FC<PromptVersionHistoryProps> = ({
  promptName,
  onBack
}) => {
  const { t, i18n } = useTranslation();
  const [versions, setVersions] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewVersion, setPreviewVersion] = useState<Prompt | null>(null);

  const loadVersions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await promptsApi.getVersionHistory(promptName);
      setVersions(data.sort((a, b) => b.version - a.version));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.promptVersionHistory.failedLoad'));
    } finally {
      setLoading(false);
    }
  }, [promptName]);

  useEffect(() => {
    loadVersions();
  }, [loadVersions]);

  const handleActivate = async (version: Prompt) => {
    try {
      await promptsApi.toggleActive(version.id, true);
      await loadVersions();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.promptVersionHistory.failedActivate'));
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString(i18n.language, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 4 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={onBack}
          sx={{ mr: 2 }}
        >
          {t('admin.promptVersionHistory.btnBack')}
        </Button>
        <Box>
          <Typography variant="h4" component="h1">
            {t('admin.promptVersionHistory.title')}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {promptName}
          </Typography>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Versions Table */}
      <TableContainer component={Paper} elevation={2}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>{t('admin.promptVersionHistory.colVersion')}</TableCell>
              <TableCell>{t('admin.promptVersionHistory.colStatus')}</TableCell>
              <TableCell>{t('admin.promptVersionHistory.colDescription')}</TableCell>
              <TableCell>{t('admin.promptVersionHistory.colCreatedAt')}</TableCell>
              <TableCell>{t('admin.promptVersionHistory.colUpdatedAt')}</TableCell>
              <TableCell align="right">{t('admin.promptVersionHistory.colActions')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {versions.map((version) => (
              <TableRow
                key={version.id}
                sx={{
                  bgcolor: version.is_active ? 'success.light' : 'inherit',
                  '&:hover': { bgcolor: version.is_active ? 'success.light' : 'action.hover' }
                }}
              >
                <TableCell>
                  <Chip
                    label={`v${version.version}`}
                    color={version.is_active ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {version.is_active ? (
                    <Chip
                      icon={<CheckCircle />}
                      label={t('admin.promptVersionHistory.statusActive')}
                      color="success"
                      size="small"
                    />
                  ) : (
                    <Chip label={t('admin.promptVersionHistory.statusInactive')} size="small" />
                  )}
                </TableCell>
                <TableCell>
                  {version.description || '-'}
                </TableCell>
                <TableCell>
                  {formatDate(version.created_at)}
                </TableCell>
                <TableCell>
                  {formatDate(version.updated_at)}
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                    <Button
                      size="small"
                      startIcon={<Visibility />}
                      onClick={() => setPreviewVersion(version)}
                    >
                      {t('admin.promptVersionHistory.btnPreview')}
                    </Button>
                    {!version.is_active && (
                      <Button
                        size="small"
                        startIcon={<Restore />}
                        onClick={() => handleActivate(version)}
                        color="primary"
                      >
                        {t('admin.promptVersionHistory.btnActivate')}
                      </Button>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {versions.length === 0 && (
        <Paper elevation={1} sx={{ p: 8, textAlign: 'center', mt: 3 }}>
          <Typography variant="h6" color="text.secondary">
            {t('admin.promptVersionHistory.empty')}
          </Typography>
        </Paper>
      )}

      {/* Preview Dialog */}
      <Dialog
        open={!!previewVersion}
        onClose={() => setPreviewVersion(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {t('admin.promptVersionHistory.previewTitle', { name: previewVersion?.name, version: previewVersion?.version })}
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              {t('admin.promptVersionHistory.previewDescriptionLabel')}
            </Typography>
            <Typography variant="body2">
              {previewVersion?.description || t('admin.promptVersionHistory.previewNoDescription')}
            </Typography>
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              {t('admin.promptVersionHistory.previewContentLabel')}
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
              <MarkdownRenderer content={previewVersion?.content || ''} />
            </Paper>
          </Box>
          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              {t('admin.promptVersionHistory.previewTagsLabel')}
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
              {previewVersion?.tags.map(tag => (
                <Chip key={tag} label={tag} size="small" />
              ))}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewVersion(null)}>{t('admin.promptVersionHistory.btnClose')}</Button>
          {previewVersion && !previewVersion.is_active && (
            <Button
              onClick={() => {
                handleActivate(previewVersion);
                setPreviewVersion(null);
              }}
              variant="contained"
            >
              {t('admin.promptVersionHistory.btnActivateVersion')}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Container>
  );
};
