import React, { useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  LinearProgress,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Grid,
  Paper
} from '@mui/material';
import {
  CloudUpload,
  Description,
  Delete,
  Refresh,
  Schedule,
  PictureAsPdf,
  TextSnippet,
  Cancel
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useTranslation } from 'react-i18next';
import { DocumentService } from '../services/DocumentService';
import { DocumentUploadResponse, DocumentProcessingResponse } from '../types/document';

interface UploadFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error' | 'cancelled';
  progress: number;
  documentId?: number;
  error?: string;
  result?: DocumentUploadResponse;
  processingResult?: DocumentProcessingResponse;
  abortController?: AbortController;
  estimatedTimeRemaining?: number;
  processingStartTime?: number;
}

interface DocumentUploadProps {
  onUploadComplete?: (documentId: number, filename: string) => void;
  onUploadError?: (filename: string, error: string) => void;
  onAllUploadsComplete?: () => void;
  maxFiles?: number;
  acceptedFileTypes?: string[];
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadComplete,
  onUploadError,
  onAllUploadsComplete,
  maxFiles = 10,
  acceptedFileTypes = ['.pdf', '.doc', '.docx', '.txt', '.md']
}) => {
  const { t } = useTranslation();
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map(file => ({
      file,
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      status: 'pending',
      progress: 0
    }));

    setUploadFiles(prev => [...prev, ...newFiles].slice(0, maxFiles));
  }, [maxFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md']
    },
    maxFiles,
    multiple: true
  });

  const getFileIcon = (filename: string) => {
    const ext = filename.toLowerCase().split('.').pop();
    switch (ext) {
      case 'pdf':
        return <PictureAsPdf color="error" />;
      case 'txt':
      case 'md':
        return <TextSnippet color="info" />;
      case 'doc':
      case 'docx':
        return <Description color="primary" />;
      default:
        return <Description />;
    }
  };

  const formatTimeRemaining = (ms: number): string => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return t('components.documentUpload.timeHours', { h: hours, m: minutes % 60 });
    } else if (minutes > 0) {
      return t('components.documentUpload.timeMinutes', { m: minutes, s: seconds % 60 });
    } else {
      return t('components.documentUpload.timeSeconds', { s: seconds });
    }
  };

  const getStatusChip = (file: UploadFile) => {
    switch (file.status) {
      case 'pending':
        return <Chip label={t('components.documentUpload.statusPending')} color="default" size="small" />;
      case 'uploading':
        return <Chip label={t('components.documentUpload.statusUploading')} color="info" size="small" />;
      case 'processing':
        const timeLabel = file.estimatedTimeRemaining
          ? t('components.documentUpload.statusProcessingTime', { time: formatTimeRemaining(file.estimatedTimeRemaining) })
          : t('components.documentUpload.statusProcessing');
        return <Chip label={timeLabel} color="warning" size="small" />;
      case 'completed':
        return <Chip label={t('components.documentUpload.statusCompleted')} color="success" size="small" />;
      case 'cancelled':
        return <Chip label={t('components.documentUpload.statusCancelled')} color="default" size="small" />;
      case 'error':
        return <Chip label={t('components.documentUpload.statusError')} color="error" size="small" />;
      default:
        return <Chip label={t('components.documentUpload.statusUnknown')} color="default" size="small" />;
    }
  };

  const removeFile = (fileId: string) => {
    // Cancel ongoing upload/processing if exists
    const file = uploadFiles.find(f => f.id === fileId);
    if (file?.abortController) {
      file.abortController.abort();
    }
    setUploadFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const cancelFile = (fileId: string) => {
    const file = uploadFiles.find(f => f.id === fileId);
    if (file?.abortController) {
      file.abortController.abort();
      setUploadFiles(prev => prev.map(f =>
        f.id === fileId
          ? { ...f, status: 'cancelled', error: 'Upload cancelled by user' }
          : f
      ));
    }
  };

  const retryFile = async (fileId: string) => {
    const file = uploadFiles.find(f => f.id === fileId);
    if (!file) return;

    setUploadFiles(prev => prev.map(f =>
      f.id === fileId
        ? { ...f, status: 'pending', progress: 0, error: undefined }
        : f
    ));

    await uploadSingleFile(file.file, fileId);
  };

  const uploadSingleFile = async (file: File, fileId: string) => {
    const abortController = new AbortController();

    try {
      // Update status to uploading with abort controller
      setUploadFiles(prev => prev.map(f =>
        f.id === fileId
          ? { ...f, status: 'uploading', progress: 10, abortController }
          : f
      ));

      // Upload file
      const uploadResult = await DocumentService.uploadDocument(file);

      // Check if cancelled
      if (abortController.signal.aborted) {
        throw new Error('Upload cancelled');
      }

      // Update with upload result
      setUploadFiles(prev => prev.map(f =>
        f.id === fileId
          ? {
              ...f,
              status: 'processing',
              progress: 50,
              documentId: uploadResult.document_id,
              result: uploadResult,
              processingStartTime: Date.now()
            }
          : f
      ));

      // Start processing (asynchron im Backend) - NICHT WARTEN!
      await DocumentService.processDocument(uploadResult.document_id, true);

      // Check if cancelled
      if (abortController.signal.aborted) {
        throw new Error('Processing cancelled');
      }

      // SOFORT als "completed" markieren - Processing läuft im Hintergrund!
      // User kann sofort weiterarbeiten, während das Dokument verarbeitet wird
      setUploadFiles(prev => prev.map(f =>
        f.id === fileId
          ? {
              ...f,
              status: 'completed',
              progress: 100,
              processingResult: {
                message: 'Document uploaded and processing started in background',
                document_id: uploadResult.document_id,
                status: 'processing'
              },
              abortController: undefined
            }
          : f
      ));

      onUploadComplete?.(uploadResult.document_id, file.name);

    } catch (error) {
      // Check if it was a cancellation
      if (abortController.signal.aborted || (error && typeof error === 'object' && 'message' in error && (error as Error).message.includes('cancel'))) {
        setUploadFiles(prev => prev.map(f =>
          f.id === fileId
            ? { ...f, status: 'cancelled', error: 'Upload cancelled by user', abortController: undefined }
            : f
        ));
        return;
      }

      const errorMessage = error && typeof error === 'object' && 'message' in error ? (error as Error).message : 'Upload failed';

      setUploadFiles(prev => prev.map(f =>
        f.id === fileId
          ? { ...f, status: 'error', error: errorMessage, abortController: undefined }
          : f
      ));

      onUploadError?.(file.name, errorMessage);
    }
  };

  const startUpload = async () => {
    if (uploadFiles.length === 0) return;

    setIsUploading(true);

    const pendingFiles = uploadFiles.filter(f => f.status === 'pending' || f.status === 'error');

    // Upload files sequentially to avoid overwhelming the server
    for (const uploadFile of pendingFiles) {
      await uploadSingleFile(uploadFile.file, uploadFile.id);
    }

    setIsUploading(false);
    setShowResults(true);
    onAllUploadsComplete?.();
  };

  const clearAll = () => {
    setUploadFiles([]);
    setShowResults(false);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const completedCount = uploadFiles.filter(f => f.status === 'completed').length;
  const errorCount = uploadFiles.filter(f => f.status === 'error').length;
  const totalCount = uploadFiles.length;

  return (
    <Box>
      {/* Upload Area */}
      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          textAlign: 'center',
          cursor: 'pointer',
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.300',
          bgcolor: isDragActive ? 'primary.light' : 'background.paper',
          transition: 'all 0.3s ease',
          '&:hover': {
            borderColor: 'primary.main',
            bgcolor: 'primary.light'
          }
        }}
      >
        <input {...getInputProps()} />
        <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive ? t('components.documentUpload.dropActive') : t('components.documentUpload.dropTitle')}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t('components.documentUpload.dropHint')}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t('components.documentUpload.dropFormats', { formats: acceptedFileTypes.join(', '), max: maxFiles })}
        </Typography>
      </Paper>

      {/* Upload Queue */}
      {uploadFiles.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                {t('components.documentUpload.queueTitle', { count: uploadFiles.length })}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  onClick={startUpload}
                  disabled={isUploading || uploadFiles.every(f => f.status === 'completed')}
                  startIcon={<CloudUpload />}
                >
                  {isUploading ? t('components.documentUpload.uploading') : t('components.documentUpload.startUpload')}
                </Button>
                <Button
                  variant="outlined"
                  onClick={clearAll}
                  disabled={isUploading}
                >
                  {t('components.documentUpload.removeAll')}
                </Button>
              </Box>
            </Box>

            <List>
              {uploadFiles.map((uploadFile) => (
                <ListItem key={uploadFile.id} divider>
                  <ListItemIcon>
                    {getFileIcon(uploadFile.file.name)}
                  </ListItemIcon>
                  <ListItemText
                    primary={uploadFile.file.name}
                    secondary={
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          {formatFileSize(uploadFile.file.size)}
                        </Typography>
                        {uploadFile.progress > 0 && uploadFile.status !== 'completed' && (
                          <LinearProgress
                            variant="determinate"
                            value={uploadFile.progress}
                            sx={{ mt: 1 }}
                          />
                        )}
                        {uploadFile.error && (
                          <Typography variant="caption" color="error" sx={{ display: 'block', mt: 1 }}>
                            {uploadFile.error}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getStatusChip(uploadFile)}
                      {(uploadFile.status === 'uploading' || uploadFile.status === 'processing') && (
                        <IconButton
                          size="small"
                          onClick={() => cancelFile(uploadFile.id)}
                          title={t('components.documentUpload.cancelUpload')}
                          color="warning"
                        >
                          <Cancel />
                        </IconButton>
                      )}
                      {uploadFile.status === 'error' && (
                        <IconButton
                          size="small"
                          onClick={() => retryFile(uploadFile.id)}
                          disabled={isUploading}
                          title={t('components.documentUpload.retry')}
                        >
                          <Refresh />
                        </IconButton>
                      )}
                      {(uploadFile.status === 'pending' || uploadFile.status === 'error' || uploadFile.status === 'cancelled') && (
                        <IconButton
                          size="small"
                          onClick={() => removeFile(uploadFile.id)}
                          disabled={isUploading}
                          title={t('components.documentUpload.remove')}
                        >
                          <Delete />
                        </IconButton>
                      )}
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Results Summary */}
      {showResults && totalCount > 0 && (
        <Alert
          severity={errorCount > 0 ? 'warning' : 'success'}
          sx={{ mt: 2 }}
          onClose={() => setShowResults(false)}
        >
          <Typography variant="subtitle2">
            {t('components.documentUpload.uploadComplete')}
          </Typography>
          <Typography variant="body2">
            {t('components.documentUpload.uploadSummary', { completed: completedCount, total: totalCount })}
            {errorCount > 0 && ` • ${t('components.documentUpload.errorCount', { count: errorCount })}`}
          </Typography>
        </Alert>
      )}

      {/* Processing Info */}
      {uploadFiles.some(f => f.status === 'processing') && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <Schedule sx={{ verticalAlign: 'middle', mr: 1 }} />
            {t('components.documentUpload.processingInfo')}
          </Typography>
        </Alert>
      )}

      {/* Upload Statistics */}
      {totalCount > 0 && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              {t('components.documentUpload.statsTitle')}
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    {totalCount}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t('components.documentUpload.statsTotal')}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="success.main">
                    {completedCount}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t('components.documentUpload.statsSuccess')}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="warning.main">
                    {uploadFiles.filter(f => f.status === 'processing').length}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t('components.documentUpload.statsProcessing')}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="error.main">
                    {errorCount}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t('components.documentUpload.statsErrors')}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default DocumentUpload;
