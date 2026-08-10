/**
 * RolePermissionsEditor — Create/Edit-Dialog für Rollen (TF-603).
 *
 * Name ist nur im Create-Modus editierbar (role === null); im Edit-Modus
 * gesperrt, auch für Nicht-System-Rollen — die Backend-API akzeptiert
 * ohnehin kein `name`-Feld im Update (siehe api/admin.py: UpdateRoleRequest).
 * Berechtigungen bleiben bei Systemrollen editierbar (das ist der eigentliche
 * Zweck dieses Tickets), nur das Löschen ist für sie gesperrt (siehe AdminRoles.tsx).
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Button,
  TextField,
  FormControlLabel,
  FormGroup,
  Typography,
  Box,
  Alert,
} from '@mui/material';
import { RolesService } from '../../services/rolesService';
import { ApiError } from '../../services/httpClient';
import { RoleOut, PermissionOut } from '../../types/role';

interface RolePermissionsEditorProps {
  open: boolean;
  role: RoleOut | null;
  onClose: () => void;
  onSaved: () => void;
}

const RolePermissionsEditor: React.FC<RolePermissionsEditorProps> = ({
  open,
  role,
  onClose,
  onSaved,
}) => {
  const { t } = useTranslation();
  const isEdit = role !== null;

  const [permissions, setPermissions] = useState<PermissionOut[]>([]);
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadPermissions = useCallback(async () => {
    try {
      const list = await RolesService.listPermissions();
      setPermissions(list);
    } catch (e) {
      // Unbehandelt würde dies den Dialog mit einer leeren Checkbox-Liste
      // zurücklassen — ununterscheidbar von einer Rolle ohne Berechtigungen.
      // eslint-disable-next-line no-console
      console.error('Failed to load permission list', e);
      setError(t('admin.roles.failedLoadPermissions'));
    }
  }, [t]);

  useEffect(() => {
    if (!open) return;
    loadPermissions();
    setName(role?.name ?? '');
    setDisplayName(role?.display_name ?? '');
    setDescription(role?.description ?? '');
    setSelected(new Set(role?.permissions ?? []));
    setError(null);
  }, [open, role, loadPermissions]);

  const grouped = useMemo(() => {
    const byCategory = new Map<string, PermissionOut[]>();
    permissions.forEach((p) => {
      const list = byCategory.get(p.category) ?? [];
      list.push(p);
      byCategory.set(p.category, list);
    });
    return byCategory;
  }, [permissions]);

  const togglePermission = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      if (isEdit && role) {
        await RolesService.update(role.id, {
          display_name: displayName,
          description,
          permissions: Array.from(selected),
        });
      } else {
        await RolesService.create({
          name,
          display_name: displayName,
          description: description || null,
          permissions: Array.from(selected),
        });
      }
      onSaved();
    } catch (e) {
      // Backend liefert bei 409 (Duplikat) / 422 (unbekannte Permission)
      // eine aussagekräftige detail-Message — die zeigen wir statt des
      // generischen Fallbacks. Netzwerkfehler (kein `.detail`) fallen
      // weiterhin auf den generischen i18n-String zurück (TF-603 Finding 4).
      if (e instanceof ApiError && typeof e.detail === 'string' && e.detail) {
        setError(e.detail);
      } else {
        setError(isEdit ? t('admin.roles.failedUpdate') : t('admin.roles.failedCreate'));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {isEdit ? t('admin.roles.editorTitleEdit') : t('admin.roles.editorTitleCreate')}
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label={t('admin.roles.fieldName')}
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isEdit}
            helperText={isEdit ? t('admin.roles.nameLockedHint') : undefined}
            fullWidth
          />
          <TextField
            label={t('admin.roles.fieldDisplayName')}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            fullWidth
          />
          <TextField
            label={t('admin.roles.fieldDescription')}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            fullWidth
            multiline
            minRows={2}
          />
        </Box>
        <Typography variant="subtitle1" sx={{ mt: 3, mb: 1 }}>
          {t('admin.roles.fieldPermissions')}
        </Typography>
        {Array.from(grouped.entries()).map(([category, categoryPermissions]) => (
          <Box key={category} sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              {category}
            </Typography>
            <FormGroup>
              {categoryPermissions.map((p) => (
                <FormControlLabel
                  key={p.key}
                  control={
                    <Checkbox
                      checked={selected.has(p.key)}
                      onChange={() => togglePermission(p.key)}
                    />
                  }
                  label={p.label}
                />
              ))}
            </FormGroup>
          </Box>
        ))}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          {t('admin.roles.btnCancel')}
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saving || !name || !displayName}
        >
          {saving ? t('admin.roles.btnSaving') : t('admin.roles.btnSave')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RolePermissionsEditor;
