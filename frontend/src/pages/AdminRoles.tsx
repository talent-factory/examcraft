/**
 * AdminRoles — Listenseite für den "Rollen"-Tab (TF-603).
 *
 * Ersetzt die bisherige RoleManagementPage (System A / RBACRole, siehe
 * Design-Doc). Zeigt models.auth.Role (System B) — das, was Role.permissions
 * tatsächlich enforced. Nur für Superuser sichtbar (Admin.tsx: visible: isSuperuser),
 * konsistent mit dem Backend-Guard get_current_superuser.
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
  Chip,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { RolesService } from '../services/rolesService';
import { ApiError } from '../services/httpClient';
import { RoleOut } from '../types/role';
import RolePermissionsEditor from '../components/admin/RolePermissionsEditor';

const AdminRoles: React.FC = () => {
  const { t } = useTranslation();
  const [roles, setRoles] = useState<RoleOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleOut | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<RoleOut | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await RolesService.list();
      setRoles(data);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('Failed to load roles', e);
      if (e instanceof ApiError && typeof e.detail === 'string' && e.detail) {
        setError(e.detail);
      } else {
        setError(t('admin.roles.failedLoad'));
      }
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditingRole(null);
    setEditorOpen(true);
  };

  const openEdit = (role: RoleOut) => {
    setEditingRole(role);
    setEditorOpen(true);
  };

  const handleSaved = () => {
    setEditorOpen(false);
    load();
  };

  const openDeleteConfirm = (role: RoleOut) => {
    setDeleteError(null);
    setDeleteTarget(role);
  };

  const closeDeleteConfirm = () => {
    setDeleteError(null);
    setDeleteTarget(null);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleteError(null);
    try {
      await RolesService.remove(deleteTarget.id);
      setDeleteTarget(null);
      load();
    } catch (e) {
      // Backend liefert bei 409 (Systemrolle / noch zugewiesene Benutzer)
      // eine aussagekräftige detail-Message — die zeigen wir statt des
      // generischen Fallbacks. Netzwerkfehler (kein `.detail`) fallen
      // weiterhin auf den generischen i18n-String zurück (TF-603 Finding 4).
      if (e instanceof ApiError && typeof e.detail === 'string' && e.detail) {
        setDeleteError(e.detail);
      } else {
        setDeleteError(t('admin.roles.failedDelete'));
      }
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h5">{t('admin.roles.title')}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t('admin.roles.subtitle')}
          </Typography>
        </Box>
        <Button variant="contained" onClick={openCreate}>
          {t('admin.roles.btnCreate')}
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <CircularProgress />
      ) : roles.length === 0 ? (
        <Typography color="text.secondary">{t('admin.roles.empty')}</Typography>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('admin.roles.colName')}</TableCell>
                <TableCell>{t('admin.roles.colDisplayName')}</TableCell>
                <TableCell>{t('admin.roles.colPermissionCount')}</TableCell>
                <TableCell>{t('admin.roles.colSystemRole')}</TableCell>
                <TableCell>{t('admin.roles.colActions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {roles.map((role) => (
                <TableRow key={role.id}>
                  <TableCell>{role.name}</TableCell>
                  <TableCell>{role.display_name}</TableCell>
                  <TableCell>{role.permissions.length}</TableCell>
                  <TableCell>
                    {role.is_system_role && <Chip size="small" label={t('admin.roles.colSystemRole')} />}
                  </TableCell>
                  <TableCell>
                    <IconButton aria-label={t('admin.roles.btnEdit')} onClick={() => openEdit(role)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      aria-label={t('admin.roles.btnDelete')}
                      onClick={() => openDeleteConfirm(role)}
                      disabled={role.is_system_role}
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

      <RolePermissionsEditor
        open={editorOpen}
        role={editingRole}
        onClose={() => setEditorOpen(false)}
        onSaved={handleSaved}
      />

      <Dialog open={deleteTarget !== null} onClose={closeDeleteConfirm}>
        <DialogTitle>{t('admin.roles.deleteConfirmTitle')}</DialogTitle>
        <DialogContent>
          {deleteError && <Alert severity="error" sx={{ mb: 2 }}>{deleteError}</Alert>}
          <DialogContentText>
            {t('admin.roles.deleteConfirmBody', { name: deleteTarget?.display_name })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDeleteConfirm}>{t('admin.roles.btnCancel')}</Button>
          <Button color="error" onClick={confirmDelete}>
            {t('admin.roles.btnConfirmDelete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AdminRoles;
