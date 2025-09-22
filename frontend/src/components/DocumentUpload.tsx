import React, { useCallback, useState } from 'react';
import {
  Box,
  Typography,
  Button,
  LinearProgress,
  Alert,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Chip
} from '@mui/material';
import {
  CloudUpload,
  InsertDriveFile,
  CheckCircle,
  Error,
  Delete,
  Description
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  status: 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
  documentId?: number;
}

interface DocumentUploadProps {
  onUploadComplete?: (documentId: number, filename: string) => void;
  onUploadError?: (filename: string, error: string) => void;
  maxFiles?: number;
  disabled?: boolean;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadComplete,
  onUploadError,
  maxFiles = 10,
  disabled = false
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const uploadFile = async (file: File): Promise<void> => {
    const fileId = `${file.name}-${Date.now()}`;
    
    // Add file to list with uploading status
    const uploadFile: UploadedFile = {
      id: fileId,
      name: file.name,
      size: file.size,
      status: 'uploading',
      progress: 0
    };
    
    setFiles(prev => [...prev, uploadFile]);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();
      
      // Update file status to success
      setFiles(prev => prev.map(f => 
        f.id === fileId 
          ? { ...f, status: 'success', progress: 100, documentId: result.document_id }
          : f
      ));

      // Notify parent component
      if (onUploadComplete) {
        onUploadComplete(result.document_id, file.name);
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      // Update file status to error
      setFiles(prev => prev.map(f => 
        f.id === fileId 
          ? { ...f, status: 'error', progress: 0, error: errorMessage }
          : f
      ));

      // Notify parent component
      if (onUploadError) {
        onUploadError(file.name, errorMessage);
      }
    }
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setGlobalError(null);

    // Check file count limit
    if (files.length + acceptedFiles.length > maxFiles) {
      setGlobalError(`Maximum ${maxFiles} files allowed`);
      return;
    }

    // Upload each file
    for (const file of acceptedFiles) {
      await uploadFile(file);
    }
  }, [files.length, maxFiles]);

  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md']
    },
    disabled,
    maxFiles: maxFiles - files.length
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'uploading':
        return <CloudUpload color="primary" />;
      case 'success':
        return <CheckCircle color="success" />;
      case 'error':
        return <Error color="error" />;
      default:
        return <InsertDriveFile />;
    }
  };

  const getStatusColor = (status: UploadedFile['status']) => {
    switch (status) {
      case 'uploading':
        return 'primary';
      case 'success':
        return 'success';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      {/* Upload Area */}
      <Card 
        sx={{ 
          mb: 2,
          border: isDragActive ? '2px dashed #1976d2' : '2px dashed #ccc',
          bgcolor: isDragActive ? 'action.hover' : 'background.paper',
          transition: 'all 0.2s ease'
        }}
      >
        <CardContent>
          <Box
            {...getRootProps()}
            sx={{
              textAlign: 'center',
              py: 4,
              cursor: disabled ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.5 : 1
            }}
          >
            <input {...getInputProps()} />
            <Description sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            
            <Typography variant="h6" gutterBottom>
              {isDragActive
                ? 'Dateien hier ablegen...'
                : 'Dokumente hochladen'
              }
            </Typography>
            
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Ziehen Sie Dateien hierher oder klicken Sie zum Auswählen
            </Typography>
            
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, mb: 2 }}>
              {['PDF', 'DOC', 'DOCX', 'TXT', 'MD'].map(format => (
                <Chip key={format} label={format} size="small" variant="outlined" />
              ))}
            </Box>
            
            <Button
              variant="contained"
              startIcon={<CloudUpload />}
              disabled={disabled}
            >
              Dateien auswählen
            </Button>
            
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              Max. {maxFiles} Dateien, bis zu 50MB pro Datei
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Global Error */}
      {globalError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setGlobalError(null)}>
          {globalError}
        </Alert>
      )}

      {/* File List */}
      {files.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Hochgeladene Dateien ({files.length})
            </Typography>
            
            <List>
              {files.map((file) => (
                <ListItem key={file.id} divider>
                  <ListItemIcon>
                    {getStatusIcon(file.status)}
                  </ListItemIcon>
                  
                  <ListItemText
                    primary={file.name}
                    secondary={
                      <Box>
                        <Typography variant="caption" display="block">
                          {formatFileSize(file.size)}
                        </Typography>
                        
                        {file.status === 'uploading' && (
                          <LinearProgress 
                            variant="indeterminate" 
                            sx={{ mt: 1, width: '100%' }} 
                          />
                        )}
                        
                        {file.error && (
                          <Typography variant="caption" color="error" display="block">
                            {file.error}
                          </Typography>
                        )}
                        
                        {file.status === 'success' && file.documentId && (
                          <Typography variant="caption" color="success.main" display="block">
                            ✓ Erfolgreich hochgeladen (ID: {file.documentId})
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                  
                  <Chip 
                    label={file.status === 'uploading' ? 'Uploading...' : file.status}
                    color={getStatusColor(file.status) as any}
                    size="small"
                    sx={{ mr: 1 }}
                  />
                  
                  <IconButton 
                    edge="end" 
                    onClick={() => removeFile(file.id)}
                    size="small"
                  >
                    <Delete />
                  </IconButton>
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};
