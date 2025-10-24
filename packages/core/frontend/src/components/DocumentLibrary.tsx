import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
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
  Divider,
  Tabs,
  Tab,
  Paper
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
  Error as ErrorIcon,
  Schedule,
  CloudUpload,
  PlayArrow
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
  const [previewTab, setPreviewTab] = useState(0);
  const [documentContent, setDocumentContent] = useState<string | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [processingDocumentId, setProcessingDocumentId] = useState<number | null>(null);

  // Pagination state for large documents
  const [documentChunks, setDocumentChunks] = useState<any[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalChunks, setTotalChunks] = useState(0);
  const [chunksPageSize] = useState(10); // Chunks pro Seite
  const [chunksLoading, setChunksLoading] = useState(false);

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
        return <Chip icon={<ErrorIcon />} label="Fehler" color="error" size="small" />;
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

  const handlePreview = async (document: Document) => {
    setPreviewDialog({ open: true, document });
    setPreviewTab(0);
    setDocumentContent(null);
    setDocumentChunks([]);
    setCurrentPage(1);
    handleMenuClose();

    // Load content if document is processed
    if (document.status === 'processed') {
      // Try to load chunks with pagination first (for large documents)
      await loadDocumentChunksPaginated(document.id, 1);
    }
  };

  const loadDocumentChunksPaginated = async (documentId: number, page: number) => {
    try {
      setChunksLoading(true);
      const response = await DocumentService.getDocumentChunksPaginated(
        documentId,
        page,
        chunksPageSize
      );

      setDocumentChunks(response.chunks);
      setCurrentPage(response.current_page);
      setTotalPages(response.total_pages);
      setTotalChunks(response.total_chunks);
    } catch (err) {
      console.error('Failed to load document chunks:', err);
      setDocumentChunks([]);
    } finally {
      setChunksLoading(false);
    }
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

  const handleProcess = async (document: Document) => {
    try {
      setProcessingDocumentId(document.id);
      handleMenuClose();

      // Start processing (asynchron im Backend) - NICHT WARTEN!
      await DocumentService.processDocument(document.id, true);

      // ✅ SOFORT Dokumente neu laden - Processing läuft im Hintergrund!
      await loadDocuments();

      setError(null);

      // Optional: Starte Auto-Refresh für 5 Minuten (alle 5 Sekunden)
      // um den Processing-Status live zu aktualisieren
      const refreshInterval = setInterval(async () => {
        await loadDocuments();
      }, 5000); // Alle 5 Sekunden

      // Stoppe Auto-Refresh nach 5 Minuten
      setTimeout(() => {
        clearInterval(refreshInterval);
      }, 300000); // 5 Minuten

    } catch (err) {
      setError(err && typeof err === 'object' && 'message' in err ? (err as Error).message : 'Fehler beim Verarbeiten des Dokuments');
    } finally {
      setProcessingDocumentId(null);
    }
  };

  const waitForDocumentProcessing = async (
    documentId: number,
    maxWaitTime: number = 1800000 // 30 Minuten für große Dokumente
  ) => {
    const startTime = Date.now();
    const pollInterval = 3000; // Poll alle 3 Sekunden
    let pollCount = 0;

    while (Date.now() - startTime < maxWaitTime) {
      try {
        const status = await DocumentService.getProcessingStatus(documentId);

        // Reload document list every 5 polls (15 seconds) to show progress
        pollCount++;
        if (pollCount % 5 === 0) {
          await loadDocuments();
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
        console.error('Error checking document status:', error);
        // Weiter versuchen
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }

    throw new Error(`Document processing timeout after ${maxWaitTime / 60000} minutes. Please try again or contact support for large documents.`);
  };

  const handleCreateRAGExam = () => {
    if (onCreateRAGExam && selectedDocuments.length > 0) {
      onCreateRAGExam(selectedDocuments);
    }
  };

  const processedDocuments = documents?.filter(doc => doc.status === DocumentStatus.PROCESSED) || [];
  const canCreateRAGExam = selectedDocuments.length > 0 &&
    selectedDocuments.every(id => {
      const doc = documents?.find(d => d.id === id);
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
                      {document.metadata?.source === 'chat_export' && (
                        <Chip
                          label="Chat"
                          size="small"
                          color="info"
                          sx={{ height: 20, fontSize: '0.7rem' }}
                        />
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

                  {/* Document Title */}
                  <Typography variant="subtitle1" noWrap title={document.title}>
                    {document.title}
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

        {/* Process button - only show for UPLOADED documents */}
        {menuAnchor && documents.find(d => d.id === menuAnchor.documentId)?.status === DocumentStatus.UPLOADED && (
          <>
            <Divider />
            <MenuItem
              onClick={() => {
                const doc = documents.find(d => d.id === menuAnchor?.documentId);
                if (doc) handleProcess(doc);
              }}
              disabled={processingDocumentId === menuAnchor.documentId}
            >
              <ListItemIcon>
                {processingDocumentId === menuAnchor.documentId ? (
                  <CircularProgress size={20} />
                ) : (
                  <PlayArrow fontSize="small" />
                )}
              </ListItemIcon>
              <ListItemText>
                {processingDocumentId === menuAnchor.documentId ? 'Verarbeitung läuft...' : 'Verarbeiten'}
              </ListItemText>
            </MenuItem>
          </>
        )}

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
            Möchten Sie das Dokument "{deleteDialog.document?.title}" wirklich löschen?
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
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Dokument-Vorschau: {previewDialog.document?.title}
        </DialogTitle>
        <DialogContent sx={{ p: 0 }}>
          {previewDialog.document && (
            <Box sx={{ width: '100%' }}>
              {/* Tabs */}
              <Tabs
                value={previewTab}
                onChange={(_, newValue) => setPreviewTab(newValue)}
                sx={{ borderBottom: 1, borderColor: 'divider', px: 3 }}
              >
                <Tab label="Metadaten" />
                <Tab
                  label="Inhalt"
                  disabled={previewDialog.document.status !== 'processed'}
                />
              </Tabs>

              {/* Tab Content */}
              <Box sx={{ p: 3 }}>
                {previewTab === 0 && (
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      Dokument-Informationen
                    </Typography>
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          <strong>Originaldatei:</strong> {previewDialog.document.original_filename}
                        </Typography>
                      </Grid>
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
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          <strong>Hochgeladen:</strong> {formatDate(previewDialog.document.created_at)}
                        </Typography>
                      </Grid>
                      {previewDialog.document.processed_at && (
                        <Grid item xs={6}>
                          <Typography variant="body2">
                            <strong>Verarbeitet:</strong> {formatDate(previewDialog.document.processed_at)}
                          </Typography>
                        </Grid>
                      )}
                    </Grid>

                    {previewDialog.document.content_preview && (
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="h6" gutterBottom>
                          Inhaltsvorschau
                        </Typography>
                        <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                            {previewDialog.document.content_preview}
                          </Typography>
                        </Paper>
                      </Box>
                    )}

                    {previewDialog.document.metadata && (
                      <Box>
                        <Typography variant="h6" gutterBottom>
                          Verarbeitungsdetails
                        </Typography>

                        {/* Sections mit Hierarchie */}
                        {previewDialog.document.metadata.sections_hierarchy && previewDialog.document.metadata.sections_hierarchy.length > 0 && (
                          <Box sx={{ mb: 3 }}>
                            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                              Dokumentstruktur ({previewDialog.document.metadata.section_count} Abschnitte)
                            </Typography>
                            <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50', maxHeight: 300, overflow: 'auto' }}>
                              <Box sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                                {previewDialog.document.metadata.sections_hierarchy.map((section: any, idx: number) => (
                                  <Box
                                    key={idx}
                                    sx={{
                                      pl: `${(section.level - 1) * 1.5}rem`,
                                      py: 0.5,
                                      borderLeft: section.level > 1 ? '1px solid #ddd' : 'none',
                                      ml: section.level > 1 ? 1 : 0
                                    }}
                                  >
                                    <Typography
                                      variant="body2"
                                      sx={{
                                        fontSize: `${1 - (section.level - 1) * 0.05}rem`,
                                        fontWeight: section.level === 1 ? 600 : 500,
                                        color: section.level === 1 ? 'primary.main' : 'text.primary'
                                      }}
                                    >
                                      {section.title}
                                    </Typography>
                                  </Box>
                                ))}
                              </Box>
                            </Paper>
                          </Box>
                        )}

                        {/* Fallback: Alle Metadaten als JSON */}
                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, mt: 2 }}>
                          Alle Metadaten
                        </Typography>
                        <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50', maxHeight: 300, overflow: 'auto' }}>
                          <pre style={{ fontSize: '0.75rem', margin: 0, fontFamily: 'monospace' }}>
                            {JSON.stringify(previewDialog.document.metadata, null, 2)}
                          </pre>
                        </Paper>
                      </Box>
                    )}
                  </Box>
                )}

                {previewTab === 1 && (
                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6">
                        Dokumentinhalt ({totalChunks} Chunks)
                      </Typography>
                      {totalPages > 1 && (
                        <Typography variant="body2" color="text.secondary">
                          Seite {currentPage} von {totalPages}
                        </Typography>
                      )}
                    </Box>

                    {chunksLoading ? (
                      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                        <CircularProgress />
                      </Box>
                    ) : documentChunks.length > 0 ? (
                      <Box>
                        {/* Chunks Display */}
                        <Box sx={{ mb: 3 }}>
                          {documentChunks.map((chunk, index) => (
                            <Paper
                              key={`${currentPage}-${index}`}
                              variant="outlined"
                              sx={{
                                p: 2,
                                mb: 2,
                                bgcolor: 'grey.50',
                                borderLeft: 4,
                                borderLeftColor: 'primary.main'
                              }}
                            >
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                                Chunk {chunk.chunk_index + 1}
                                {chunk.page_number && ` • Seite ${chunk.page_number}`}
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{
                                  fontFamily: 'monospace',
                                  fontSize: '0.875rem',
                                  lineHeight: 1.6,
                                  whiteSpace: 'pre-wrap',
                                  wordBreak: 'break-word'
                                }}
                              >
                                {chunk.content}
                              </Typography>
                            </Paper>
                          ))}
                        </Box>

                        {/* Pagination Controls */}
                        {totalPages > 1 && (
                          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, mt: 3 }}>
                            <Button
                              variant="outlined"
                              size="small"
                              disabled={currentPage === 1 || chunksLoading}
                              onClick={() => loadDocumentChunksPaginated(previewDialog.document!.id, currentPage - 1)}
                            >
                              Zurück
                            </Button>

                            {/* Page numbers */}
                            <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                              {Array.from({ length: Math.min(5, totalPages) }, (_, i): number => {
                                if (totalPages <= 5) {
                                  return i + 1;
                                } else if (currentPage <= 3) {
                                  return i + 1;
                                } else if (currentPage >= totalPages - 2) {
                                  return totalPages - 4 + i;
                                } else {
                                  return currentPage - 2 + i;
                                }
                              }).map((pageNum) => (
                                <Button
                                  key={pageNum}
                                  variant={currentPage === pageNum ? 'contained' : 'outlined'}
                                  size="small"
                                  onClick={() => loadDocumentChunksPaginated(previewDialog.document!.id, pageNum)}
                                  disabled={chunksLoading}
                                >
                                  {pageNum}
                                </Button>
                              ))}
                            </Box>

                            <Button
                              variant="outlined"
                              size="small"
                              disabled={currentPage === totalPages || chunksLoading}
                              onClick={() => loadDocumentChunksPaginated(previewDialog.document!.id, currentPage + 1)}
                            >
                              Weiter
                            </Button>
                          </Box>
                        )}
                      </Box>
                    ) : (
                      <Alert severity="info">
                        {previewDialog.document.status !== 'processed'
                          ? 'Dokument muss erst verarbeitet werden, um den Inhalt anzuzeigen.'
                          : 'Kein Inhalt verfügbar.'
                        }
                      </Alert>
                    )}
                  </Box>
                )}
              </Box>
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
