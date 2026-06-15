/**
 * Notenexport-Panel — TF-335 Spec 9.
 *
 * Drei Formate (CSV / Moodle-CSV / PDF) per Radio. Download-Button
 * deaktiviert solange noch Submissions im Status `pending_review` oder
 * `partially_reviewed` sind — der Backend-Endpoint blockiert mit 409
 * (i18n key `submissions_grade_export_blocked_pending_review`), aber
 * wir spiegeln die Sperre auch im UI, damit der Button nicht
 * scheinbar nichts tut.
 *
 * Ein Hinweis-Banner mit Link zur Review-Queue zeigt sich, wenn der
 * Export aktuell blockiert ist.
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  FormControlLabel,
  FormLabel,
  InputLabel,
  Link,
  ListSubheader,
  MenuItem,
  Paper,
  Radio,
  RadioGroup,
  Select,
  Typography,
} from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

import {
  ExportFormat,
  GradeExportService,
} from '../../services/gradeExportService';
import { ComposerService } from '../../services/ComposerService';
import { GradingSchemesService } from '../../services/gradingSchemesService';
import { GradingSchemeOut } from '../../types/gradingScheme';
import { ApiError } from '../../services/submissionsService';
import { useAuth } from '../../contexts/AuthContext';

interface NotenexportPanelProps {
  examId: number;
  /**
   * Counts surfaced from the submissions list so we can show the
   * review-progress hint without fetching anything extra. The export
   * is unlocked when ``pendingCount === 0``.
   */
  totalSubmissions: number;
  pendingCount: number;
  /** Click handler: opens the Review tab so the user can clear the queue. */
  onOpenReview?: () => void;
}

const FORMATS: ExportFormat[] = ['csv', 'moodle_csv', 'pdf'];

const NotenexportPanel: React.FC<NotenexportPanelProps> = ({
  examId,
  totalSubmissions,
  pendingCount,
  onOpenReview,
}) => {
  const { t } = useTranslation();
  const { hasPermission } = useAuth();
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reassigning the scheme goes through PATCH /exams/{id}/grading-scheme,
  // which requires ``create_exams``. The export tab itself is reachable with
  // only ``submissions:read`` (e.g. the Assistant role), so a reviewer without
  // ``create_exams`` would otherwise see a picker that 403s on save. Gate the
  // whole picker on the same permission the endpoint enforces.
  const canAssignScheme = hasPermission('create_exams');

  // Per-exam grading scheme (TF-432). The scheme picker is an enhancement on
  // top of the export — a failed scheme/exam fetch must never block the
  // download itself, so it lives behind its own ``schemeReady`` flag.
  const [schemes, setSchemes] = useState<GradingSchemeOut[]>([]);
  const [schemeId, setSchemeId] = useState<number | null>(null);
  const [examUpdatedAt, setExamUpdatedAt] = useState<string | null>(null);
  const [schemeReady, setSchemeReady] = useState(false);
  const [savingScheme, setSavingScheme] = useState(false);
  const [schemeMsg, setSchemeMsg] = useState<{
    severity: 'success' | 'error';
    text: string;
  } | null>(null);

  useEffect(() => {
    // Skip the fetch entirely for users who can't reassign — they never see
    // the picker, so there's no point loading schemes or the exam metadata.
    if (!canAssignScheme) {
      setSchemeReady(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [schemesResp, exam] = await Promise.all([
          GradingSchemesService.list(true),
          ComposerService.getExam(examId),
        ]);
        if (cancelled) return;
        setSchemes(schemesResp.schemes);
        setSchemeId(exam.grading_scheme_id ?? null);
        setExamUpdatedAt(exam.updated_at);
        setSchemeReady(true);
      } catch (err) {
        // Enhancement only — leave the picker hidden, keep export working.
        // Log so an auth/permission/network failure is observable instead of
        // collapsing silently into "the picker just isn't there".
        if (!cancelled) {
          setSchemeReady(false);
          console.warn(
            'NotenexportPanel: grading-scheme metadata load failed',
            err,
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [examId, canAssignScheme]);

  const handleSchemeChange = async (value: number | null) => {
    setSavingScheme(true);
    setSchemeMsg(null);
    try {
      const updated = await ComposerService.updateExamGradingScheme(examId, {
        grading_scheme_id: value,
        // ``examUpdatedAt`` is always populated before the picker is
        // interactable (set together with ``schemeReady`` on load), and the
        // backend requires it for optimistic locking.
        updated_at: examUpdatedAt ?? '',
      });
      setSchemeId(updated.grading_scheme_id ?? null);
      setExamUpdatedAt(updated.updated_at);
      setSchemeMsg({
        severity: 'success',
        text: t('auswertungen.export.gradingSchemeSaved'),
      });
    } catch (err) {
      // Optimistic-lock clash (409): the exam changed under us. Reload so
      // the next attempt carries a fresh updated_at, and tell the user.
      // ``updateExamGradingScheme`` goes through the raw axios ``apiClient``
      // (status on ``err.response.status``), but read ``ApiError.status`` too
      // so the 409 branch survives a future switch to a safeFetch-style wrapper.
      const status =
        err instanceof ApiError
          ? err.status
          : (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        try {
          const exam = await ComposerService.getExam(examId);
          setSchemeId(exam.grading_scheme_id ?? null);
          setExamUpdatedAt(exam.updated_at);
        } catch {
          /* keep stale value; user can retry */
        }
        setSchemeMsg({
          severity: 'error',
          text: t('auswertungen.export.gradingSchemeConflict'),
        });
      } else {
        setSchemeMsg({
          severity: 'error',
          text: t('auswertungen.export.gradingSchemeError'),
        });
      }
    } finally {
      setSavingScheme(false);
    }
  };

  const blocked = pendingCount > 0 || totalSubmissions === 0;

  const handleDownload = async () => {
    setDownloading(true);
    setError(null);
    try {
      const { blob, filename } = await GradeExportService.download(
        examId,
        format,
      );
      // Trigger browser download via temporary anchor.
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      if (err instanceof ApiError) {
        // Branch on err.kind so the lehrperson sees an actionable
        // message instead of "Export failed (500)". Conflict (409)
        // surfaces the backend's translated detail directly because
        // it carries the specific reason (pending review vs. draft
        // status vs. "etwas anderes").
        switch (err.kind) {
          case 'auth':
            setError(t('auswertungen.export.errorAuth'));
            break;
          case 'permission':
            setError(t('auswertungen.export.errorPermission'));
            break;
          case 'not_found':
            setError(t('auswertungen.export.errorNotFound'));
            break;
          case 'conflict':
            setError(err.message);
            break;
          default:
            setError(t('auswertungen.export.errorServer'));
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t('auswertungen.export.unexpectedError'));
      }
    } finally {
      setDownloading(false);
    }
  };

  const reviewHint = useMemo(() => {
    if (totalSubmissions === 0) {
      return t('auswertungen.export.noSubmissionsHint');
    }
    if (pendingCount > 0) {
      return t('auswertungen.export.pendingReviewHint', {
        count: pendingCount,
      });
    }
    return null;
  }, [pendingCount, totalSubmissions, t]);

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        {t('auswertungen.export.title')}
      </Typography>

      {reviewHint && (
        <Alert
          severity="warning"
          sx={{ mb: 3 }}
          data-testid="notenexport-blocked-hint"
        >
          {reviewHint}{' '}
          {pendingCount > 0 && onOpenReview && (
            <Link
              component="button"
              onClick={onOpenReview}
              data-testid="notenexport-open-review"
            >
              {t('auswertungen.export.openReviewQueue')}
            </Link>
          )}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} data-testid="notenexport-error">
          {error}
        </Alert>
      )}

      {schemeReady && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <FormControl fullWidth size="small">
            <InputLabel id="exam-grading-scheme-label">
              {t('auswertungen.export.gradingSchemeLabel')}
            </InputLabel>
            <Select
              labelId="exam-grading-scheme-label"
              label={t('auswertungen.export.gradingSchemeLabel')}
              value={schemeId ?? ''}
              disabled={savingScheme}
              onChange={(e) =>
                handleSchemeChange(
                  e.target.value === '' ? null : Number(e.target.value),
                )
              }
              data-testid="exam-grading-scheme-select"
            >
              <MenuItem value="">
                <em>{t('auswertungen.export.gradingSchemeInherit')}</em>
              </MenuItem>
              {schemes.some((s) => s.is_system_scheme) && (
                <ListSubheader>
                  {t('auswertungen.export.gradingSchemeSystemGroup')}
                </ListSubheader>
              )}
              {schemes
                .filter((s) => s.is_system_scheme)
                .map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    {s.name}
                  </MenuItem>
                ))}
              {schemes.some((s) => !s.is_system_scheme) && (
                <ListSubheader>
                  {t('auswertungen.export.gradingSchemeInstitutionGroup')}
                </ListSubheader>
              )}
              {schemes
                .filter((s) => !s.is_system_scheme)
                .map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    {s.name}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>
          {schemeMsg && (
            <Alert
              severity={schemeMsg.severity}
              sx={{ mt: 2 }}
              data-testid="exam-grading-scheme-msg"
            >
              {schemeMsg.text}
            </Alert>
          )}
        </Paper>
      )}

      <Paper sx={{ p: 3, mb: 3 }}>
        <FormControl>
          <FormLabel>{t('auswertungen.export.formatLabel')}</FormLabel>
          <RadioGroup
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
            data-testid="notenexport-format-radio"
          >
            {FORMATS.map((f) => (
              <FormControlLabel
                key={f}
                value={f}
                control={<Radio />}
                label={t(`auswertungen.export.format.${f}`)}
                data-testid={`notenexport-format-${f}`}
              />
            ))}
          </RadioGroup>
        </FormControl>
      </Paper>

      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
        <Button
          variant="contained"
          startIcon={
            downloading ? (
              <CircularProgress size={16} color="inherit" />
            ) : (
              <DownloadIcon />
            )
          }
          disabled={blocked || downloading}
          onClick={handleDownload}
          data-testid="notenexport-download-button"
        >
          {t('auswertungen.export.downloadButton')}
        </Button>
        <Typography variant="body2" color="text.secondary">
          {t('auswertungen.export.summary', {
            total: totalSubmissions,
            pending: pendingCount,
          })}
        </Typography>
      </Box>
    </Box>
  );
};

export default NotenexportPanel;
