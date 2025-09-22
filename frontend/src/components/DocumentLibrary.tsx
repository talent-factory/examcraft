import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Grid,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  LinearProgress,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider
} from '@mui/material';
import {
  Description,
  PictureAsPdf,
  TextSnippet,
  Code,
  MoreVert,
  Visibility,
  Delete,
  Download,
  Psychology,
  Timeline,
  CheckCircle,
  Error,
  Schedule,
  CloudUpload
} from '@mui/icons-material';
import { DocumentService } from '../services/DocumentService';
import { Document, DocumentStatus } from '../types/document';

interface DocumentLibraryProps {
  onCreateRAGExam?: (documentIds: number[]) => void;
  refreshTrigger?: number;
}

const DocumentLibrary: React.FC<DocumentLibraryProps> = ({ 
  onCreateRAGExam, 
  refreshTrigger 
}) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocuments, setSelectedDocuments] = useState<number[]>([]);
  const [menuAnchor, setMenuAnchor] = useState<{ element: HTMLElement; documentId: number } | null>(null);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; document: Document | null }>({
    open: false,
    document: null
  });
  const [previewDialog, setPreviewDialog] = useState<{ open: boolean; document: Document | null }>({
    open: false,
    document: null
  });

  useEffect(() => {
    loadDocuments();
  }, [refreshTrigger]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const docs = await DocumentService.getDocuments();
      setDocuments(docs);
    } catch (err) {
      setError(err && typeof err === 'object' && 'message' in err ? (err as Error).message : 'Fehler beim Laden der Dokumente');
    } finally {
      setLoading(false);
    }
  };

  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes('pdf')) return <PictureAsPdf color="error" />;
    if (mimeType.includes('text')) return <TextSnippet color="info" />;
    if (mimeType.includes('word') || mimeType.includes('document')) return <Description color="primary" />;
    if (mimeType.includes('markdown')) return <Code color="success" />;
    return <Description />;
  };

  const getStatusChip = (status: DocumentStatus) => {
    switch (status) {
      case DocumentStatus.UPLOADED:
        return <Chip icon={<CloudUpload />} label="Hochgeladen" color="default" size="small" />;
      case DocumentStatus.PROCESSING:
        return <Chip icon={<Schedule />} label="Verarbeitung..." color="warning" size="small" />;
      case DocumentStatus.PROCESSED:
        return <Chip icon={<CheckCircle />} label="Verarbeitet" color="success" size="small" />;
      case DocumentStatus.ERROR:
        return <Chip icon={<Error />} label="Fehler" color="error" size="small" />;
      default:
        return <Chip label="Unbekannt" color="default" size="small" />;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('de-DE', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleDocumentSelect = (documentId: number) => {
    setSelectedDocuments(prev => 
      prev.includes(documentId)
        ? prev.filter(id => id !== documentId)
        : [...prev, documentId]
    );
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, documentId: number) => {
    setMenuAnchor({ element: event.currentTarget, documentId });
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handlePreview = (document: Document) => {
    setPreviewDialog({ open: true, document });
    handleMenuClose();
  };

  const handleDelete = (document: Document) => {
    setDeleteDialog({ open: true, document });
    handleMenuClose();
  };

  const confirmDelete = async () => {
    if (!deleteDialog.document) return;
    
    try {
      await DocumentService.deleteDocument(deleteDialog.document.id);
      setDocuments(prev => prev.filter(doc => doc.id !== deleteDialog.document!.id));
      setSelectedDocuments(prev => prev.filter(id => id !== deleteDialog.document!.id));
      setDeleteDialog({ open: false, document: null });
    } catch (err) {
      setError(err && typeof err === 'object' && 'message' in err ? (err as Error).message : 'Fehler beim Löschen');
    }
  };

  const handleDownload = async (document: Document) => {
    try {
      await DocumentService.downloadDocument(document.id, document.filename);
      handleMenuClose();
    } catch (err) {
      setError(err && typeof err === 'object' && 'message' in err ? (err as Error).message : 'Fehler beim Download');
    }
  };

  const handleCreateRAGExam = () => {
    if (onCreateRAGExam && selectedDocuments.length > 0) {
      onCreateRAGExam(selectedDocuments);
    }
  };

  const processedDocuments = documents.filter(doc => doc.status === DocumentStatus.PROCESSED);
  const canCreateRAGExam = selectedDocuments.length > 0 && 
    selectedDocuments.every(id => {
      const doc = documents.find(d => d.id === id);
      return doc?.status === DocumentStatus.PROCESSED && doc?.has_vectors;
    });

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Dokumentenbibliothek ({documents.length} Dokumente)
        </Typography>
        
        {selectedDocuments.length > 0 && (
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              {selectedDocuments.length} ausgewählt
            </Typography>
            <Button
              variant="contained"
              startIcon={<Psychology />}
              onClick={handleCreateRAGExam}
              disabled={!canCreateRAGExam}
              size="small"
            >
              RAG-Prüfung erstellen
            </Button>
          </Box>
        )}
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Statistics */}
      <Box sx={{ mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" color="primary">
                  {documents.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Gesamt
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" color="success.main">
                  {processedDocuments.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Verarbeitet
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" color="info.main">
                  {documents.filter(doc => doc.has_vectors).length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Mit Vektoren
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" color="warning.main">
                  {documents.filter(doc => doc.status === DocumentStatus.PROCESSING).length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  In Bearbeitung
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Document Grid */}
      {documents.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Description sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Keine Dokumente vorhanden
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Laden Sie Dokumente hoch, um mit der RAG-basierten Prüfungserstellung zu beginnen.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={2}>
          {documents.map((document) => (
            <Grid item xs={12} sm={6} md={4} key={document.id}>
              <Card 
                sx={{ 
                  height: '100%',
                  cursor: 'pointer',
                  border: selectedDocuments.includes(document.id) ? 2 : 1,
                  borderColor: selectedDocuments.includes(document.id) ? 'primary.main' : 'divider',
                  '&:hover': {
                    boxShadow: 4
                  }
                }}
                onClick={() => handleDocumentSelect(document.id)}
              >
                <CardContent>
                  {/* File Icon and Status */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getFileIcon(document.mime_type)}
                      {document.has_vectors && (
                        <Tooltip title="Vector Embeddings verfügbar">
                          <Timeline color="success" fontSize="small" />
                        </Tooltip>
                      )}
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMenuOpen(e, document.id);
                      }}
                    >
                      <MoreVert />
                    </IconButton>
                  </Box>

                  {/* Filename */}
                  <Typography variant="subtitle1" noWrap title={document.filename}>
                    {document.filename}
                  </Typography>

                  {/* Status */}
                  <Box sx={{ mb: 2 }}>
                    {getStatusChip(document.status)}
                  </Box>

                  {/* Processing Progress */}
                  {document.status === DocumentStatus.PROCESSING && (
                    <Box sx={{ mb: 2 }}>
                      <LinearProgress />
                      <Typography variant="caption" color="text.secondary">
                        Verarbeitung läuft...
                      </Typography>
                    </Box>
                  )}

                  {/* Metadata */}
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      Größe: {formatFileSize(document.file_size || 0)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Hochgeladen: {formatDate(document.created_at)}
                    </Typography>
                    {document.processed_at && (
                      <Typography variant="caption" color="text.secondary">
                        Verarbeitet: {formatDate(document.processed_at)}
                      </Typography>
                    )}
                    {document.metadata?.total_chunks && (
                      <Typography variant="caption" color="text.secondary">
                        Chunks: {document.metadata.total_chunks}
                      </Typography>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor?.element}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          const doc = documents.find(d => d.id === menuAnchor?.documentId);
          if (doc) handlePreview(doc);
        }}>
          <ListItemIcon>
            <Visibility fontSize="small" />
          </ListItemIcon>
          <ListItemText>Vorschau</ListItemText>
        </MenuItem>
        
        <MenuItem onClick={() => {
          const doc = documents.find(d => d.id === menuAnchor?.documentId);
          if (doc) handleDownload(doc);
        }}>
          <ListItemIcon>
            <Download fontSize="small" />
          </ListItemIcon>
          <ListItemText>Download</ListItemText>
        </MenuItem>
        
        <Divider />
        
        <MenuItem 
          onClick={() => {
            const doc = documents.find(d => d.id === menuAnchor?.documentId);
            if (doc) handleDelete(doc);
          }}
          sx={{ color: 'error.main' }}
        >
          <ListItemIcon>
            <Delete fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText>Löschen</ListItemText>
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, document: null })}
      >
        <DialogTitle>Dokument löschen</DialogTitle>
        <DialogContent>
          <Typography>
            Möchten Sie das Dokument "{deleteDialog.document?.filename}" wirklich löschen?
            Diese Aktion kann nicht rückgängig gemacht werden.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, document: null })}>
            Abbrechen
          </Button>
          <Button onClick={confirmDelete} color="error" variant="contained">
            Löschen
          </Button>
        </DialogActions>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog
        open={previewDialog.open}
        onClose={() => setPreviewDialog({ open: false, document: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Dokument-Vorschau: {previewDialog.document?.filename}
        </DialogTitle>
        <DialogContent>
          {previewDialog.document && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Metadaten
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>Dateigröße:</strong> {formatFileSize(previewDialog.document.file_size || 0)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>MIME-Type:</strong> {previewDialog.document.mime_type}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>Status:</strong> {previewDialog.document.status}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>Vektoren:</strong> {previewDialog.document.has_vectors ? 'Ja' : 'Nein'}
                  </Typography>
                </Grid>
              </Grid>
              
              {previewDialog.document.metadata && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Verarbeitungsdetails
                  </Typography>
                  <pre style={{ fontSize: '0.75rem', overflow: 'auto' }}>
                    {JSON.stringify(previewDialog.document.metadata, null, 2)}
                  </pre>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialog({ open: false, document: null })}>
            Schließen
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DocumentLibrary;
