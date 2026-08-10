/**
 * AdminOrgUnits — list page for the org-units admin tab (Stufe 0 Fundament).
 *
 * Flat list (parent shown as a column, not a visual tree — see design doc's
 * scope note: no tree-view precedent in this frontend yet). Delete shows an
 * explicit confirm dialog with the descendant count so a cascading delete
 * is never silent.
 *
 * Requires the `manage_org_units` permission on the writable actions.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material';

import { OrgUnitOut } from '../types/orgUnit';
import { OrgUnitsService } from '../services/orgUnitsService';
import { ApiError } from '../services/submissionsService';
import OrgUnitEditor from '../components/admin/OrgUnitEditor';

const AdminOrgUnits: React.FC = () => {
  const { t } = useTranslation();

  const [units, setUnits] = useState<OrgUnitOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<OrgUnitOut | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<OrgUnitOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const result = await OrgUnitsService.list();
      setUnits(result.items);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : t('admin.orgUnits.failedLoad'));
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

  const handleEdit = (unit: OrgUnitOut) => {
    setEditTarget(unit);
    setEditorOpen(true);
  };

  const handleEditorClose = () => {
    setEditorOpen(false);
    setEditTarget(null);
  };

  const parentName = (unit: OrgUnitOut): string => {
    if (unit.parent_org_unit_id === null) return '—';
    return units.find(u => u.id === unit.parent_org_unit_id)?.name ?? '—';
  };

  const handleDeleteConfirmed = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setActionError(null);
    try {
      await OrgUnitsService.remove(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch (err) {
      setActionError(
        err instanceof ApiError ? err.message : t('admin.orgUnits.failedDelete'),
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box mb={3} display="flex" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            {t('admin.orgUnits.title')}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {t('admin.orgUnits.subtitle')}
          </Typography>
        </Box>
        <Button variant="contained" onClick={handleCreate} data-testid="ou-page-create">
          {t('admin.orgUnits.btnCreate')}
        </Button>
      </Box>

      {loadError && (
        <Alert severity="error" sx={{ mb: 2 }} data-testid="ou-page-load-error">
          {loadError}
        </Alert>
      )}
      {actionError && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          onClose={() => setActionError(null)}
          data-testid="ou-page-action-error"
        >
          {actionError}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : units.length === 0 ? (
        <Typography color="text.secondary" data-testid="ou-page-empty">
          {t('admin.orgUnits.empty')}
        </Typography>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" data-testid="ou-page-table">
            <TableHead>
              <TableRow>
                <TableCell>{t('admin.orgUnits.colName')}</TableCell>
                <TableCell>{t('admin.orgUnits.colType')}</TableCell>
                <TableCell>{t('admin.orgUnits.colParent')}</TableCell>
                <TableCell align="right">{t('admin.orgUnits.colDescendants')}</TableCell>
                <TableCell align="right">{t('admin.orgUnits.colActions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {units.map(unit => (
                <TableRow key={unit.id} data-testid={`ou-row-${unit.id}`}>
                  <TableCell>{unit.name}</TableCell>
                  <TableCell>{unit.unit_type}</TableCell>
                  <TableCell>{parentName(unit)}</TableCell>
                  <TableCell align="right">{unit.descendant_count}</TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleEdit(unit)}
                      data-testid={`ou-btn-edit-${unit.id}`}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => setDeleteTarget(unit)}
                      data-testid={`ou-btn-delete-${unit.id}`}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <OrgUnitEditor
        open={editorOpen}
        orgUnit={editTarget}
        allOrgUnits={units}
        onClose={handleEditorClose}
        onSaved={load}
      />

      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        data-testid="ou-delete-confirm-dialog"
      >
        <DialogTitle>{t('admin.orgUnits.deleteConfirmTitle')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {deleteTarget && deleteTarget.descendant_count > 0
              ? t('admin.orgUnits.deleteConfirmBodyWithChildren', {
                  name: deleteTarget.name,
                  count: deleteTarget.descendant_count,
                })
              : t('admin.orgUnits.deleteConfirmBodyNoChildren', {
                  name: deleteTarget?.name ?? '',
                })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleting}>
            {t('admin.orgUnits.btnCancel')}
          </Button>
          <Button
            onClick={handleDeleteConfirmed}
            color="error"
            variant="contained"
            disabled={deleting}
            data-testid="ou-delete-confirm-btn"
          >
            {t('admin.orgUnits.btnConfirmDelete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AdminOrgUnits;
