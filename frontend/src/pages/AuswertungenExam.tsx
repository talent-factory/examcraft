/**
 * Per-exam evaluations page with tabs (Spec 7.3).
 *
 * Submissions list renders with row-click → detail drawer (answers +
 * grades). Review/Statistik/Notenexport tabs are wired in but disabled
 * until their backends ship.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Drawer,
  IconButton,
  Paper,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Close as CloseIcon,
  DeleteForever as DeleteForeverIcon,
  Upload as UploadIcon,
} from '@mui/icons-material';

import { SubmissionsService } from '../services/submissionsService';
import { ComposerService } from '../services/ComposerService';
import {
  AttemptAnswer,
  SubmissionDetail,
  SubmissionGradeStatus,
  SubmissionListItem,
} from '../types/submission';
import { ExamDetail } from '../types/composer';
import ImportDialog from '../components/auswertungen/ImportDialog';
import ImportStatusBanner from '../components/auswertungen/ImportStatusBanner';
import DeleteImportDialog from '../components/auswertungen/DeleteImportDialog';
import SyncMoodleIdsDialog from '../components/auswertungen/SyncMoodleIdsDialog';
import OverrideGradeDialog from '../components/auswertungen/OverrideGradeDialog';
import ReviewQueue from '../components/auswertungen/ReviewQueue';
import StatistikPanel from '../components/auswertungen/StatistikPanel';
import NotenexportPanel from '../components/auswertungen/NotenexportPanel';
import MarkdownRenderer from '../components/MarkdownRenderer';

const formatPct = (pct: number): string => `${Math.round(pct * 10) / 10}%`;

const gradeStatusColor: Record<SubmissionGradeStatus, 'default' | 'warning' | 'success'> =
  {
    pending_review: 'warning',
    partially_reviewed: 'warning',
    fully_reviewed: 'success',
  };

const AuswertungenExam: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams<{ examId: string }>();
  const examId = Number(params.examId);

  const [tab, setTab] = useState<
    'submissions' | 'review' | 'statistik' | 'export'
  >('submissions');
  const [exam, setExam] = useState<ExamDetail | null>(null);
  const [items, setItems] = useState<SubmissionListItem[]>([]);
  // Server-reported totals so the export-pending banner is accurate
  // even when the visible items page is smaller than the full set.
  const [submissionTotal, setSubmissionTotal] = useState(0);
  const [submissionPending, setSubmissionPending] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<SubmissionDetail | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  // TF-428: bumped when the import dialog closes so the status banner re-polls
  // immediately instead of waiting out its idle interval.
  const [importPollKey, setImportPollKey] = useState(0);
  const [deleteImportOpen, setDeleteImportOpen] = useState(false);
  const [syncMoodleOpen, setSyncMoodleOpen] = useState(false);
  const [reviewCount, setReviewCount] = useState<number | null>(null);
  const [overrideAnswer, setOverrideAnswer] = useState<AttemptAnswer | null>(
    null,
  );

  // Keep ``t`` out of the deps: in production it is stable across
  // language-change re-renders, but i18next mocks (and react-i18next's
  // own behaviour during tests) sometimes return a new function each
  // render, which would loop the effect.
  const reload = useCallback(async () => {
    if (!examId) return;
    setLoading(true);
    setError(null);
    try {
      const [examDetail, list] = await Promise.all([
        ComposerService.getExam(examId),
        SubmissionsService.listForExam(examId),
      ]);
      setExam(examDetail);
      setItems(list.items);
      setSubmissionTotal(list.total);
      setSubmissionPending(list.pending_count);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t('auswertungen.exam.loadError'),
      );
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId]);

  useEffect(() => {
    reload();
  }, [reload]);

  const handleRowClick = async (item: SubmissionListItem) => {
    setDrawerLoading(true);
    setDrawerError(null);
    setDrawer(null);
    try {
      const detail = await SubmissionsService.getDetail(item.id);
      setDrawer(detail);
    } catch (err) {
      // Surface the failure inside the drawer where the user clicked,
      // not in the page-level alert at the top.
      setDrawerError(
        err instanceof Error
          ? err.message
          : t('auswertungen.exam.detailError'),
      );
    } finally {
      setDrawerLoading(false);
    }
  };

  const closeDrawer = () => {
    setDrawer(null);
    setDrawerError(null);
  };

  const headerSection = useMemo(
    () => (
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <IconButton onClick={() => navigate('/auswertungen')} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4" component="h1">
            {exam?.title ?? '…'}
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Button
            variant="outlined"
            onClick={() => setSyncMoodleOpen(true)}
            data-testid="auswertungen-exam-sync-moodle"
            sx={{ mr: 1 }}
          >
            {t('auswertungen.moodleSync.actionLabel')}
          </Button>
          {submissionTotal > 0 && (
            <Button
              variant="outlined"
              color="error"
              startIcon={<DeleteForeverIcon />}
              onClick={() => setDeleteImportOpen(true)}
              data-testid="auswertungen-exam-delete-import"
              sx={{ mr: 1 }}
            >
              {t('auswertungen.exam.actionDeleteImport')}
            </Button>
          )}
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => setImportOpen(true)}
            data-testid="auswertungen-exam-import"
          >
            {t('auswertungen.exam.actionImport')}
          </Button>
        </Box>
        {exam && (
          <Typography variant="body2" color="text.secondary">
            {exam.course ?? '—'}
            {exam.exam_date ? ` · ${exam.exam_date}` : ''}
          </Typography>
        )}
      </Box>
    ),
    [exam, navigate, t, submissionTotal],
  );

  return (
    <Box sx={{ p: 3 }}>
      {headerSection}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Tabs
        value={tab}
        onChange={(_, v) =>
          setTab(v as 'submissions' | 'review' | 'statistik' | 'export')
        }
        sx={{ mb: 2 }}
      >
        <Tab
          label={`${t('auswertungen.exam.tabSubmissions')} (${items.length})`}
          value="submissions"
        />
        <Tab
          label={
            reviewCount !== null
              ? `${t('auswertungen.exam.tabReview')} (${reviewCount})`
              : t('auswertungen.exam.tabReview')
          }
          value="review"
        />
        <Tab label={t('auswertungen.exam.tabStatistik')} value="statistik" />
        <Tab label={t('auswertungen.exam.tabExport')} value="export" />
      </Tabs>

      {tab === 'submissions' && examId ? (
        <ImportStatusBanner
          examId={examId}
          pollKey={importPollKey}
          onCompleted={reload}
        />
      ) : null}

      {tab === 'statistik' ? (
        <StatistikPanel examId={examId} />
      ) : tab === 'export' ? (
        <NotenexportPanel
          examId={examId}
          totalSubmissions={submissionTotal}
          pendingCount={submissionPending}
          onOpenReview={() => setTab('review')}
        />
      ) : tab === 'review' ? (
        <ReviewQueue
          examId={examId}
          onTotalChange={(total) => setReviewCount(total)}
          onOpenSubmission={(submissionId) => {
            const item = items.find((i) => i.id === submissionId);
            if (item) {
              setTab('submissions');
              void handleRowClick(item);
            }
          }}
        />
      ) : loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : items.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
            {t('auswertungen.exam.emptyHint')}
          </Typography>
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => setImportOpen(true)}
          >
            {t('auswertungen.exam.actionImport')}
          </Button>
        </Paper>
      ) : (
        <TableContainer component={Paper} data-testid="submissions-table">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('auswertungen.exam.colExternalId')}</TableCell>
                <TableCell>{t('auswertungen.exam.colDisplayName')}</TableCell>
                <TableCell align="center">
                  {t('auswertungen.exam.colAttempts')}
                </TableCell>
                <TableCell align="right">
                  {t('auswertungen.exam.colPoints')}
                </TableCell>
                <TableCell align="right">
                  {t('auswertungen.exam.colPercentage')}
                </TableCell>
                <TableCell>
                  {t('auswertungen.exam.colGradeStatus')}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow
                  key={item.id}
                  hover
                  onClick={() => handleRowClick(item)}
                  sx={{ cursor: 'pointer' }}
                  data-testid={`submission-row-${item.id}`}
                >
                  <TableCell>{item.student_external_id}</TableCell>
                  <TableCell>{item.student_display_name ?? '—'}</TableCell>
                  <TableCell align="center">{item.attempt_count}</TableCell>
                  <TableCell align="right">
                    {item.total_points_awarded.toFixed(1)} /{' '}
                    {item.total_points_max.toFixed(1)}
                  </TableCell>
                  <TableCell align="right">
                    {formatPct(item.percentage)}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={t(
                        `auswertungen.exam.gradeStatus.${item.grade_status}`,
                      )}
                      color={gradeStatusColor[item.grade_status]}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Drawer
        anchor="right"
        open={!!drawer || drawerLoading || !!drawerError}
        onClose={closeDrawer}
        PaperProps={{ sx: { width: { xs: '100%', md: 600 } } }}
      >
        <Box sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {drawer
                ? drawer.student_display_name ??
                  drawer.student_external_id
                : ''}
            </Typography>
            <IconButton onClick={closeDrawer}>
              <CloseIcon />
            </IconButton>
          </Box>

          {drawerError ? (
            <Alert severity="error" data-testid="drawer-error">
              {drawerError}
            </Alert>
          ) : drawerLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : drawer ? (
            <Box>
              <Typography variant="body2" color="text.secondary">
                {drawer.student_external_id}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, my: 2 }}>
                <Chip
                  label={t('auswertungen.exam.drawer.points', {
                    awarded: drawer.total_points_awarded.toFixed(1),
                    max: drawer.total_points_max.toFixed(1),
                  })}
                />
                <Chip
                  label={formatPct(drawer.percentage)}
                  color="primary"
                />
                <Chip
                  size="small"
                  label={t(
                    `auswertungen.exam.gradeStatus.${drawer.grade_status}`,
                  )}
                  color={gradeStatusColor[drawer.grade_status]}
                />
              </Box>
              <Divider sx={{ my: 2 }} />

              {drawer.attempts.map((attempt) => (
                <Box key={attempt.id} sx={{ mb: 3 }}>
                  <Typography variant="subtitle1">
                    {t('auswertungen.exam.drawer.attemptHeader', {
                      number: attempt.attempt_number,
                    })}
                    {attempt.id === drawer.graded_attempt_id && (
                      <Chip
                        size="small"
                        label={t('auswertungen.exam.drawer.gradedTag')}
                        color="primary"
                        sx={{ ml: 1 }}
                      />
                    )}
                  </Typography>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>
                          {t('auswertungen.exam.drawer.colQuestion')}
                        </TableCell>
                        <TableCell>
                          {t('auswertungen.exam.drawer.colAnswer')}
                        </TableCell>
                        <TableCell align="right">
                          {t('auswertungen.exam.drawer.colGrade')}
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {attempt.answers.map((answer) => {
                        const grade = answer.grade;
                        const statusLabel = grade
                          ? t(`auswertungen.exam.gradeStatus.${grade.status}`)
                          : null;
                        return (
                          <TableRow key={answer.id}>
                            <TableCell>#{answer.exam_question_id}</TableCell>
                            <TableCell>
                              <MarkdownRenderer
                                content={answer.given_answer || '—'}
                                variant="compact"
                              />
                              {grade?.llm_rationale && (
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{ display: 'block', mt: 0.5 }}
                                >
                                  {t('auswertungen.exam.drawer.rationale')}:{' '}
                                  {grade.llm_rationale}
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell align="right">
                              {grade
                                ? `${grade.points_awarded.toFixed(
                                    1,
                                  )} / ${grade.points_max.toFixed(1)}`
                                : '—'}
                              {grade?.is_correct === true && ' ✓'}
                              {grade?.is_correct === false && ' ✗'}
                              {statusLabel && (
                                <Chip
                                  size="small"
                                  label={statusLabel}
                                  sx={{ ml: 1 }}
                                  color={
                                    grade?.status === 'manual_override'
                                      ? 'secondary'
                                      : grade?.status === 'approved'
                                      ? 'success'
                                      : 'default'
                                  }
                                  variant={
                                    grade?.status === 'proposed'
                                      ? 'outlined'
                                      : 'filled'
                                  }
                                />
                              )}
                              {grade && grade.status !== 'manual_override' && (
                                <Button
                                  size="small"
                                  sx={{ ml: 1 }}
                                  onClick={() => setOverrideAnswer(answer)}
                                  data-testid={`drawer-override-${answer.id}`}
                                >
                                  {grade.is_correct === null
                                    ? t(
                                        'auswertungen.exam.drawer.actionOverrideOpen',
                                      )
                                    : t(
                                        'auswertungen.exam.drawer.actionOverrideMc',
                                      )}
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </Box>
              ))}
            </Box>
          ) : null}
        </Box>
      </Drawer>

      <OverrideGradeDialog
        open={!!overrideAnswer}
        gradeId={overrideAnswer?.grade?.id ?? null}
        initialPoints={overrideAnswer?.grade?.points_awarded ?? 0}
        pointsMax={overrideAnswer?.grade?.points_max ?? 0}
        onClose={() => setOverrideAnswer(null)}
        onSuccess={async () => {
          // Drawer-State zum Aufruf-Zeitpunkt einfangen — der Drawer
          // kann während des Requests geschlossen werden, dann brauchen
          // wir keinen Re-Fetch.
          const submissionId = drawer?.id;
          if (submissionId !== undefined) {
            const updated = await SubmissionsService.getDetail(submissionId);
            setDrawer(updated);
          }
          void reload();
        }}
      />

      {importOpen && exam && (
        <ImportDialog
          open
          examId={exam.id}
          examTitle={exam.title}
          onClose={() => {
            setImportOpen(false);
            // Re-poll the status banner at once: the import may now be running
            // in the background (TF-428).
            setImportPollKey((key) => key + 1);
          }}
          onImported={() => {
            setImportOpen(false);
            setImportPollKey((key) => key + 1);
            void reload();
          }}
        />
      )}
      {deleteImportOpen && exam && (
        <DeleteImportDialog
          open
          examId={exam.id}
          examTitle={exam.title}
          onClose={() => setDeleteImportOpen(false)}
          onDeleted={() => {
            setDeleteImportOpen(false);
            void reload();
          }}
        />
      )}
      {syncMoodleOpen && exam && (
        <SyncMoodleIdsDialog
          open
          examId={exam.id}
          onClose={() => setSyncMoodleOpen(false)}
        />
      )}
    </Box>
  );
};

export default AuswertungenExam;
