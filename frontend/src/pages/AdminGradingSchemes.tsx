/**
 * AdminGradingSchemes — list page for the /admin/grading-schemes route.
 *
 * Shows system + institution grading schemes in a table. System schemes
 * are read-only (edit/delete buttons disabled). Delete is blocked by a
 * 409 when the scheme is referenced by at least one exam — that error is
 * surfaced as a descriptive inline alert.
 *
 * Requires the `grading_schemes:manage` permission on the writable actions.
 * The page itself is already protected at the route level.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';

import { GradingSchemeOut } from '../types/gradingScheme';
import { GradingSchemesService } from '../services/gradingSchemesService';
import { ApiError } from '../services/submissionsService';
import GradingSchemeEditor from '../components/admin/GradingSchemeEditor';

const AdminGradingSchemes: React.FC = () => {
  const { t } = useTranslation();

  const [schemes, setSchemes] = useState<GradingSchemeOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<GradingSchemeOut | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const result = await GradingSchemesService.list(true);
      setSchemes(result.schemes);
    } catch (err) {
      setLoadError(
        err instanceof ApiError ? err.message : t('admin.gradingSchemes.failedLoad'),
      );
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = () => {
    setEditTarget(null);
    setEditorOpen(true);
  };

  const handleEdit = (scheme: GradingSchemeOut) => {
    setEditTarget(scheme);
    setEditorOpen(true);
  };

  const handleEditorClose = () => {
    setEditorOpen(false);
    setEditTarget(null);
  };

  const handleSaved = () => {
    load();
  };

  const handleDelete = async (scheme: GradingSchemeOut) => {
    setDeleteError(null);
    try {
      await GradingSchemesService.delete(scheme.id);
      setSchemes(prev => prev.filter(s => s.id !== scheme.id));
    } catch (err) {
      if (err instanceof ApiError && err.kind === 'conflict') {
        setDeleteError(t('admin.gradingSchemes.deleteInUse'));
      } else {
        setDeleteError(
          err instanceof ApiError ? err.message : t('admin.gradingSchemes.failedDelete'),
        );
      }
    }
  };

  const configTypeLabel = (type: string) => {
    const map: Record<string, string> = {
      linear: t('admin.gradingSchemes.configTypeLinear'),
      linear_segments: t('admin.gradingSchemes.configTypeLinearSegments'),
      stepped: t('admin.gradingSchemes.configTypeStepped'),
    };
    return map[type] ?? type;
  };

  const formatLabel = (fmt: string) => {
    const map: Record<string, string> = {
      numeric: t('admin.gradingSchemes.displayFormatNumeric'),
      letter: t('admin.gradingSchemes.displayFormatLetter'),
      pass_fail: t('admin.gradingSchemes.displayFormatPassFail'),
    };
    return map[fmt] ?? fmt;
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box mb={3} display="flex" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            {t('admin.gradingSchemes.title')}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {t('admin.gradingSchemes.subtitle')}
          </Typography>
        </Box>
        <Button
          variant="contained"
          onClick={handleCreate}
          data-testid="gs-page-create"
        >
          {t('admin.gradingSchemes.btnCreate')}
        </Button>
      </Box>

      {loadError && (
        <Alert severity="error" sx={{ mb: 2 }} data-testid="gs-page-load-error">
          {loadError}
        </Alert>
      )}

      {deleteError && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          onClose={() => setDeleteError(null)}
          data-testid="gs-page-delete-error"
        >
          {deleteError}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : schemes.length === 0 ? (
        <Typography color="text.secondary" data-testid="gs-page-empty">
          {t('admin.gradingSchemes.empty')}
        </Typography>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" data-testid="gs-page-table">
            <TableHead>
              <TableRow>
                <TableCell>{t('admin.gradingSchemes.colName')}</TableCell>
                <TableCell>{t('admin.gradingSchemes.colType')}</TableCell>
                <TableCell>{t('admin.gradingSchemes.colFormat')}</TableCell>
                <TableCell>{t('admin.gradingSchemes.colDefault')}</TableCell>
                <TableCell align="right">{t('admin.gradingSchemes.colActions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {schemes.map(scheme => (
                <TableRow key={scheme.id} data-testid={`gs-row-${scheme.id}`}>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      {scheme.name}
                      {scheme.is_system_scheme && (
                        <Chip
                          label={t('admin.gradingSchemes.tagSystem')}
                          size="small"
                          variant="outlined"
                          color="default"
                          data-testid={`gs-tag-system-${scheme.id}`}
                        />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {configTypeLabel(scheme.config.type)}
                    </Typography>
                  </TableCell>
                  <TableCell>{formatLabel(scheme.display_format)}</TableCell>
                  <TableCell>
                    {scheme.is_default_for_institution && (
                      <Chip
                        label={t('admin.gradingSchemes.tagDefault')}
                        size="small"
                        color="primary"
                        data-testid={`gs-tag-default-${scheme.id}`}
                      />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip
                      title={
                        scheme.is_system_scheme
                          ? t('admin.gradingSchemes.systemReadOnly')
                          : t('admin.gradingSchemes.btnEdit')
                      }
                    >
                      <span>
                        <IconButton
                          size="small"
                          onClick={() => handleEdit(scheme)}
                          disabled={scheme.is_system_scheme}
                          data-testid={`gs-btn-edit-${scheme.id}`}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                    <Tooltip
                      title={
                        scheme.is_system_scheme
                          ? t('admin.gradingSchemes.systemReadOnly')
                          : t('admin.gradingSchemes.btnDelete')
                      }
                    >
                      <span>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDelete(scheme)}
                          disabled={scheme.is_system_scheme}
                          data-testid={`gs-btn-delete-${scheme.id}`}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <GradingSchemeEditor
        open={editorOpen}
        scheme={editTarget}
        onClose={handleEditorClose}
        onSaved={handleSaved}
      />
    </Container>
  );
};

export default AdminGradingSchemes;
