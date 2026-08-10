/**
 * OrgUnitEditor — create/edit dialog for organizational units (Stufe 0 Fundament).
 *
 * Same component handles create (orgUnit === null) and edit, mirroring
 * GradingSchemeEditor. Parent selection excludes the unit itself and all of
 * its own descendants (cycle prevention is enforced server-side too, but a
 * client-side filter avoids submitting an obviously invalid choice).
 *
 * unit_type is immutable after creation (disabled on edit) — the PATCH API
 * does not support changing it (see Global Constraints in the plan). It is a
 * fixed dropdown (KNOWN_UNIT_TYPES), not free text — the storage column
 * itself stays a free string on purpose (see models/org_unit.py, adding a
 * level is a one-line backend constant change, no migration), but the UI
 * shouldn't let an admin typo a new "level" into existence by accident.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  TextField,
} from '@mui/material';

import { OrgUnitOut } from '../../types/orgUnit';
import { OrgUnitsService } from '../../services/orgUnitsService';
import { ApiError } from '../../services/submissionsService';

export interface OrgUnitEditorProps {
  open: boolean;
  orgUnit: OrgUnitOut | null;
  allOrgUnits: OrgUnitOut[];
  onClose: () => void;
  onSaved: () => void;
}

// Mirrors KNOWN_UNIT_TYPES in models/org_unit.py — keep both lists in sync
// when Stufe 1/2 introduces a new level.
const UNIT_TYPES = ['abteilung', 'team'] as const;

function descendantIds(units: OrgUnitOut[], rootId: number): Set<number> {
  const byParent = new Map<number | null, OrgUnitOut[]>();
  units.forEach(u => {
    const list = byParent.get(u.parent_org_unit_id) ?? [];
    list.push(u);
    byParent.set(u.parent_org_unit_id, list);
  });
  const result = new Set<number>();
  const stack = [rootId];
  while (stack.length > 0) {
    const current = stack.pop()!;
    result.add(current);
    (byParent.get(current) ?? []).forEach(child => stack.push(child.id));
  }
  return result;
}

const OrgUnitEditor: React.FC<OrgUnitEditorProps> = ({
  open,
  orgUnit,
  allOrgUnits,
  onClose,
  onSaved,
}) => {
  const { t } = useTranslation();
  const isEdit = orgUnit !== null;

  const [name, setName] = useState('');
  const [unitType, setUnitType] = useState('');
  const [parentOrgUnitId, setParentOrgUnitId] = useState<number | ''>('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (orgUnit) {
      setName(orgUnit.name);
      setUnitType(orgUnit.unit_type);
      setParentOrgUnitId(orgUnit.parent_org_unit_id ?? '');
    } else {
      setName('');
      setUnitType('');
      setParentOrgUnitId('');
    }
    setError(null);
  }, [open, orgUnit]);

  const excludedParentIds = useMemo(
    () => (orgUnit ? descendantIds(allOrgUnits, orgUnit.id) : new Set<number>()),
    [orgUnit, allOrgUnits],
  );

  const parentOptions = allOrgUnits.filter(u => !excludedParentIds.has(u.id));

  const validate = (): string | null => {
    if (name.trim().length === 0) return t('admin.orgUnits.validationNameRequired');
    if (unitType.trim().length === 0) return t('admin.orgUnits.validationUnitTypeRequired');
    return null;
  };

  const handleSave = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const parentValue = parentOrgUnitId === '' ? null : parentOrgUnitId;
      if (isEdit && orgUnit) {
        await OrgUnitsService.update(orgUnit.id, {
          name,
          parent_org_unit_id: parentValue,
          move_to_root: parentValue === null,
        });
      } else {
        await OrgUnitsService.create({
          name,
          unit_type: unitType,
          parent_org_unit_id: parentValue,
        });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t(isEdit ? 'admin.orgUnits.failedUpdate' : 'admin.orgUnits.failedCreate'),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth data-testid="ou-editor-dialog">
      <DialogTitle>
        {isEdit ? t('admin.orgUnits.editorTitleEdit') : t('admin.orgUnits.editorTitleCreate')}
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} data-testid="ou-editor-error">
            {error}
          </Alert>
        )}
        <TextField
          label={t('admin.orgUnits.fieldName')}
          value={name}
          onChange={e => setName(e.target.value)}
          fullWidth
          margin="normal"
          inputProps={{ 'data-testid': 'ou-editor-field-name' }}
        />
        <TextField
          select
          label={t('admin.orgUnits.fieldUnitType')}
          value={unitType}
          onChange={e => setUnitType(e.target.value)}
          fullWidth
          margin="normal"
          disabled={isEdit}
          SelectProps={{ 'data-testid': 'ou-editor-field-unit-type' } as never}
        >
          {UNIT_TYPES.map(type => (
            <MenuItem key={type} value={type}>
              {t(`admin.orgUnits.unitType_${type}`)}
            </MenuItem>
          ))}
          {/* Edit mode may show a unit_type outside the current dropdown
              (a future Stufe-1/2 level, or legacy data) — render it as-is
              rather than leaving the disabled select blank. */}
          {isEdit && unitType !== '' && !UNIT_TYPES.includes(unitType as typeof UNIT_TYPES[number]) && (
            <MenuItem value={unitType}>{unitType}</MenuItem>
          )}
        </TextField>
        <TextField
          select
          label={t('admin.orgUnits.fieldParent')}
          value={parentOrgUnitId}
          onChange={e =>
            setParentOrgUnitId(e.target.value === '' ? '' : Number(e.target.value))
          }
          fullWidth
          margin="normal"
          SelectProps={{ 'data-testid': 'ou-editor-field-parent' } as never}
        >
          <MenuItem value="">{t('admin.orgUnits.fieldParentNone')}</MenuItem>
          {parentOptions.map(option => (
            <MenuItem key={option.id} value={option.id}>
              {option.name}
            </MenuItem>
          ))}
        </TextField>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving} data-testid="ou-editor-btn-cancel">
          {t('admin.orgUnits.btnCancel')}
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saving}
          data-testid="ou-editor-btn-save"
        >
          {saving ? t('admin.orgUnits.btnSaving') : t('admin.orgUnits.btnSave')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default OrgUnitEditor;
