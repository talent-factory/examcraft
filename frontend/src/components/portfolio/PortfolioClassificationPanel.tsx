/**
 * Classification step of the detail page (TF-990): start the AI proposal,
 * review it per file, correct it and confirm it.
 *
 * The pipeline does not classify on its own after the ingestion: the teacher
 * starts it here (`POST /classify`). A successful start writes the returned
 * summary (with its `queued` job) into the detail query, which turns on
 * `usePortfolioAssessment`'s polling; the job panel above shows progress and
 * failures. A re-run keeps every manual assignment (the task skips
 * `classification_source === 'manual'`).
 *
 * The table groups the files by phase. Files without a phase come first and
 * are highlighted: the backend only assigns a phase automatically at or above
 * `CONFIDENCE_THRESHOLD` and keeps the lower confidence for this review. A
 * correction is a `PATCH` per file; the backend has no way back to «no
 * phase», so the dropdown offers phases only. Automatic assignments carry the
 * EU AI Act label (`AiNotice` kind `classificationSuggestion`).
 *
 * Confirming (`POST /confirm-classification`) moves the assessment to
 * `ready_to_grade`. The button stays disabled while any file lacks a phase;
 * if the server still finds some (another tab, a stale view), its 409 lists
 * them and those rows are marked.
 *
 * Phase names come from `GET /portfolio-templates/{template_id}`. Phases and
 * criteria of a template are locked once an assessment uses it
 * (`portfolio_template_phases_locked`), so the template's current phases are
 * the assessment's.
 */
import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  alpha,
} from '@mui/material';
import {
  isPortfolioUnclassifiedDocumentsError,
  portfolioApi,
} from '../../api/portfolioApi';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';
import {
  isPortfolioJobActive,
  portfolioAssessmentQueryKey,
  portfolioAssessmentsQueryKey,
} from '../../hooks/usePortfolioAssessment';
import type {
  PortfolioAssessmentDetail,
  PortfolioAssessmentSummary,
  PortfolioDocument,
  PortfolioTemplatePhase,
} from '../../types/portfolio';
import { AiNotice } from '../common/AiNotice';
import { PortfolioMutationError } from './PortfolioMutationError';

/** Must match the backend classification confidence threshold (`CONFIDENCE_THRESHOLD`). */
export const PORTFOLIO_CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.7;

/** Shares the `portfolioTemplates` prefix, so invalidating the list refreshes it too. */
export const portfolioTemplateQueryKey = (id: string) => ['portfolioTemplates', id] as const;

const UNASSIGNED = 'unassigned';
const UNKNOWN_PHASE = 'unknown';

interface DocumentGroup {
  key: string;
  /** `null` for the unassigned and the unknown-phase group. */
  phase: PortfolioTemplatePhase | null;
  documents: PortfolioDocument[];
}

const byPath = (a: PortfolioDocument, b: PortfolioDocument) =>
  a.original_relative_path.localeCompare(b.original_relative_path);

/**
 * Unassigned files first, then every phase in template order (empty ones too:
 * a phase without files is worth noticing before grading), then files whose
 * phase the template no longer lists — or all assigned files while the
 * template could not be loaded.
 */
export function groupPortfolioDocuments(
  documents: PortfolioDocument[],
  phases: PortfolioTemplatePhase[],
): DocumentGroup[] {
  const sortedPhases = [...phases].sort((a, b) => a.position - b.position);
  const known = new Set(sortedPhases.map((phase) => phase.id));
  const groups: DocumentGroup[] = [];

  const unassigned = documents.filter((doc) => doc.phase_id === null);
  if (unassigned.length > 0) {
    groups.push({ key: UNASSIGNED, phase: null, documents: unassigned.sort(byPath) });
  }
  for (const phase of sortedPhases) {
    groups.push({
      key: phase.id,
      phase,
      documents: documents.filter((doc) => doc.phase_id === phase.id).sort(byPath),
    });
  }
  const unknown = documents.filter((doc) => doc.phase_id !== null && !known.has(doc.phase_id));
  if (unknown.length > 0) {
    groups.push({ key: UNKNOWN_PHASE, phase: null, documents: unknown.sort(byPath) });
  }
  return groups;
}

interface PortfolioClassificationPanelProps {
  assessment: PortfolioAssessmentDetail;
}

export const PortfolioClassificationPanel: React.FC<PortfolioClassificationPanelProps> = ({
  assessment,
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canManage = hasPermission('portfolio_assessments:manage');
  // Ids the last 409 `unclassified_documents` listed; a correction clears its own.
  const [flaggedIds, setFlaggedIds] = useState<ReadonlySet<number>>(new Set());

  const templateQuery = useQuery({
    queryKey: portfolioTemplateQueryKey(assessment.template_id),
    queryFn: () => portfolioApi.getTemplate(assessment.template_id),
  });
  const phases = useMemo(() => templateQuery.data?.phases ?? [], [templateQuery.data]);

  const detailKey = portfolioAssessmentQueryKey(assessment.id);
  const reload = () => {
    void queryClient.invalidateQueries({ queryKey: detailKey });
  };
  const applySummary = (summary: PortfolioAssessmentSummary) => {
    queryClient.setQueryData<PortfolioAssessmentDetail>(detailKey, (current) =>
      current ? { ...current, ...summary } : current,
    );
    reload();
    void queryClient.invalidateQueries({ queryKey: portfolioAssessmentsQueryKey });
  };

  const classifyMutation = useMutation({
    mutationFn: () => portfolioApi.startClassification(assessment.id),
    onSuccess: (summary) => {
      setFlaggedIds(new Set());
      applySummary(summary);
    },
    // A 409 may mean a job runs after all (another tab): reload to show it.
    onError: reload,
  });

  const updateMutation = useMutation({
    mutationFn: ({ documentId, phaseId }: { documentId: number; phaseId: string }) =>
      portfolioApi.updateDocumentPhase(assessment.id, documentId, phaseId),
    onSuccess: (updated) => {
      queryClient.setQueryData<PortfolioAssessmentDetail>(detailKey, (current) =>
        current
          ? {
              ...current,
              documents: current.documents.map((doc) =>
                doc.document_id === updated.document_id ? updated : doc,
              ),
            }
          : current,
      );
      // A refused confirm described the state before this correction.
      confirmMutation.reset();
      setFlaggedIds((current) => {
        if (!current.has(updated.document_id)) return current;
        const next = new Set(current);
        next.delete(updated.document_id);
        return next;
      });
    },
    onError: reload,
  });

  const confirmMutation = useMutation({
    mutationFn: () => portfolioApi.confirmClassification(assessment.id),
    onSuccess: applySummary,
    onError: (err) => {
      if (isPortfolioUnclassifiedDocumentsError(err)) {
        setFlaggedIds(new Set(err.documentIds));
      }
      reload();
    },
  });

  const documents = assessment.documents;
  const groups = groupPortfolioDocuments(documents, phases);
  const unassignedCount = documents.filter((doc) => doc.phase_id === null).length;
  // A confidence without a phase is AI output too (below the threshold).
  const hasAiOutput = documents.some(
    (doc) => doc.classification_source === 'auto' || doc.classification_confidence !== null,
  );
  const hasProposal = hasAiOutput || documents.some((doc) => doc.classification_source !== null);
  const jobActive = isPortfolioJobActive(assessment.job);
  const busy =
    classifyMutation.isPending || updateMutation.isPending || confirmMutation.isPending;
  const editable = canManage && !jobActive;
  const canConfirm =
    editable && !busy && documents.length > 0 && unassignedCount === 0;

  const renderSource = (doc: PortfolioDocument) => {
    if (doc.classification_source === 'auto') {
      return <AiNotice kind="classificationSuggestion" variant="chip" />;
    }
    if (doc.classification_source === 'manual') {
      return (
        <Chip size="small" label={t('pages.portfolio.classification.source.manual')} />
      );
    }
    return (
      <Chip
        size="small"
        color="warning"
        variant="outlined"
        label={t('pages.portfolio.classification.source.open')}
      />
    );
  };

  const renderConfidence = (doc: PortfolioDocument) => {
    if (doc.classification_confidence === null) {
      return <Typography variant="body2" color="textSecondary">–</Typography>;
    }
    const percent = Math.round(doc.classification_confidence * 100);
    const low = doc.classification_confidence < PORTFOLIO_CLASSIFICATION_CONFIDENCE_THRESHOLD;
    return (
      <Box>
        <Typography variant="body2">
          {t('pages.portfolio.classification.confidence', { percent })}
        </Typography>
        {low && (
          <Typography variant="caption" color="warning.main" component="p">
            {t('pages.portfolio.classification.lowConfidence', {
              threshold: Math.round(PORTFOLIO_CLASSIFICATION_CONFIDENCE_THRESHOLD * 100),
            })}
          </Typography>
        )}
      </Box>
    );
  };

  const renderPhaseSelect = (doc: PortfolioDocument) => (
    <TextField
      select
      size="small"
      fullWidth
      value={doc.phase_id ?? ''}
      onChange={(event) =>
        updateMutation.mutate({ documentId: doc.document_id, phaseId: event.target.value })
      }
      disabled={!editable || busy || phases.length === 0}
      SelectProps={{ native: true }}
      inputProps={{
        'aria-label': t('pages.portfolio.classification.phaseFor', {
          path: doc.original_relative_path,
        }),
        'data-testid': `portfolio-classification-phase-${doc.document_id}`,
      }}
    >
      {/* No way back to «no phase» in the backend: offered only as the
          initial empty value, never as a choice. */}
      {doc.phase_id === null && (
        <option value="" disabled>
          {t('pages.portfolio.classification.choosePhase')}
        </option>
      )}
      {phases.map((phase) => (
        <option key={phase.id} value={phase.id}>
          {phase.name}
        </option>
      ))}
    </TextField>
  );

  const groupTitle = (group: DocumentGroup) => {
    if (group.phase) return group.phase.name;
    return t(
      group.key === UNASSIGNED
        ? 'pages.portfolio.classification.unassignedGroup'
        : 'pages.portfolio.classification.unknownPhaseGroup',
    );
  };

  return (
    <Paper variant="outlined" sx={{ p: 2 }} data-testid="portfolio-classification-panel">
      <Stack spacing={2}>
        <Typography variant="h6" component="h2">
          {t('pages.portfolio.classification.title')}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {t('pages.portfolio.classification.intro')}
        </Typography>

        {!canManage && (
          <Alert severity="info">{t('pages.portfolio.classification.readOnly')}</Alert>
        )}

        {jobActive && (
          <Alert severity="info">{t('pages.portfolio.classification.running')}</Alert>
        )}

        {editable && (
          <Box>
            <Button
              variant={hasProposal ? 'outlined' : 'contained'}
              onClick={() => classifyMutation.mutate()}
              disabled={busy || documents.length === 0}
              data-testid="portfolio-classification-start"
            >
              {t(
                hasProposal
                  ? 'pages.portfolio.classification.reclassify'
                  : 'pages.portfolio.classification.classify',
              )}
            </Button>
            {hasProposal && (
              <Typography variant="caption" color="textSecondary" component="p" sx={{ mt: 0.5 }}>
                {t('pages.portfolio.classification.reclassifyHint')}
              </Typography>
            )}
          </Box>
        )}
        <PortfolioMutationError
          error={classifyMutation.error}
          message={
            classifyMutation.error
              ? translateError(classifyMutation.error, t, 'errors.portfolio_assessment_classify_failed')
              : ''
          }
        />

        {hasAiOutput && <AiNotice kind="classificationSuggestion" />}

        {templateQuery.isError && (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={() => void templateQuery.refetch()}>
                {t('pages.portfolio.detail.retry')}
              </Button>
            }
          >
            {t('pages.portfolio.classification.templateLoadFailed', {
              reason: translateError(templateQuery.error, t, 'errors.portfolio_template_load_failed'),
            })}
          </Alert>
        )}

        {templateQuery.isLoading ? (
          // Without phase names every assigned file would flash up under
          // «Unbekannte Phase» first.
          <Box display="flex" justifyContent="center" sx={{ py: 2 }}>
            <CircularProgress size={28} />
          </Box>
        ) : documents.length === 0 ? (
          <Alert severity="warning">{t('pages.portfolio.classification.noDocuments')}</Alert>
        ) : (
          <>
            <Typography variant="body2" data-testid="portfolio-classification-summary">
              {t('pages.portfolio.classification.summary', {
                total: documents.length,
                unassigned: unassignedCount,
              })}
            </Typography>

            {groups.map((group) => {
              const unassigned = group.key === UNASSIGNED;
              return (
                <Box key={group.key} data-testid={`portfolio-classification-group-${group.key}`}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <Typography
                      variant="subtitle1"
                      component="h3"
                      color={unassigned ? 'warning.main' : undefined}
                    >
                      {groupTitle(group)}
                    </Typography>
                    <Chip size="small" label={group.documents.length} />
                  </Stack>
                  {unassigned && (
                    <Alert severity="warning" sx={{ mb: 1 }}>
                      {t('pages.portfolio.classification.unassignedHint')}
                    </Alert>
                  )}
                  {group.documents.length === 0 ? (
                    <Typography variant="body2" color="textSecondary">
                      {t('pages.portfolio.classification.emptyPhase')}
                    </Typography>
                  ) : (
                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>{t('pages.portfolio.classification.columns.path')}</TableCell>
                            <TableCell>{t('pages.portfolio.classification.columns.origin')}</TableCell>
                            <TableCell>{t('pages.portfolio.classification.columns.source')}</TableCell>
                            <TableCell>
                              {t('pages.portfolio.classification.columns.confidence')}
                            </TableCell>
                            <TableCell sx={{ minWidth: 200 }}>
                              {t('pages.portfolio.classification.columns.phase')}
                            </TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {group.documents.map((doc) => {
                            const flagged = flaggedIds.has(doc.document_id);
                            return (
                              <TableRow
                                key={doc.document_id}
                                data-testid={`portfolio-classification-row-${doc.document_id}`}
                                data-flagged={flagged ? 'true' : undefined}
                                sx={
                                  flagged
                                    ? { bgcolor: (theme) => alpha(theme.palette.error.main, 0.12) }
                                    : doc.phase_id === null
                                      ? { bgcolor: (theme) => alpha(theme.palette.warning.main, 0.08) }
                                      : undefined
                                }
                              >
                                <TableCell sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                                  {doc.original_relative_path}
                                  {flagged && (
                                    <Typography
                                      variant="caption"
                                      color="error"
                                      component="p"
                                      sx={{ fontFamily: 'inherit' }}
                                    >
                                      {t('pages.portfolio.classification.flagged')}
                                    </Typography>
                                  )}
                                </TableCell>
                                <TableCell>
                                  {t(`pages.portfolio.classification.origin.${doc.origin}`, {
                                    defaultValue: doc.origin,
                                  })}
                                </TableCell>
                                <TableCell>{renderSource(doc)}</TableCell>
                                <TableCell>{renderConfidence(doc)}</TableCell>
                                <TableCell>{renderPhaseSelect(doc)}</TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </Box>
              );
            })}
          </>
        )}

        <PortfolioMutationError
          error={updateMutation.error}
          message={
            updateMutation.error
              ? translateError(updateMutation.error, t, 'errors.portfolio_assessment_document_update_failed')
              : ''
          }
        />

        {canManage && (
          <Box>
            <Button
              variant="contained"
              color="primary"
              onClick={() => confirmMutation.mutate()}
              disabled={!canConfirm}
              data-testid="portfolio-classification-confirm"
            >
              {t('pages.portfolio.classification.confirm')}
            </Button>
            {unassignedCount > 0 && (
              <Typography variant="caption" color="textSecondary" component="p" sx={{ mt: 0.5 }}>
                {t('pages.portfolio.classification.confirmBlocked', { open: unassignedCount })}
              </Typography>
            )}
          </Box>
        )}
        <PortfolioMutationError
          error={confirmMutation.error}
          message={
            confirmMutation.error
              ? translateError(
                  confirmMutation.error,
                  t,
                  'errors.portfolio_assessment_confirm_classification_failed',
                )
              : ''
          }
        />
      </Stack>
    </Paper>
  );
};
