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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Paper
} from '@mui/material';
import {
  CloudUpload,
  Description,
  CheckCircle,
  Error as ErrorIcon,
  Delete,
  Refresh,
  Schedule,
  PictureAsPdf,
  TextSnippet,
  Code,
  Cancel
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
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
      return `~${hours}h ${minutes % 60}m verbleibend`;
    } else if (minutes > 0) {
      return `~${minutes}m ${seconds % 60}s verbleibend`;
    } else {
      return `~${seconds}s verbleibend`;
    }
  };

  const getStatusChip = (file: UploadFile) => {
    switch (file.status) {
      case 'pending':
        return <Chip label="Wartend" color="default" size="small" />;
      case 'uploading':
        return <Chip label="Upload..." color="info" size="small" />;
      case 'processing':
        const timeLabel = file.estimatedTimeRemaining
          ? `Verarbeitung... (${formatTimeRemaining(file.estimatedTimeRemaining)})`
          : 'Verarbeitung...';
        return <Chip label={timeLabel} color="warning" size="small" />;
      case 'completed':
        return <Chip label="Abgeschlossen" color="success" size="small" />;
      case 'cancelled':
        return <Chip label="Abgebrochen" color="default" size="small" />;
      case 'error':
        return <Chip label="Fehler" color="error" size="small" />;
      default:
        return <Chip label="Unbekannt" color="default" size="small" />;
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

      // ✅ SOFORT als "completed" markieren - Processing läuft im Hintergrund!
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

  const waitForDocumentProcessing = async (
    documentId: number,
    fileId: string,
    abortController: AbortController,
    maxWaitTime: number = 1800000 // 30 Minuten für große Dokumente (300+ Seiten)
  ) => {
    /**
     * Warte auf Dokumentenverarbeitung durch Polling des Status
     * maxWaitTime: Maximale Wartezeit in ms (default: 30 Minuten)
     */
    const startTime = Date.now();
    const pollInterval = 3000; // Poll alle 3 Sekunden
    const warningThreshold = maxWaitTime * 0.8; // Warnung bei 80% der Zeit

    while (Date.now() - startTime < maxWaitTime) {
      // Check if cancelled
      if (abortController.signal.aborted) {
        throw new Error('Processing cancelled by user');
      }

      try {
        const status = await DocumentService.getProcessingStatus(documentId);
        const elapsedTime = Date.now() - startTime;
        const estimatedTimeRemaining = Math.max(0, maxWaitTime - elapsedTime);

        // Calculate progress (50% → 95%)
        const processingProgress = Math.min(95, 50 + (elapsedTime / maxWaitTime) * 45);

        // Update progress with estimated time
        setUploadFiles(prev => prev.map(f =>
          f.id === fileId
            ? {
                ...f,
                progress: processingProgress,
                estimatedTimeRemaining: estimatedTimeRemaining
              }
            : f
        ));

        // Show warning if approaching timeout
        if (elapsedTime > warningThreshold && elapsedTime < warningThreshold + pollInterval) {
          console.warn(`Document processing taking longer than expected. ${Math.round(estimatedTimeRemaining / 1000)}s remaining.`);
        }

        if (status.status === 'Verarbeitet' || status.status === 'processed') {
          return; // Verarbeitung abgeschlossen
        }

        if (status.status === 'Fehler' || status.status === 'error') {
          throw new Error(`Document processing failed: ${status.status}`);
        }

        // Warte vor nächstem Poll
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      } catch (error) {
        // Check if cancelled
        if (abortController.signal.aborted) {
          throw new Error('Processing cancelled by user');
        }

        console.error('Error checking document status:', error);
        // Weiter versuchen
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }

    throw new Error(`Document processing timeout after ${maxWaitTime / 60000} minutes. Please try again or contact support for large documents.`);
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
          {isDragActive ? 'Dateien hier ablegen...' : 'Dokumente hochladen'}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Ziehen Sie Dateien hierher oder klicken Sie zum Auswählen
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Unterstützte Formate: {acceptedFileTypes.join(', ')} • Max. {maxFiles} Dateien
        </Typography>
      </Paper>

      {/* Upload Queue */}
      {uploadFiles.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Upload-Warteschlange ({uploadFiles.length})
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  onClick={startUpload}
                  disabled={isUploading || uploadFiles.every(f => f.status === 'completed')}
                  startIcon={<CloudUpload />}
                >
                  {isUploading ? 'Uploading...' : 'Upload starten'}
                </Button>
                <Button
                  variant="outlined"
                  onClick={clearAll}
                  disabled={isUploading}
                >
                  Alle entfernen
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
                          title="Upload abbrechen"
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
                          title="Erneut versuchen"
                        >
                          <Refresh />
                        </IconButton>
                      )}
                      {(uploadFile.status === 'pending' || uploadFile.status === 'error' || uploadFile.status === 'cancelled') && (
                        <IconButton
                          size="small"
                          onClick={() => removeFile(uploadFile.id)}
                          disabled={isUploading}
                          title="Entfernen"
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
            Upload abgeschlossen
          </Typography>
          <Typography variant="body2">
            {completedCount} von {totalCount} Dateien erfolgreich hochgeladen und verarbeitet
            {errorCount > 0 && ` • ${errorCount} Fehler`}
          </Typography>
        </Alert>
      )}

      {/* Processing Info */}
      {uploadFiles.some(f => f.status === 'processing') && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <Schedule sx={{ verticalAlign: 'middle', mr: 1 }} />
            Dokumente werden verarbeitet und für RAG-Prüfungen vorbereitet. 
            Dies kann je nach Dateigröße einige Minuten dauern.
          </Typography>
        </Alert>
      )}

      {/* Upload Statistics */}
      {totalCount > 0 && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Upload-Statistiken
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    {totalCount}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Gesamt
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="success.main">
                    {completedCount}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Erfolgreich
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="warning.main">
                    {uploadFiles.filter(f => f.status === 'processing').length}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Verarbeitung
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="error.main">
                    {errorCount}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Fehler
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
