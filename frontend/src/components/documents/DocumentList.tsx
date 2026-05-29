/**
 * DocumentList — Tabellen-Ansicht für die Dokumentbibliothek (TF-355 Phase 3).
 *
 * Presentational component. All mutations flow through props.
 */
import React, { useState } from 'react';
import {
  Box,
  Checkbox,
  Chip,
  CircularProgress,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TextField,
  Tooltip,
} from '@mui/material';
import {
  Business,
  Check,
  Close,
  Edit,
  LockOutlined,
  MoreVert,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import {
  Document,
  DocumentSort,
  DocumentStatus,
  DocumentVisibility,
} from '../../types/document';
import { getDateLocale } from '../../utils/dateLocale';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DocumentListProps {
  documents: Document[];
  selectedDocuments: number[];
  sort?: DocumentSort;
  onToggleSelect: (id: number) => void;
  onToggleSelectAll: () => void;
  onSortChange: (sort: DocumentSort) => void;
  onPreview: (document: Document) => void;
  onRename: (id: number, name: string) => void | Promise<void>;
  onMenu: (event: React.MouseEvent<HTMLElement>, documentId: number) => void;
  isOwner: (document: Document) => boolean;
}

// ---------------------------------------------------------------------------
// Sort helpers
// ---------------------------------------------------------------------------

const COLUMN_SORTS = {
  title: { asc: 'title_asc' as DocumentSort, desc: 'title_desc' as DocumentSort },
  size: { asc: 'size_asc' as DocumentSort, desc: 'size_desc' as DocumentSort },
  created_at: { asc: 'created_at_asc' as DocumentSort, desc: 'created_at_desc' as DocumentSort },
} as const;

type SortColumn = keyof typeof COLUMN_SORTS;

const SORT_TO_COLUMN: Record<DocumentSort, { col: SortColumn; dir: 'asc' | 'desc' }> = {
  title_asc: { col: 'title', dir: 'asc' },
  title_desc: { col: 'title', dir: 'desc' },
  size_asc: { col: 'size', dir: 'asc' },
  size_desc: { col: 'size', dir: 'desc' },
  created_at_asc: { col: 'created_at', dir: 'asc' },
  created_at_desc: { col: 'created_at', dir: 'desc' },
};

function parseSortProp(sort?: DocumentSort): { col: SortColumn | null; dir: 'asc' | 'desc' } {
  if (!sort) return { col: null, dir: 'asc' };
  return SORT_TO_COLUMN[sort] ?? { col: null, dir: 'asc' };
}

function nextSort(col: SortColumn, activeCol: SortColumn | null, dir: 'asc' | 'desc'): DocumentSort {
  if (activeCol === col && dir === 'asc') return COLUMN_SORTS[col].desc;
  return COLUMN_SORTS[col].asc;
}

// ---------------------------------------------------------------------------
// Local formatting helpers (mirrors DocumentLibrary private helpers)
// ---------------------------------------------------------------------------

function formatFileSize(bytes: number | undefined): string {
  if (!bytes || bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString: string, lang: string): string {
  return new Date(dateString).toLocaleDateString(getDateLocale(lang), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getMimeLabel(mimeType: string): string {
  if (mimeType.includes('pdf')) return 'PDF';
  if (mimeType.includes('word') || mimeType.includes('document')) return 'Word';
  if (mimeType.includes('markdown')) return 'Markdown';
  if (mimeType.includes('text')) return 'Text';
  return 'Datei';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  selectedDocuments,
  sort,
  onToggleSelect,
  onToggleSelectAll,
  onSortChange,
  onPreview,
  onRename,
  onMenu,
  isOwner,
}) => {
  const { t, i18n } = useTranslation();

  // Local inline-rename state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const [renaming, setRenaming] = useState(false);

  const { col: activeCol, dir: activeDir } = parseSortProp(sort);

  // Select-all checkbox state
  const allSelected = documents.length > 0 && documents.every(d => selectedDocuments.includes(d.id));
  const someSelected = documents.some(d => selectedDocuments.includes(d.id)) && !allSelected;

  const handleStartRename = (doc: Document) => {
    setEditingId(doc.id);
    setEditingValue(doc.display_name ?? doc.title);
  };

  const handleCancelRename = () => {
    setEditingId(null);
    setEditingValue('');
  };

  const handleSaveRename = async (doc: Document) => {
    if (renaming || editingId === null) return;
    try {
      setRenaming(true);
      await onRename(doc.id, editingValue);
      // Clear edit state only on success
      setEditingId(null);
      setEditingValue('');
    } finally {
      setRenaming(false);
    }
  };

  const renderStatusChip = (doc: Document) => {
    switch (doc.status) {
      case DocumentStatus.PROCESSED:
        return (
          <Chip
            label={t('components.documentLibrary.statusProcessed', 'Verarbeitet')}
            color="success"
            size="small"
          />
        );
      case DocumentStatus.PROCESSING:
        return (
          <Chip
            label={t('components.documentLibrary.statusProcessing', 'Verarbeitung')}
            color="warning"
            size="small"
          />
        );
      case DocumentStatus.UPLOADED:
        return (
          <Chip
            label={t('components.documentLibrary.statusUploaded', 'Hochgeladen')}
            color="default"
            size="small"
          />
        );
      case DocumentStatus.ERROR:
        return (
          <Chip
            label={t('components.documentLibrary.statusError', 'Fehler')}
            color="error"
            size="small"
          />
        );
      case DocumentStatus.COMPLETED:
        return (
          <Chip
            label={t('components.documentLibrary.statusProcessed', 'Verarbeitet')}
            color="success"
            size="small"
          />
        );
      case DocumentStatus.QUEUED:
        return (
          <Chip
            label={t('components.documentLibrary.statusUploaded', 'Hochgeladen')}
            color="default"
            size="small"
          />
        );
      case DocumentStatus.FAILED:
        return (
          <Chip
            label={t('components.documentLibrary.statusError', 'Fehler')}
            color="error"
            size="small"
          />
        );
      default:
        return (
          <Chip
            label={t('components.documentLibrary.statusUnknown', 'Unbekannt')}
            color="default"
            size="small"
          />
        );
    }
  };

  const renderVisibilityIcon = (doc: Document) => {
    const isInstitution = doc.visibility === DocumentVisibility.INSTITUTION;
    const VisIcon = isInstitution ? Business : LockOutlined;
    const label = isInstitution
      ? t('components.documentLibrary.visibilityInstitution', 'Institution')
      : t('components.documentLibrary.visibilityPrivate', 'Privat');
    return (
      <Tooltip title={label}>
        <VisIcon fontSize="small" color={isInstitution ? 'primary' : 'action'} />
      </Tooltip>
    );
  };

  const renderSortLabel = (col: SortColumn, label: string) => (
    <TableSortLabel
      active={activeCol === col}
      direction={activeCol === col ? activeDir : 'asc'}
      onClick={() => onSortChange(nextSort(col, activeCol, activeDir))}
    >
      {label}
    </TableSortLabel>
  );

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            {/* Select-all checkbox */}
            <TableCell padding="checkbox">
              <Checkbox
                indeterminate={someSelected}
                checked={allSelected}
                onChange={onToggleSelectAll}
                aria-label={t('components.documentLibrary.list.selectAll', 'Alle auswählen')}
              />
            </TableCell>
            {/* Visibility */}
            <TableCell>
              {t('components.documentLibrary.list.colVisibility', 'Sichtbarkeit')}
            </TableCell>
            {/* Titel — sortable */}
            <TableCell>
              {renderSortLabel('title', t('components.documentLibrary.list.colTitle', 'Titel'))}
            </TableCell>
            {/* Tags */}
            <TableCell>
              {t('components.documentLibrary.list.colTags', 'Tags')}
            </TableCell>
            {/* Status */}
            <TableCell>
              {t('components.documentLibrary.list.colStatus', 'Status')}
            </TableCell>
            {/* Typ */}
            <TableCell>
              {t('components.documentLibrary.list.colType', 'Typ')}
            </TableCell>
            {/* Grösse — sortable */}
            <TableCell>
              {renderSortLabel('size', t('components.documentLibrary.list.colSize', 'Grösse'))}
            </TableCell>
            {/* Hochgeladen — sortable */}
            <TableCell>
              {renderSortLabel('created_at', t('components.documentLibrary.list.colUploaded', 'Hochgeladen'))}
            </TableCell>
            {/* Actions */}
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {documents.map((doc) => {
            const isEditing = editingId === doc.id;
            const isSelected = selectedDocuments.includes(doc.id);
            const owner = isOwner(doc);

            return (
              <TableRow
                key={doc.id}
                selected={isSelected}
                hover
              >
                {/* Row checkbox */}
                <TableCell padding="checkbox">
                  <Checkbox
                    checked={isSelected}
                    onChange={(e) => {
                      e.stopPropagation();
                      onToggleSelect(doc.id);
                    }}
                    inputProps={{ 'aria-label': doc.display_name ?? doc.title }}
                    onClick={(e) => e.stopPropagation()}
                  />
                </TableCell>

                {/* Visibility icon */}
                <TableCell>
                  {renderVisibilityIcon(doc)}
                </TableCell>

                {/* Title — inline-editable */}
                <TableCell>
                  {isEditing ? (
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <TextField
                        size="small"
                        value={editingValue}
                        onChange={(e) => setEditingValue(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleSaveRename(doc);
                          } else if (e.key === 'Escape') {
                            e.preventDefault();
                            handleCancelRename();
                          }
                        }}
                        autoFocus
                        disabled={renaming}
                        placeholder={doc.original_filename}
                        inputProps={{ maxLength: 255 }}
                        sx={{ minWidth: 180 }}
                      />
                      <Tooltip title={t('components.documentLibrary.renameSave', 'Speichern')}>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSaveRename(doc);
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
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <Box
                        component="span"
                        sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
                        onClick={() => onPreview(doc)}
                        title={doc.display_name ?? doc.title}
                      >
                        {doc.display_name ?? doc.title}
                      </Box>
                      {owner && (
                        <Tooltip title={t('components.documentLibrary.renameTooltip', 'Umbenennen')}>
                          <IconButton
                            size="small"
                            aria-label={t('components.documentLibrary.renameTooltip', 'Umbenennen')}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStartRename(doc);
                            }}
                            sx={{ opacity: 0.4, '&:hover': { opacity: 1 } }}
                          >
                            <Edit fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Stack>
                  )}
                </TableCell>

                {/* Tags */}
                <TableCell>
                  {doc.tags && doc.tags.length > 0 ? (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {doc.tags.slice(0, 3).map((tag) => (
                        <Chip key={tag.id} label={tag.name} size="small" variant="outlined" />
                      ))}
                      {doc.tags.length > 3 && (
                        <Chip
                          label={`+${doc.tags.length - 3}`}
                          size="small"
                          variant="outlined"
                          title={doc.tags.slice(3).map((tg) => tg.name).join(', ')}
                        />
                      )}
                    </Box>
                  ) : null}
                </TableCell>

                {/* Status */}
                <TableCell>
                  {renderStatusChip(doc)}
                </TableCell>

                {/* Typ */}
                <TableCell>
                  {getMimeLabel(doc.mime_type)}
                </TableCell>

                {/* Grösse */}
                <TableCell>
                  {formatFileSize(doc.file_size)}
                </TableCell>

                {/* Hochgeladen */}
                <TableCell>
                  {formatDate(doc.created_at, i18n.language)}
                </TableCell>

                {/* Actions ⋮ */}
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      onMenu(e, doc.id);
                    }}
                  >
                    <MoreVert />
                  </IconButton>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default DocumentList;
