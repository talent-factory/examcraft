import React, { useState, useEffect, useCallback } from 'react';
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
  Paper,
  TextField,
  Stack
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
  PlayArrow,
  Edit,
  Check,
  Close,
  LockOutlined,
  Business
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../utils/dateLocale';
import { useAuth } from '../contexts/AuthContext';
import { DocumentService } from '../services/DocumentService';
import { Document, DocumentStatus, DocumentVisibility } from '../types/document';
import DocumentVisibilityDialog from './DocumentVisibilityDialog';

const READY_STATUSES: ReadonlyArray<string> = ['processed', 'completed'];
const isDocumentReady = (status: string | undefined | null): boolean =>
  status != null && READY_STATUSES.includes(status);

/**
 * Pick a localized error key for the ORIGINAL preview based on the HTTP
 * status of a `DocumentFetchError`. Falls back to the generic
 * `originalError` key (which interpolates the raw message) for unmapped
 * statuses so the user still sees something actionable.
 */
const errorKeyForStatus = (status: number): string => {
  if (status === 0) return 'components.documentLibrary.originalErrorNetwork';
  if (status === 401) return 'components.documentLibrary.originalErrorAuth';
  if (status === 403) return 'components.documentLibrary.originalErrorPermission';
  if (status === 404) return 'components.documentLibrary.originalErrorMissing';
  if (status === 429 || status === 503) return 'components.documentLibrary.originalErrorThrottled';
  if (status >= 500) return 'components.documentLibrary.originalErrorServer';
  return 'components.documentLibrary.originalError';
};

interface DocumentLibraryProps {
  onCreateRAGExam?: (documentIds: number[]) => void;
  refreshTrigger?: number;
}

/**
 * Renders the ORIGINAL preview tab. Dispatches on MIME type / source:
 *   - PDF        -> <object> with blob URL + anchor fallback (Safari)
 *   - Markdown   -> react-markdown + remark-gfm (also chat exports)
 *   - Plain text -> monospace <Paper>
 *   - DOCX       -> info alert; extracted text lives in the CHUNKS tab
 *   - Unknown    -> info alert
 *
 * Bytes come from GET /api/v1/documents/{id}/raw (Content-Disposition: inline).
 * Prop is named `doc` to avoid shadowing the DOM `document` global.
 */
interface OriginalDocumentContentProps {
  doc: Document;
}

const OriginalDocumentContent: React.FC<OriginalDocumentContentProps> = ({ doc }) => {
  const { t } = useTranslation();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<string>('');

  const mime = doc.mime_type || '';
  const isChatExport = doc.metadata?.source === 'chat_export';
  const isPdf = mime === 'application/pdf';
  const isMarkdown =
    mime === 'text/markdown' || mime === 'text/x-markdown' || isChatExport;
  const isPlainText = mime === 'text/plain';
  // Match all Word-family MIMEs: classic .doc, .docx, .docm (macro-enabled),
  // .dotx (template). Anything containing 'wordprocessingml' is a Word doc.
  const isDocx = mime.includes('wordprocessingml') || mime === 'application/msword';

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    let createdBlobUrl: string | null = null;

    if (isDocx) {
      setLoading(false);
      return () => {
        controller.abort();
      };
    }

    setLoading(true);
    setErrorKey(null);
    setErrorDetail('');

    (async () => {
      try {
        const response = await DocumentService.getDocumentRaw(doc.id);
        if (cancelled) return;

        if (isPdf) {
          const blob = await response.blob();
          if (cancelled) return;
          const url = URL.createObjectURL(blob);
          createdBlobUrl = url;
          setBlobUrl(url);
        } else {
          const text = await response.text();
          if (cancelled) return;
          setTextContent(text);
        }
      } catch (e) {
        if (cancelled) return;
        // AbortError is the expected outcome of unmount/document switch —
        // never surface it as an error to the user.
        if (e instanceof DOMException && e.name === 'AbortError') return;
        // Duck-type DocumentFetchError so the check survives jest auto-mocks
        // (where the module-scope class identity may diverge between
        // component and test imports).
        const maybeFetchErr = e as { name?: string; status?: number; message?: string };
        if (
          maybeFetchErr?.name === 'DocumentFetchError' &&
          typeof maybeFetchErr.status === 'number'
        ) {
          setErrorKey(errorKeyForStatus(maybeFetchErr.status));
          setErrorDetail(maybeFetchErr.message ?? '');
        } else {
          setErrorKey('components.documentLibrary.originalError');
          setErrorDetail(
            e && typeof e === 'object' && 'message' in e
              ? (e as Error).message
              : 'Unknown error',
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
      if (createdBlobUrl) {
        URL.revokeObjectURL(createdBlobUrl);
      }
    };
  }, [doc.id, isPdf, isDocx]);

  if (isDocx) {
    return (
      <Alert severity="info">
        {t('components.documentLibrary.originalDocxPending')}
      </Alert>
    );
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4, gap: 1 }}>
        <CircularProgress />
        <Typography variant="caption" color="text.secondary">
          {t('components.documentLibrary.originalLoading')}
        </Typography>
      </Box>
    );
  }

  if (errorKey) {
    return (
      <Alert severity="error">
        {t(errorKey, { error: errorDetail })}
      </Alert>
    );
  }

  if (isPdf && blobUrl) {
    // <object> renders PDFs in Chrome/Firefox/Edge and degrades to the
    // fallback <a> on Safari (which refuses to render `blob:` PDFs in an
    // embedded viewer). `sandbox` is intentionally omitted: an empty
    // sandbox blocks PDF.js scripts in Firefox and blanks the viewer.
    return (
      <Box
        sx={{
          height: 600,
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <object
          data={blobUrl}
          type="application/pdf"
          aria-label={doc.original_filename}
          style={{ width: '100%', flex: 1 }}
        >
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" gutterBottom>
              {t('components.documentLibrary.originalPdfFallback')}
            </Typography>
            <Button
              variant="outlined"
              component="a"
              href={blobUrl}
              target="_blank"
              rel="noopener noreferrer"
              download={doc.original_filename}
            >
              {t('components.documentLibrary.originalOpenInNewTab')}
            </Button>
          </Box>
        </object>
      </Box>
    );
  }

  if (isMarkdown && textContent !== null) {
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 3,
          maxHeight: 600,
          overflow: 'auto',
          '& pre': {
            bgcolor: 'grey.100',
            p: 1,
            borderRadius: 1,
            overflow: 'auto',
          },
          '& code': {
            bgcolor: 'grey.100',
            px: 0.5,
            borderRadius: 0.5,
            fontSize: '0.875em',
          },
        }}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{textContent}</ReactMarkdown>
      </Paper>
    );
  }

  if (isPlainText && textContent !== null) {
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 3,
          maxHeight: 600,
          overflow: 'auto',
          fontFamily: 'monospace',
          fontSize: '0.875rem',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {textContent}
      </Paper>
    );
  }

  return (
    <Alert severity="info">
      {t('components.documentLibrary.originalUnsupported')}
    </Alert>
  );
};

const DocumentLibrary: React.FC<DocumentLibraryProps> = ({
  onCreateRAGExam,
  refreshTrigger
}) => {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const hasInstitution = Boolean(user?.institution_id);
  const institutionName = user?.institution?.name ?? '';
  const isOwner = (document: Document): boolean =>
    user != null && document.user_id != null && document.user_id === user.id;
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
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
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [documentContent, setDocumentContent] = useState<string | null>(null);
  const [processingDocumentId, setProcessingDocumentId] = useState<number | null>(null);

  // Inline title rename state
  const [editingDocumentId, setEditingDocumentId] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const [renaming, setRenaming] = useState(false);

  // Visibility quick-edit state (TF-354)
  const [visibilityDialog, setVisibilityDialog] = useState<{ open: boolean; document: Document | null }>({
    open: false,
    document: null,
  });
  const [savingVisibility, setSavingVisibility] = useState(false);
  const [visibilityError, setVisibilityError] = useState<string | null>(null);

  // Pagination state for large documents
  const [documentChunks, setDocumentChunks] = useState<any[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalChunks, setTotalChunks] = useState(0);
  const [chunksPageSize] = useState(10); // Chunks pro Seite
  const [chunksLoading, setChunksLoading] = useState(false);
  const [chunksError, setChunksError] = useState<string | null>(null);

  // Define loadDocuments before useEffect hooks that use it
  const loadDocuments = useCallback(async (showLoading: boolean = true) => {
    try {
      if (showLoading && !hasLoadedOnce) {
        setLoading(true);
      }
      setError(null);
      const docs = await DocumentService.getDocuments();
      setDocuments(docs);
    } catch (err) {
      setError(err && typeof err === 'object' && 'message' in err ? (err as Error).message : t('components.documentLibrary.loadError'));
    } finally {
      // ALWAYS set loading to false after load completes
      setLoading(false);
      // Mark that we've loaded at least once
      if (!hasLoadedOnce) {
        setHasLoadedOnce(true);
      }
    }
  }, [hasLoadedOnce, t]);

  // Initial load and refresh trigger
  useEffect(() => {
    loadDocuments(true); // Initial load with loading state
  }, [refreshTrigger, loadDocuments]);

  // Auto-refresh for documents with status "processing"
  useEffect(() => {
    const hasProcessingDocs = documents.some(doc => doc.status === DocumentStatus.PROCESSING);

    if (!hasProcessingDocs) {
      return; // No processing documents, no need to refresh
    }

    // Refresh every 5 seconds while there are processing documents
    const intervalId = setInterval(() => {
      loadDocuments(false); // Background refresh without loading state
    }, 5000);

    // Cleanup: Stop interval when component unmounts or no more processing docs
    return () => {
      clearInterval(intervalId);
    };
  }, [documents, loadDocuments]); // Re-run when documents change

  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes('pdf')) return <PictureAsPdf color="error" />;
    if (mimeType.includes('text')) return <TextSnippet color="info" />;
    if (mimeType.includes('word') || mimeType.includes('document')) return <Description color="primary" />;
    if (mimeType.includes('markdown')) return <Code color="success" />;
    return <Description />;
  };

  /**
   * Resolve a localised error message for a failed document.
   * Looks up `metadata.error_code` in i18n; falls back to the raw English
   * `error` string when the code is unknown to keep the user informed.
   */
  const resolveErrorMessage = (document: Document): string => {
    const code = document.metadata?.error_code;
    if (code) {
      const i18nKey = `components.documentLibrary.errorMessages.${code}`;
      const localised = t(i18nKey);
      if (localised && localised !== i18nKey) {
        return localised;
      }
    }
    return document.metadata?.error
      || document.metadata?.vector_embedding_error
      || t('components.documentLibrary.errorMessages.unknown_error');
  };

  const getStatusChip = (status: DocumentStatus, document?: Document) => {
    switch (status) {
      case DocumentStatus.UPLOADED:
        return <Chip icon={<CloudUpload />} label={t('components.documentLibrary.statusUploaded')} color="default" size="small" />;
      case DocumentStatus.PROCESSING:
        return <Chip icon={<Schedule />} label={t('components.documentLibrary.statusProcessing')} color="warning" size="small" />;
      case DocumentStatus.PROCESSED:
        return <Chip icon={<CheckCircle />} label={t('components.documentLibrary.statusProcessed')} color="success" size="small" />;
      case DocumentStatus.ERROR: {
        const errorChip = (
          <Chip icon={<ErrorIcon />} label={t('components.documentLibrary.statusError')} color="error" size="small" />
        );
        if (!document) return errorChip;
        const tooltipText = t('components.documentLibrary.errorTooltip', {
          code: document.metadata?.error_code || 'unknown_error',
          filename: document.metadata?.error_details?.filename || document.original_filename,
        });
        return <Tooltip title={tooltipText}>{errorChip}</Tooltip>;
      }
      default:
        return <Chip label={t('components.documentLibrary.statusUnknown')} color="default" size="small" />;
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
    return new Date(dateString).toLocaleDateString(getDateLocale(i18n.language), {
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
    // Open ORIGINAL by default when the document is ready; the tab itself
    // is disabled (and METADATEN is opened) until processing finishes.
    setPreviewTab(isDocumentReady(document.status) ? 1 : 0);
    setDocumentContent(null);
    setDocumentChunks([]);
    setChunksError(null);
    setCurrentPage(1);
    handleMenuClose();

    // Pre-fetch chunks so switching to the CHUNKS tab feels instant.
    if (isDocumentReady(document.status)) {
      await loadDocumentChunksPaginated(document.id, 1);
    }
  };

  const loadDocumentChunksPaginated = async (documentId: number, page: number) => {
    try {
      setChunksLoading(true);
      setChunksError(null);
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
      // Default tab is ORIGINAL, so a chunk-load failure would otherwise be
      // invisible until the user clicks CHUNKS. Surface it via state so the
      // CHUNKS tab can show an Alert instead of an empty list.
      // eslint-disable-next-line no-console
      console.error('Failed to load document chunks:', err);
      setDocumentChunks([]);
      setChunksError(
        err && typeof err === 'object' && 'message' in err
          ? (err as Error).message
          : 'Unknown error',
      );
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
      setError(err && typeof err === 'object' && 'message' in err ? (err as Error).message : t('components.documentLibrary.deleteError'));
    }
  };

  const handleDownload = async (document: Document) => {
    try {
      // Use original_filename for user-friendly download name
      await DocumentService.downloadDocument(document.id, document.original_filename);
      handleMenuClose();
    } catch (err) {
      setError(err && typeof err === 'object' && 'message' in err ? (err as Error).message : t('components.documentLibrary.downloadError'));
    }
  };

  const handleStartRename = (document: Document) => {
    setEditingDocumentId(document.id);
    setEditingValue(document.display_name ?? document.title);
  };

  const handleCancelRename = () => {
    setEditingDocumentId(null);
    setEditingValue('');
  };

  const handleSaveRename = async () => {
    // Guard against double-fire from rapid Enter keypresses or
    // simultaneous Save-button clicks while a request is in flight.
    if (renaming || editingDocumentId === null) return;
    const trimmed = editingValue.trim();
    // Empty value clears the override and falls back to the resolver chain
    const payload = trimmed.length === 0 ? null : trimmed;
    try {
      setRenaming(true);
      const updated = await DocumentService.renameDocument(editingDocumentId, payload);
      setDocuments(prev =>
        prev.map(d => (d.id === updated.id ? { ...d, ...updated } : d))
      );
      setEditingDocumentId(null);
      setEditingValue('');
      setError(null);
    } catch (err) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? (err as Error).message
          : t('components.documentLibrary.renameError', 'Umbenennen fehlgeschlagen'),
      );
    } finally {
      setRenaming(false);
    }
  };

  const handleOpenVisibility = (document: Document) => {
    setVisibilityError(null);
    setVisibilityDialog({ open: true, document });
    handleMenuClose();
  };

  const handleCloseVisibility = () => {
    if (savingVisibility) return;
    setVisibilityDialog({ open: false, document: null });
    setVisibilityError(null);
  };

  const handleSaveVisibility = async (newVisibility: DocumentVisibility) => {
    const target = visibilityDialog.document;
    if (!target) return;
    try {
      setSavingVisibility(true);
      setVisibilityError(null);
      const updated = await DocumentService.updateVisibility(target.id, newVisibility);
      setDocuments(prev =>
        prev.map(d => (d.id === updated.id ? { ...d, ...updated } : d)),
      );
      setVisibilityDialog({ open: false, document: null });
    } catch (err) {
      setVisibilityError(
        err && typeof err === 'object' && 'message' in err
          ? (err as Error).message
          : t('components.documentVisibility.saveError', 'Sichtbarkeit konnte nicht geändert werden'),
      );
    } finally {
      setSavingVisibility(false);
    }
  };

  const handleProcess = async (document: Document) => {
    try {
      setProcessingDocumentId(document.id);
      handleMenuClose();

      // Start processing (asynchron im Backend) - NICHT WARTEN!
      await DocumentService.processDocument(document.id, true);

      // SOFORT Dokumente neu laden - Processing läuft im Hintergrund!
      await loadDocuments();

      setError(null);

    } catch (err) {
      setError(err && typeof err === 'object' && 'message' in err ? (err as Error).message : t('components.documentLibrary.processError'));
    } finally {
      setProcessingDocumentId(null);
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
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

  // Visibility indicator next to the title (TF-354). 🔒 private / 🏢 institution.
  // Owners get a clickable button that opens the quick-edit dialog; everyone
  // else sees a static informational icon.
  const renderVisibilityIcon = (document: Document) => {
    const isInstitution = document.visibility === DocumentVisibility.INSTITUTION;
    const VisIcon = isInstitution ? Business : LockOutlined;
    const label = isInstitution
      ? t('components.documentLibrary.visibilityInstitution')
      : t('components.documentLibrary.visibilityPrivate');
    const owner = isOwner(document);
    const tooltip = owner
      ? `${label} — ${t('components.documentLibrary.visibilityClickToChange')}`
      : label;
    const icon = <VisIcon fontSize="small" color={isInstitution ? 'primary' : 'action'} />;
    return (
      <Tooltip title={tooltip}>
        {owner ? (
          <IconButton
            size="small"
            aria-label={t('components.documentLibrary.visibilityEditAria')}
            onClick={(e) => {
              e.stopPropagation();
              handleOpenVisibility(document);
            }}
            sx={{ p: 0.25 }}
          >
            {icon}
          </IconButton>
        ) : (
          <Box component="span" sx={{ display: 'inline-flex', p: 0.25 }}>
            {icon}
          </Box>
        )}
      </Tooltip>
    );
  };

  const processedDocuments = documents?.filter(doc => doc.status === DocumentStatus.PROCESSED) || [];
  const canCreateRAGExam = selectedDocuments.length > 0 &&
    selectedDocuments.every(id => {
      const doc = documents?.find(d => d.id === id);
      return doc?.status === DocumentStatus.PROCESSED && doc?.has_vectors;
    });

  // Only show loading spinner on initial load, not on background refreshes
  // Use hasLoadedOnce to persist the state even if component remounts
  if (loading && !hasLoadedOnce) {
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
          {t('components.documentLibrary.title', { count: documents.length })}
        </Typography>

        {selectedDocuments.length > 0 && (
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              {t('components.documentLibrary.selected', { count: selectedDocuments.length })}
            </Typography>
            <Button
              variant="contained"
              startIcon={<Psychology />}
              onClick={handleCreateRAGExam}
              disabled={!canCreateRAGExam}
              size="small"
            >
              {t('components.documentLibrary.createRAGExam')}
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
                  {t('components.documentLibrary.statsTotal')}
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
                  {t('components.documentLibrary.statsProcessed')}
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
                  {t('components.documentLibrary.statsWithVectors')}
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
                  {t('components.documentLibrary.statsInProgress')}
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
              {t('components.documentLibrary.noDocuments')}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t('components.documentLibrary.noDocumentsHint')}
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
                        <Tooltip title={t('components.documentLibrary.vectorsAvailable')}>
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

                  {/* Document Title — inline-editable */}
                  {editingDocumentId === document.id ? (
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
                      <TextField
                        size="small"
                        value={editingValue}
                        onChange={(e) => setEditingValue(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleSaveRename();
                          } else if (e.key === 'Escape') {
                            e.preventDefault();
                            handleCancelRename();
                          }
                        }}
                        autoFocus
                        fullWidth
                        disabled={renaming}
                        placeholder={document.original_filename}
                        inputProps={{ maxLength: 255 }}
                      />
                      <Tooltip title={t('components.documentLibrary.renameSave', 'Speichern')}>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSaveRename();
                          }}
                          disabled={renaming}
                        >
                          {renaming ? <CircularProgress size={16} /> : <Check fontSize="small" />}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={t('components.documentLibrary.renameCancel', 'Abbrechen')}>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCancelRename();
                          }}
                          disabled={renaming}
                        >
                          <Close fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  ) : (
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
                      {renderVisibilityIcon(document)}
                      <Typography
                        variant="subtitle1"
                        noWrap
                        title={document.title}
                        sx={{ flex: 1, minWidth: 0 }}
                      >
                        {document.title}
                      </Typography>
                      <Tooltip title={t('components.documentLibrary.renameTooltip', 'Umbenennen')}>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartRename(document);
                          }}
                          sx={{ opacity: 0.6, '&:hover': { opacity: 1 } }}
                        >
                          <Edit fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  )}

                  {/* Status */}
                  <Box sx={{ mb: 2 }}>
                    {getStatusChip(document.status, document)}
                  </Box>

                  {/* Localised error detail — only when status === ERROR.
                      Tooltip on the chip shows the machine-readable code +
                      filename for support diagnostics; the inline Alert
                      shows the actionable message every user can read. */}
                  {document.status === DocumentStatus.ERROR && (
                    <Alert
                      severity="error"
                      icon={false}
                      sx={{
                        mb: 2,
                        py: 0.5,
                        '& .MuiAlert-message': { fontSize: '0.85rem' },
                      }}
                    >
                      {resolveErrorMessage(document)}
                    </Alert>
                  )}

                  {/* Processing Progress */}
                  {document.status === DocumentStatus.PROCESSING && (
                    <Box sx={{ mb: 2 }}>
                      <LinearProgress />
                      <Typography variant="caption" color="text.secondary">
                        {t('components.documentLibrary.processingRunning')}
                      </Typography>
                    </Box>
                  )}

                  {/* Metadata */}
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      {t('components.documentLibrary.sizeLabel', { size: formatFileSize(document.file_size || 0) })}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t('components.documentLibrary.uploadedLabel', { date: formatDate(document.created_at) })}
                    </Typography>
                    {document.processed_at && (
                      <Typography variant="caption" color="text.secondary">
                        {t('components.documentLibrary.processedLabel', { date: formatDate(document.processed_at) })}
                      </Typography>
                    )}
                    {document.metadata?.total_chunks && (
                      <Typography variant="caption" color="text.secondary">
                        {t('components.documentLibrary.chunksLabel', { count: document.metadata.total_chunks })}
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
          <ListItemText>{t('components.documentLibrary.menuPreview')}</ListItemText>
        </MenuItem>

        <MenuItem onClick={() => {
          const doc = documents.find(d => d.id === menuAnchor?.documentId);
          if (doc) handleDownload(doc);
        }}>
          <ListItemIcon>
            <Download fontSize="small" />
          </ListItemIcon>
          <ListItemText>{t('components.documentLibrary.menuDownload')}</ListItemText>
        </MenuItem>

        {/* Change visibility — owner-only (TF-354), redundant with the
            clickable card icon for discoverability. */}
        {(() => {
          const doc = menuAnchor
            ? documents.find(d => d.id === menuAnchor.documentId)
            : undefined;
          if (!doc || !isOwner(doc)) return null;
          const isInst = doc.visibility === DocumentVisibility.INSTITUTION;
          return (
            <MenuItem onClick={() => handleOpenVisibility(doc)}>
              <ListItemIcon>
                {isInst ? <Business fontSize="small" /> : <LockOutlined fontSize="small" />}
              </ListItemIcon>
              <ListItemText>{t('components.documentLibrary.menuChangeVisibility')}</ListItemText>
            </MenuItem>
          );
        })()}

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
                {processingDocumentId === menuAnchor.documentId
                  ? t('components.documentLibrary.menuProcessing')
                  : t('components.documentLibrary.menuProcess')}
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
          <ListItemText>{t('components.documentLibrary.menuDelete')}</ListItemText>
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, document: null })}
      >
        <DialogTitle>{t('components.documentLibrary.deleteTitle')}</DialogTitle>
        <DialogContent>
          <Typography>
            {t('components.documentLibrary.deleteConfirm', { title: deleteDialog.document?.title })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, document: null })}>
            {t('components.documentLibrary.cancel')}
          </Button>
          <Button onClick={confirmDelete} color="error" variant="contained">
            {t('components.documentLibrary.delete')}
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
          {t('components.documentLibrary.previewTitle', { title: previewDialog.document?.title })}
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
                <Tab label={t('components.documentLibrary.tabMetadata')} />
                <Tab
                  label={t('components.documentLibrary.tabOriginal')}
                  disabled={!isDocumentReady(previewDialog.document.status)}
                />
                <Tab
                  label={t('components.documentLibrary.tabChunks')}
                  disabled={!isDocumentReady(previewDialog.document.status)}
                />
              </Tabs>

              {/* Tab Content */}
              <Box sx={{ p: 3 }}>
                {previewTab === 0 && (
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      {t('components.documentLibrary.docInfo')}
                    </Typography>
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          <strong>{t('components.documentLibrary.originalFile')}</strong> {previewDialog.document.original_filename}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          <strong>{t('components.documentLibrary.fileSize')}</strong> {formatFileSize(previewDialog.document.file_size || 0)}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          <strong>{t('components.documentLibrary.mimeType')}</strong> {previewDialog.document.mime_type}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          <strong>{t('components.documentLibrary.status')}</strong> {previewDialog.document.status}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          <strong>{t('components.documentLibrary.vectors')}</strong> {previewDialog.document.has_vectors ? t('components.documentLibrary.yes') : t('components.documentLibrary.no')}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          <strong>{t('components.documentLibrary.uploaded')}</strong> {formatDate(previewDialog.document.created_at)}
                        </Typography>
                      </Grid>
                      {previewDialog.document.processed_at && (
                        <Grid item xs={6}>
                          <Typography variant="body2">
                            <strong>{t('components.documentLibrary.processed')}</strong> {formatDate(previewDialog.document.processed_at)}
                          </Typography>
                        </Grid>
                      )}
                    </Grid>

                    {previewDialog.document.content_preview && (
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="h6" gutterBottom>
                          {t('components.documentLibrary.contentPreview')}
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
                          {t('components.documentLibrary.processingDetails')}
                        </Typography>

                        {/* Sections mit Hierarchie */}
                        {previewDialog.document.metadata.sections_hierarchy && previewDialog.document.metadata.sections_hierarchy.length > 0 && (
                          <Box sx={{ mb: 3 }}>
                            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                              {t('components.documentLibrary.documentStructure', { count: previewDialog.document.metadata.section_count })}
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
                          {t('components.documentLibrary.allMetadata')}
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
                    <OriginalDocumentContent doc={previewDialog.document} />
                  </Box>
                )}

                {previewTab === 2 && (
                  <Box>
                    {chunksError && (
                      <Alert severity="error" sx={{ mb: 2 }} onClose={() => setChunksError(null)}>
                        {t('components.documentLibrary.chunksLoadError', { error: chunksError })}
                      </Alert>
                    )}
                    {/* Fallback for non-chat-export documents that happen to
                        populate metadata.full_content. Chat exports are
                        rendered in the ORIGINAL tab. */}
                    {previewDialog.document.metadata?.full_content ? (
                      <Box>
                        <Typography variant="h6" gutterBottom>
                          {t('components.documentLibrary.documentContent')}
                        </Typography>
                        <Paper
                          variant="outlined"
                          sx={{
                            p: 3,
                            bgcolor: 'grey.50',
                            maxHeight: 600,
                            overflow: 'auto',
                            fontFamily: 'monospace',
                            fontSize: '0.875rem',
                            lineHeight: 1.6,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word'
                          }}
                        >
                          {previewDialog.document.metadata.full_content}
                        </Paper>
                      </Box>
                    ) : (
                      <>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                          <Typography variant="h6">
                            {t('components.documentLibrary.documentContentChunks', { count: totalChunks })}
                          </Typography>
                          {totalPages > 1 && (
                            <Typography variant="body2" color="text.secondary">
                              {t('components.documentLibrary.pageOf', { current: currentPage, total: totalPages })}
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
                                {t('components.documentLibrary.chunkLabel', { number: chunk.chunk_index + 1 })}
                                {chunk.page_number && ` • ${t('components.documentLibrary.chunkPage', { number: chunk.page_number })}`}
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
                              {t('components.documentLibrary.prevPage')}
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
                              {t('components.documentLibrary.nextPage')}
                            </Button>
                          </Box>
                        )}
                      </Box>
                    ) : (
                      <Alert severity="info">
                        {!isDocumentReady(previewDialog.document.status)
                          ? t('components.documentLibrary.needsProcessing')
                          : t('components.documentLibrary.noContent')
                        }
                      </Alert>
                    )}
                      </>
                    )}
                  </Box>
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialog({ open: false, document: null })}>
            {t('components.documentLibrary.close')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Visibility quick-edit dialog (TF-354) */}
      <DocumentVisibilityDialog
        open={visibilityDialog.open}
        current={visibilityDialog.document?.visibility ?? DocumentVisibility.PRIVATE}
        institutionName={institutionName}
        hasInstitution={hasInstitution}
        saving={savingVisibility}
        error={visibilityError}
        onClose={handleCloseVisibility}
        onSave={handleSaveVisibility}
      />
    </Box>
  );
};

export default DocumentLibrary;
