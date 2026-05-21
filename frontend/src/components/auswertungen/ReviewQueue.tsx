/**
 * Review-Queue (Spec 6.4 / TF-334).
 *
 * Listet alle ``status='proposed'``-Grades für ``open_ended``-Antworten
 * der ausgewählten Prüfung auf. Sortierung nach Konfidenz (NULL +
 * niedrig zuerst — dort braucht es Lehrperson-Aufmerksamkeit). Filter:
 * Konfidenz-Range, Frage, Studi. Aktionen pro Eintrag: Übernehmen,
 * Anpassen (öffnet Inline-Editor), "Im Kontext" (Hand-off an die
 * Submissions-Detailansicht).
 *
 * Bulk-Aktion: explizit getriggert (kein Auto-Approve, Spec 6.4
 * Abgrenzung). Schwelle als Konfidenz-Slider, plus Auswahl-basierter
 * Pfad für Lehrperson, die einzelne Items "abhaken" will.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Snackbar,
  Stack,
  Typography,
} from '@mui/material';
import {
  CheckCircle as ApproveIcon,
  Edit as OverrideIcon,
  OpenInNew as ContextIcon,
} from '@mui/icons-material';

import { GradesService } from '../../services/gradesService';
import { ApiError } from '../../services/submissionsService';
import { ReviewQueueItem } from '../../types/submission';
import OverrideGradeDialog from './OverrideGradeDialog';

// Untere Grenze für die Bulk-Konfidenz-Schwelle: 0% würde alle
// proposed-Grades inklusive der Fail-Soft-Stubs (confidence=0.0)
// einsammeln — Lehrperson soll das nicht versehentlich auslösen.
const MIN_BULK_THRESHOLD = 50;
const SNACKBAR_AUTOHIDE_MS = 5000;

interface Props {
  examId: number;
  /** Optional callback when the user picks "in context" — parent can
   *  open the submissions detail drawer for the linked submission. */
  onOpenSubmission?: (submissionId: number) => void;
  /** Optional notify on counts so the parent tab label can update. */
  onTotalChange?: (total: number) => void;
}

const ReviewQueue: React.FC<Props> = ({
  examId,
  onOpenSubmission,
  onTotalChange,
}) => {
  const { t } = useTranslation();

  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confidenceMin, setConfidenceMin] = useState(0);
  const [confidenceMax, setConfidenceMax] = useState(100);
  const [questionFilter, setQuestionFilter] = useState<number | ''>('');
  const [studentFilter, setStudentFilter] = useState<number | ''>('');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkThreshold, setBulkThreshold] = useState(80);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [overrideItem, setOverrideItem] = useState<ReviewQueueItem | null>(null);
  const [snack, setSnack] = useState<string | null>(null);
  const [snackErr, setSnackErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await GradesService.getReviewQueue(examId, {
        confidence_min: confidenceMin > 0 ? confidenceMin / 100 : undefined,
        confidence_max: confidenceMax < 100 ? confidenceMax / 100 : undefined,
        question_id: questionFilter === '' ? undefined : questionFilter,
        student_id: studentFilter === '' ? undefined : studentFilter,
      });
      setItems(result.items);
      setTotal(result.total);
      onTotalChange?.(result.total);
      // Selection ausmisten — verschwundene IDs nicht mehr auswählbar.
      setSelected((prev) => {
        const next = new Set<number>();
        for (const it of result.items) {
          if (prev.has(it.grade_id)) next.add(it.grade_id);
        }
        return next;
      });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t('auswertungen.exam.review.loadError'),
      );
    } finally {
      setLoading(false);
    }
    // ``t`` aus den Deps gelassen (siehe AuswertungenExam.tsx Begründung).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId, confidenceMin, confidenceMax, questionFilter, studentFilter]);

  useEffect(() => {
    reload();
  }, [reload]);

  // Distinct question + student facets aus aktueller Item-Liste —
  // einfach genug ohne separaten Endpoint, solange die Queue
  // begrenzt ist (Default 200, Hard-Cap 1000).
  const questionOptions = useMemo(() => {
    const map = new Map<number, string>();
    for (const it of items) {
      if (!map.has(it.exam_question_id)) {
        map.set(
          it.exam_question_id,
          it.question_text.length > 80
            ? `${it.question_text.slice(0, 80)}…`
            : it.question_text,
        );
      }
    }
    return Array.from(map.entries());
  }, [items]);

  const studentOptions = useMemo(() => {
    const map = new Map<number, string>();
    for (const it of items) {
      if (!map.has(it.student_id)) {
        map.set(
          it.student_id,
          it.student_display_name ?? it.student_external_id,
        );
      }
    }
    return Array.from(map.entries());
  }, [items]);

  const handleApprove = async (item: ReviewQueueItem) => {
    try {
      await GradesService.approve(item.grade_id);
      setSnack(t('auswertungen.exam.review.actionApproveSuccess'));
      await reload();
    } catch (err) {
      setSnackErr(
        err instanceof ApiError
          ? err.message
          : t('auswertungen.exam.review.actionFailure'),
      );
    }
  };

  const handleOverrideSuccess = async () => {
    setSnack(t('auswertungen.exam.review.actionOverrideSuccess'));
    await reload();
  };

  const toggleSelect = (gradeId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(gradeId)) next.delete(gradeId);
      else next.add(gradeId);
      return next;
    });
  };

  const handleBulkByThreshold = async () => {
    const threshold = bulkThreshold / 100;
    const eligible = items.filter(
      (it) => (it.confidence ?? -1) >= threshold,
    );
    // Confirm-Dialog ist bewusst nur ein window.confirm — kein neuer
    // Modal-Flow für das hier; die Queue ist sichtbar, der Schwellwert
    // ist sichtbar, und der Snackbar-Toast meldet den Erfolg.
    if (
      !window.confirm(
        t('auswertungen.exam.review.bulk.confirmThreshold', {
          count: eligible.length,
          threshold: bulkThreshold,
        }),
      )
    ) {
      return;
    }
    setBulkBusy(true);
    try {
      const result = await GradesService.bulkApprove({
        examId,
        confidenceMin: threshold,
      });
      setSnack(
        t('auswertungen.exam.review.bulk.success', {
          count: result.approved_count,
        }),
      );
      await reload();
    } catch (err) {
      setSnackErr(
        err instanceof ApiError
          ? err.message
          : t('auswertungen.exam.review.actionFailure'),
      );
    } finally {
      setBulkBusy(false);
    }
  };

  const handleBulkBySelection = async () => {
    if (selected.size === 0) return;
    setBulkBusy(true);
    try {
      const result = await GradesService.bulkApprove({
        examId,
        gradeIds: Array.from(selected),
      });
      setSelected(new Set());
      setSnack(
        t('auswertungen.exam.review.bulk.success', {
          count: result.approved_count,
        }),
      );
      await reload();
    } catch (err) {
      setSnackErr(
        err instanceof ApiError
          ? err.message
          : t('auswertungen.exam.review.actionFailure'),
      );
    } finally {
      setBulkBusy(false);
    }
  };

  return (
    <Box data-testid="review-queue">
      {/* Filters */}
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            spacing={2}
            alignItems={{ md: 'center' }}
          >
            <Box sx={{ minWidth: 240, flexGrow: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {t('auswertungen.exam.review.filterConfidence')}
              </Typography>
              <Slider
                value={[confidenceMin, confidenceMax]}
                onChange={(_, value) => {
                  if (Array.isArray(value)) {
                    setConfidenceMin(value[0]);
                    setConfidenceMax(value[1]);
                  }
                }}
                valueLabelDisplay="auto"
                valueLabelFormat={(v) => `${v}%`}
                aria-label="confidence range"
                data-testid="filter-confidence"
              />
            </Box>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel id="filter-question-label">
                {t('auswertungen.exam.review.filterQuestion')}
              </InputLabel>
              <Select
                labelId="filter-question-label"
                value={questionFilter}
                label={t('auswertungen.exam.review.filterQuestion')}
                onChange={(e) =>
                  setQuestionFilter(
                    e.target.value === '' ? '' : Number(e.target.value),
                  )
                }
                data-testid="filter-question"
              >
                <MenuItem value="">
                  {t('auswertungen.exam.review.filterAllQuestions')}
                </MenuItem>
                {questionOptions.map(([id, text]) => (
                  <MenuItem key={id} value={id}>
                    {text}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel id="filter-student-label">
                {t('auswertungen.exam.review.filterStudent')}
              </InputLabel>
              <Select
                labelId="filter-student-label"
                value={studentFilter}
                label={t('auswertungen.exam.review.filterStudent')}
                onChange={(e) =>
                  setStudentFilter(
                    e.target.value === '' ? '' : Number(e.target.value),
                  )
                }
                data-testid="filter-student"
              >
                <MenuItem value="">
                  {t('auswertungen.exam.review.filterAllStudents')}
                </MenuItem>
                {studentOptions.map(([id, name]) => (
                  <MenuItem key={id} value={id}>
                    {name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              size="small"
              onClick={() => {
                setConfidenceMin(0);
                setConfidenceMax(100);
                setQuestionFilter('');
                setStudentFilter('');
              }}
            >
              {t('auswertungen.exam.review.filterClear')}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Bulk-Bar */}
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            spacing={2}
            alignItems={{ md: 'center' }}
          >
            <Typography variant="subtitle2" sx={{ minWidth: 120 }}>
              {t('auswertungen.exam.review.bulk.title')}
            </Typography>
            <Box sx={{ minWidth: 220, flexGrow: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {t('auswertungen.exam.review.bulk.thresholdLabel')}{' '}
                {bulkThreshold}%
              </Typography>
              <Slider
                value={bulkThreshold}
                onChange={(_, v) => {
                  if (typeof v === 'number') setBulkThreshold(v);
                }}
                min={MIN_BULK_THRESHOLD}
                max={100}
                valueLabelDisplay="auto"
                aria-label="bulk threshold"
                data-testid="bulk-threshold"
              />
            </Box>
            <Button
              variant="outlined"
              onClick={handleBulkByThreshold}
              disabled={bulkBusy}
              data-testid="bulk-apply-threshold"
            >
              {t('auswertungen.exam.review.bulk.applyByThreshold')}
            </Button>
            <Button
              variant="contained"
              onClick={handleBulkBySelection}
              disabled={bulkBusy || selected.size === 0}
              data-testid="bulk-apply-selection"
            >
              {t('auswertungen.exam.review.bulk.applyBySelection', {
                count: selected.size,
              })}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Snackbar
        open={!!snack}
        autoHideDuration={SNACKBAR_AUTOHIDE_MS}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="success" onClose={() => setSnack(null)}>
          {snack}
        </Alert>
      </Snackbar>
      <Snackbar
        open={!!snackErr}
        autoHideDuration={SNACKBAR_AUTOHIDE_MS}
        onClose={() => setSnackErr(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="error" onClose={() => setSnackErr(null)}>
          {snackErr}
        </Alert>
      </Snackbar>

      <Box sx={{ mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {t('auswertungen.exam.review.totalCount', { count: total })}
        </Typography>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : items.length === 0 ? (
        <Alert severity="success">
          {t('auswertungen.exam.review.emptyHint')}
        </Alert>
      ) : (
        <Stack spacing={2}>
          {items.map((item) => (
            <Card
              key={item.grade_id}
              variant="outlined"
              data-testid={`review-card-${item.grade_id}`}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                  <Checkbox
                    checked={selected.has(item.grade_id)}
                    onChange={() => toggleSelect(item.grade_id)}
                    inputProps={{
                      'aria-label': 'select grade',
                      'data-testid': `select-${item.grade_id}`,
                    }}
                  />
                  <Box sx={{ flexGrow: 1 }}>
                    <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                      <Chip
                        size="small"
                        label={
                          item.confidence === null
                            ? t('auswertungen.exam.review.noConfidence')
                            : t('auswertungen.exam.review.confidenceLabel', {
                                value: Math.round((item.confidence ?? 0) * 100),
                              })
                        }
                        color={
                          (item.confidence ?? 0) >= 0.8
                            ? 'success'
                            : (item.confidence ?? 0) >= 0.5
                            ? 'warning'
                            : 'error'
                        }
                      />
                      <Chip
                        size="small"
                        label={
                          item.student_display_name ?? item.student_external_id
                        }
                        variant="outlined"
                      />
                      <Chip
                        size="small"
                        label={`${item.points_awarded.toFixed(
                          1,
                        )} / ${item.points_max.toFixed(1)}`}
                        variant="outlined"
                      />
                    </Stack>

                    <Typography variant="caption" color="text.secondary">
                      {t('auswertungen.exam.review.questionLabel')}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {item.question_text}
                    </Typography>

                    {item.correct_answer && (
                      <>
                        <Typography variant="caption" color="text.secondary">
                          {t('auswertungen.exam.review.correctAnswerLabel')}
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{ mb: 1, fontStyle: 'italic' }}
                        >
                          {item.correct_answer}
                        </Typography>
                      </>
                    )}

                    <Typography variant="caption" color="text.secondary">
                      {t('auswertungen.exam.review.studentAnswerLabel')}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {item.given_answer ?? '—'}
                    </Typography>

                    <Divider sx={{ my: 1 }} />

                    <Typography variant="caption" color="text.secondary">
                      {t('auswertungen.exam.review.proposalLabel')}
                    </Typography>
                    {item.rationale && (
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        {item.rationale}
                      </Typography>
                    )}

                    {(item.matched_aspects.length > 0 ||
                      item.missing_aspects.length > 0) && (
                      <Stack direction="row" spacing={2} sx={{ mt: 1, flexWrap: 'wrap' }}>
                        {item.matched_aspects.length > 0 && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              {t('auswertungen.exam.review.matchedAspects')}
                            </Typography>
                            <Stack
                              direction="row"
                              spacing={0.5}
                              sx={{ flexWrap: 'wrap', mt: 0.5 }}
                            >
                              {item.matched_aspects.map((aspect) => (
                                <Chip
                                  key={aspect}
                                  size="small"
                                  label={aspect}
                                  color="success"
                                  variant="outlined"
                                />
                              ))}
                            </Stack>
                          </Box>
                        )}
                        {item.missing_aspects.length > 0 && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              {t('auswertungen.exam.review.missingAspects')}
                            </Typography>
                            <Stack
                              direction="row"
                              spacing={0.5}
                              sx={{ flexWrap: 'wrap', mt: 0.5 }}
                            >
                              {item.missing_aspects.map((aspect) => (
                                <Chip
                                  key={aspect}
                                  size="small"
                                  label={aspect}
                                  color="warning"
                                  variant="outlined"
                                />
                              ))}
                            </Stack>
                          </Box>
                        )}
                      </Stack>
                    )}
                  </Box>
                </Box>
              </CardContent>
              <CardActions>
                <Button
                  startIcon={<ApproveIcon />}
                  size="small"
                  variant="contained"
                  onClick={() => handleApprove(item)}
                  data-testid={`approve-${item.grade_id}`}
                >
                  {t('auswertungen.exam.review.actionApprove')}
                </Button>
                <Button
                  startIcon={<OverrideIcon />}
                  size="small"
                  onClick={() => setOverrideItem(item)}
                  data-testid={`override-${item.grade_id}`}
                >
                  {t('auswertungen.exam.review.actionOverride')}
                </Button>
                {onOpenSubmission && (
                  <Button
                    startIcon={<ContextIcon />}
                    size="small"
                    onClick={() => onOpenSubmission(item.submission_id)}
                  >
                    {t('auswertungen.exam.review.actionContext')}
                  </Button>
                )}
              </CardActions>
            </Card>
          ))}
        </Stack>
      )}

      <OverrideGradeDialog
        open={!!overrideItem}
        gradeId={overrideItem?.grade_id ?? null}
        initialPoints={overrideItem?.points_awarded ?? 0}
        pointsMax={overrideItem?.points_max ?? 0}
        onClose={() => setOverrideItem(null)}
        onSuccess={handleOverrideSuccess}
      />
    </Box>
  );
};

export default ReviewQueue;
