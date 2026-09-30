/**
 * PortfolioTemplateEditor — dialog to create, edit or view a portfolio
 * template: master data → phases → criteria (TF-988).
 *
 * Modelled on `GradingSchemeEditor`. `PUT` replaces the whole template, so
 * create and update send the same full payload (`draftToPayload`).
 *
 * Once a portfolio assessment references the template, the backend refuses
 * any change to phases/criteria (409 `portfolio_template_phases_locked`)
 * while master data stays editable. The serializer does not say so up front,
 * so the editor learns it from the 409: it explains the lock, offers to
 * discard the phase changes, and then keeps the phases read-only. Unchanged
 * phases are sent back exactly as stored (`phasesPayloadFromTemplate`), so
 * a master-data-only save does not trip the lock.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  FormHelperText,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';

import { portfolioApi } from '../../../api/portfolioApi';
import { OrgUnitsService } from '../../../services/orgUnitsService';
import { useAuth } from '../../../contexts/AuthContext';
import { isAppError, translateError } from '../../../errors';
import type {
  PortfolioTemplate,
  PortfolioTemplateVisibility,
} from '../../../types/portfolio';
import PortfolioPhaseFields from './PortfolioPhaseFields';
import {
  criterionErrorsByName,
  DraftErrors,
  draftFromTemplate,
  draftToPayload,
  emptyDraft,
  emptyPhase,
  hasErrors,
  mergeErrors,
  moveItem,
  NAME_MAX_LENGTH,
  PhaseDraft,
  phasesPayloadFromTemplate,
  samePhases,
  TemplateDraft,
  validateDraft,
} from './templateDraft';

const KEY = 'pages.portfolio.templates.editor';
const NO_ERRORS: DraftErrors = { phases: {} };
const VISIBILITIES: PortfolioTemplateVisibility[] = ['private', 'team', 'institution', 'system'];

/** `null`: no conflict yet; `conflict`: 409 received; `reverted`: phase changes discarded. */
type PhaseLock = null | 'conflict' | 'reverted';

export interface PortfolioTemplateEditorProps {
  open: boolean;
  /** `null` creates a new template. */
  template: PortfolioTemplate | null;
  /** Non-owners only look (the backend would reject with 403/404). */
  readOnly: boolean;
  onClose: () => void;
  onSaved: (template: PortfolioTemplate) => void;
  /** The template no longer exists (404 on save); the list should refetch. */
  onDeleted: () => void;
}

const PortfolioTemplateEditor: React.FC<PortfolioTemplateEditorProps> = ({
  open,
  template,
  readOnly,
  onClose,
  onSaved,
  onDeleted,
}) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isEdit = template !== null;

  const [draft, setDraft] = useState<TemplateDraft>(emptyDraft);
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [serverErrors, setServerErrors] = useState<DraftErrors>(NO_ERRORS);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [phaseLock, setPhaseLock] = useState<PhaseLock>(null);

  useEffect(() => {
    if (!open) return;
    setDraft(template ? draftFromTemplate(template) : emptyDraft());
    setSubmitAttempted(false);
    setServerErrors(NO_ERRORS);
    setGeneralError(null);
    setPhaseLock(null);
  }, [open, template]);

  const orgUnits = useQuery({
    queryKey: ['orgUnits', 'mine'],
    queryFn: () => OrgUnitsService.mine(),
    enabled: open && draft.visibility === 'team',
  });
  const myOrgUnits = orgUnits.data?.items ?? [];

  const clientErrors = useMemo(
    () => (submitAttempted ? validateDraft(t, draft) : NO_ERRORS),
    [submitAttempted, t, draft],
  );
  const errors = mergeErrors(clientErrors, serverErrors);
  const phasesReadOnly = readOnly || phaseLock === 'reverted';

  const update = (patch: Partial<TemplateDraft>) => {
    setDraft((prev) => ({ ...prev, ...patch }));
    // A server error describes the payload that was sent, not the edited one.
    setServerErrors(NO_ERRORS);
  };
  const setPhases = (phases: PhaseDraft[]) => update({ phases });

  /** `sent` is the draft at save time: fields stay editable while saving. */
  const handleApiError = (err: unknown, sent: TemplateDraft) => {
    // Two literal keys, not a ternary: `i18n:check` only resolves literals.
    const message = isEdit
      ? translateError(err, t, 'errors.portfolio_template_update_failed')
      : translateError(err, t, 'errors.portfolio_template_create_failed');
    const code = isAppError(err) ? err.code : null;
    const criterion = isAppError(err) ? err.params?.criterion : undefined;
    setGeneralError(null);
    setServerErrors(NO_ERRORS);
    switch (code) {
      case 'portfolio_template_phases_locked':
        if (phaseLock === 'reverted') {
          // Unchanged phases are sent back as stored, so this should not
          // happen; if the backend still sees a difference, say so instead
          // of looping.
          setGeneralError(t(`${KEY}.phasesStillLocked`));
        } else {
          setPhaseLock('conflict');
        }
        return;
      case 'portfolio_template_not_found':
        // Deleted meanwhile: refresh the list behind the dialog.
        setGeneralError(message);
        onDeleted();
        return;
      case 'portfolio_template_incomplete_rubric':
      case 'portfolio_template_invalid_max_points': {
        const fieldErrors =
          criterion !== undefined
            ? criterionErrorsByName(
                sent,
                String(criterion),
                code === 'portfolio_template_invalid_max_points' ? 'maxPoints' : 'rubric',
                message,
              )
            : NO_ERRORS;
        setServerErrors(fieldErrors);
        // No matching criterion (renamed meanwhile): the message must not vanish.
        if (!hasErrors(fieldErrors)) setGeneralError(message);
        return;
      }
      case 'portfolio_template_org_unit_required':
      case 'portfolio_template_visibility_team_forbidden':
        setServerErrors({ orgUnit: message, phases: {} });
        return;
      case 'portfolio_template_visibility_system_forbidden':
        setServerErrors({ visibility: message, phases: {} });
        return;
      default:
        setGeneralError(message);
    }
  };

  const save = useMutation({
    mutationFn: ({ payload }: { payload: ReturnType<typeof draftToPayload>; sent: TemplateDraft }) =>
      template
        ? portfolioApi.updateTemplate(template.id, payload)
        : portfolioApi.createTemplate(payload),
    onSuccess: (saved) => {
      onSaved(saved);
      onClose();
    },
    onError: (err, { sent }) => handleApiError(err, sent),
  });

  const handleSave = () => {
    setSubmitAttempted(true);
    setGeneralError(null);
    setServerErrors(NO_ERRORS);
    if (hasErrors(validateDraft(t, draft))) return;
    const payload = draftToPayload(draft);
    if (template && samePhases(draft.phases, draftFromTemplate(template).phases)) {
      payload.phases = phasesPayloadFromTemplate(template);
    }
    save.mutate({ payload, sent: draft });
  };

  const revertPhases = () => {
    if (!template) return;
    update({ phases: draftFromTemplate(template).phases });
    setPhaseLock('reverted');
  };

  const visibilityOptions = VISIBILITIES.filter(
    (v) => v !== 'system' || user?.is_superuser || draft.visibility === 'system',
  );
  // An owner who left the org unit may still keep it (backend re-validates
  // membership only on a change), so the current value must stay selectable.
  const orgUnitOptions =
    draft.orgUnitId !== null && !myOrgUnits.some((ou) => ou.id === draft.orgUnitId)
      ? [...myOrgUnits, { id: draft.orgUnitId, name: t(`${KEY}.orgUnitFallback`, { id: draft.orgUnitId }) }]
      : myOrgUnits;

  const title = readOnly
    ? t(`${KEY}.titleView`)
    : isEdit
      ? t(`${KEY}.titleEdit`)
      : t(`${KEY}.titleCreate`);
  const showFieldHint = submitAttempted && hasErrors(errors) && !generalError;

  return (
    <Dialog
      open={open}
      onClose={save.isPending ? undefined : onClose}
      maxWidth="lg"
      fullWidth
      scroll="paper"
      aria-labelledby="pt-editor-title"
      data-testid="pt-editor-dialog"
    >
      <DialogTitle id="pt-editor-title">{title}</DialogTitle>

      <DialogContent dividers>
        <Stack spacing={3} sx={{ pt: 1 }}>
          {readOnly && (
            <Alert severity="info" data-testid="pt-editor-readonly">
              {t(`${KEY}.readOnlyHint`)}
            </Alert>
          )}
          {generalError && (
            <Alert severity="error" data-testid="pt-editor-error">
              {generalError}
            </Alert>
          )}
          {showFieldHint && (
            <Alert severity="error" data-testid="pt-editor-field-hint">
              {t(`${KEY}.fieldErrorsHint`)}
            </Alert>
          )}

          <TextField
            label={t(`${KEY}.name`)}
            value={draft.name}
            required
            fullWidth
            error={!!errors.name}
            helperText={errors.name}
            InputProps={{ readOnly }}
            inputProps={{ maxLength: NAME_MAX_LENGTH, 'data-testid': 'pt-field-name' }}
            onChange={(e) => update({ name: e.target.value })}
          />
          <TextField
            label={t(`${KEY}.description`)}
            value={draft.description}
            fullWidth
            multiline
            minRows={2}
            InputProps={{ readOnly }}
            inputProps={{ 'data-testid': 'pt-field-description' }}
            onChange={(e) => update({ description: e.target.value })}
          />

          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <TextField
              select
              label={t(`${KEY}.visibility`)}
              value={draft.visibility}
              disabled={readOnly}
              error={!!errors.visibility}
              helperText={errors.visibility}
              sx={{ minWidth: 220 }}
              inputProps={{ 'data-testid': 'pt-field-visibility' }}
              onChange={(e) => {
                const visibility = e.target.value as PortfolioTemplateVisibility;
                // Leaving 'team' drops the org unit (DB CHECK: set exactly for team).
                update({ visibility, orgUnitId: visibility === 'team' ? draft.orgUnitId : null });
              }}
            >
              {visibilityOptions.map((v) => (
                <MenuItem key={v} value={v}>
                  {t(`pages.portfolio.templates.visibility.${v}`)}
                </MenuItem>
              ))}
            </TextField>

            {draft.visibility === 'team' && (
              <Box>
                <TextField
                  select
                  label={t(`${KEY}.orgUnit`)}
                  value={draft.orgUnitId ?? ''}
                  required
                  disabled={readOnly || orgUnitOptions.length === 0}
                  error={!!errors.orgUnit}
                  sx={{ minWidth: 240 }}
                  inputProps={{ 'data-testid': 'pt-field-org-unit' }}
                  onChange={(e) =>
                    update({ orgUnitId: e.target.value === '' ? null : Number(e.target.value) })
                  }
                >
                  {orgUnitOptions.map((ou) => (
                    <MenuItem key={ou.id} value={ou.id}>
                      {ou.name}
                    </MenuItem>
                  ))}
                </TextField>
                {orgUnits.isError ? (
                  // Before `errors.orgUnit`: «choose one» is useless when the
                  // list failed to load and the select is disabled.
                  <FormHelperText error data-testid="pt-field-org-unit-load-error">
                    {t(`${KEY}.orgUnitsLoadError`)}{' '}
                    <Button size="small" onClick={() => orgUnits.refetch()} sx={{ p: 0, minWidth: 0 }}>
                      {t(`${KEY}.retry`)}
                    </Button>
                  </FormHelperText>
                ) : errors.orgUnit ? (
                  <FormHelperText error data-testid="pt-field-org-unit-error">
                    {errors.orgUnit}
                  </FormHelperText>
                ) : !orgUnits.isLoading && myOrgUnits.length === 0 && !readOnly ? (
                  <FormHelperText>{t(`${KEY}.noOrgUnit`)}</FormHelperText>
                ) : null}
              </Box>
            )}

            <FormControlLabel
              control={
                <Switch
                  checked={draft.isActive}
                  disabled={readOnly}
                  onChange={(e) => update({ isActive: e.target.checked })}
                  inputProps={{ 'data-testid': 'pt-field-active' } as React.InputHTMLAttributes<HTMLInputElement>}
                />
              }
              label={t(`${KEY}.active`)}
            />
          </Box>

          <Divider />

          <Box>
            <Typography variant="h6" component="h2">
              {t(`${KEY}.phases`)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t(`${KEY}.phasesHelper`)}
            </Typography>
          </Box>

          {phaseLock !== null && (
            <Alert
              severity="warning"
              data-testid="pt-editor-phases-locked"
              action={
                phaseLock === 'conflict' ? (
                  <Button color="inherit" size="small" onClick={revertPhases} data-testid="pt-editor-revert-phases">
                    {t(`${KEY}.revertPhases`)}
                  </Button>
                ) : undefined
              }
            >
              {t(`${KEY}.phasesLocked`)}
              {phaseLock === 'reverted' && ` ${t(`${KEY}.phasesReverted`)}`}
            </Alert>
          )}

          {draft.phases.map((phase, index) => (
            <PortfolioPhaseFields
              key={phase.key}
              phase={phase}
              index={index}
              count={draft.phases.length}
              readOnly={phasesReadOnly}
              errors={errors.phases[phase.key]}
              onChange={(next) => setPhases(draft.phases.map((p) => (p.key === phase.key ? next : p)))}
              onMove={(delta) => setPhases(moveItem(draft.phases, index, delta))}
              onRemove={() => setPhases(draft.phases.filter((p) => p.key !== phase.key))}
            />
          ))}

          {!phasesReadOnly && (
            <Box>
              <Button
                startIcon={<AddIcon />}
                onClick={() => setPhases([...draft.phases, emptyPhase()])}
                data-testid="pt-add-phase"
              >
                {t(`${KEY}.addPhase`)}
              </Button>
            </Box>
          )}
        </Stack>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={save.isPending} data-testid="pt-editor-cancel">
          {readOnly ? t(`${KEY}.close`) : t(`${KEY}.cancel`)}
        </Button>
        {!readOnly && (
          <Button
            variant="contained"
            onClick={handleSave}
            // After the 409 a retry would fail the same way until the phase
            // changes are discarded.
            disabled={save.isPending || phaseLock === 'conflict'}
            startIcon={save.isPending ? <CircularProgress size={16} /> : undefined}
            data-testid="pt-editor-save"
          >
            {save.isPending ? t(`${KEY}.saving`) : t(`${KEY}.save`)}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default PortfolioTemplateEditor;
