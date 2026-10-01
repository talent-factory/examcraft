/**
 * Grading step of the detail page (TF-991, P5a of TF-953): start or resume
 * the grading and show the phase results as they come in.
 *
 * `POST /{id}/grade` serves both: the first start from `ready_to_grade` and
 * the resume after a failed run. A failed grade job (phase failure, time
 * budget, watchdog, broker down) deliberately leaves the assessment in
 * `grading`, so «`grading` without an active job» is exactly the resumable
 * state; a resume re-grades only the phases that are not `completed` yet.
 * Progress and the stalled-job hint come from the shared job panel above.
 *
 * The phase results carry ids only, so the template is loaded for names,
 * `max_points` and rubric texts. Everything shown here is the LLM's proposal
 * (EU AI Act, TF-947) until a teacher reviews it.
 *
 * Review (TF-992, P5b): approve/override per phase on the cards, and the
 * aggregate card on top, which shows a grade only once every phase is
 * reviewed. Approve/override answer with the phase and the recomputed
 * aggregate, which go straight into the cache; only the grade needs another
 * GET (the endpoints leave it out), so that happens once `fully_reviewed`.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Box, Button, CircularProgress, Paper, Stack, Typography } from '@mui/material';
import { portfolioApi } from '../../api/portfolioApi';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';
import {
  isPortfolioJobActive,
  portfolioAssessmentQueryKey,
  portfolioAssessmentsQueryKey,
} from '../../hooks/usePortfolioAssessment';
import type {
  PortfolioAssessmentDetail,
  PortfolioPhaseResult,
  PortfolioPhaseReviewResponse,
  PortfolioTemplatePhase,
} from '../../types/portfolio';
import { PortfolioAggregateCard } from './PortfolioAggregateCard';
import { portfolioTemplateQueryKey } from './PortfolioClassificationPanel';
import { PortfolioMutationError } from './PortfolioMutationError';
import { PortfolioPhaseResultCard, type PortfolioPhaseReviewProps } from './PortfolioPhaseResultCard';

interface OrderedPhaseResult {
  result: PortfolioPhaseResult;
  phase: PortfolioTemplatePhase | null;
}

/** Template order; a result whose phase the template lacks goes last. */
function orderPhaseResults(
  results: PortfolioPhaseResult[],
  phases: PortfolioTemplatePhase[] | undefined,
): OrderedPhaseResult[] {
  const byId = new Map((phases ?? []).map((p) => [p.id, p]));
  return results
    .map((result) => ({ result, phase: byId.get(result.phase_id) ?? null }))
    .sort(
      (a, b) =>
        (a.phase?.position ?? Number.MAX_SAFE_INTEGER) -
        (b.phase?.position ?? Number.MAX_SAFE_INTEGER),
    );
}

interface PortfolioGradingPanelProps {
  assessment: PortfolioAssessmentDetail;
}

export const PortfolioGradingPanel: React.FC<PortfolioGradingPanelProps> = ({ assessment }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canManage = hasPermission('portfolio_assessments:manage');

  const detailKey = portfolioAssessmentQueryKey(assessment.id);
  const phaseResults = assessment.phase_results;
  const templateQuery = useQuery({
    queryKey: portfolioTemplateQueryKey(assessment.template_id),
    queryFn: () => portfolioApi.getTemplate(assessment.template_id),
    enabled: phaseResults.length > 0,
  });

  const gradeMutation = useMutation({
    mutationFn: () => portfolioApi.startGrading(assessment.id),
    onSuccess: (summary) => {
      // The summary's `queued` job switches polling on at once; the refetch
      // brings the phase rows the endpoint has just created.
      queryClient.setQueryData<PortfolioAssessmentDetail>(
        detailKey,
        (current) => (current ? { ...current, ...summary } : current),
      );
      void queryClient.invalidateQueries({ queryKey: detailKey });
      void queryClient.invalidateQueries({ queryKey: portfolioAssessmentsQueryKey });
    },
    // A 409 can mean another tab started it meanwhile, and a 503 has already
    // failed a job: reload so the job panel shows what is true now.
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: detailKey });
    },
  });

  const review: PortfolioPhaseReviewProps | undefined = canManage
    ? {
        assessmentId: assessment.id,
        onReviewed: ({ assessment: aggregate, ...phaseResult }: PortfolioPhaseReviewResponse) => {
          queryClient.setQueryData<PortfolioAssessmentDetail>(detailKey, (current) =>
            current
              ? {
                  ...current,
                  ...aggregate,
                  phase_results: current.phase_results.map((r) =>
                    r.id === phaseResult.id ? phaseResult : r,
                  ),
                }
              : current,
          );
          // The grade is not part of the review response.
          if (aggregate.review_status === 'fully_reviewed') {
            void queryClient.invalidateQueries({ queryKey: detailKey });
          }
          void queryClient.invalidateQueries({ queryKey: portfolioAssessmentsQueryKey });
        },
        onReviewFailed: () => {
          void queryClient.invalidateQueries({ queryKey: detailKey });
        },
      }
    : undefined;

  const jobActive = isPortfolioJobActive(assessment.job);
  const canStart = assessment.status === 'ready_to_grade' && !jobActive;
  const canResume = assessment.status === 'grading' && !jobActive;
  const completedCount = phaseResults.filter((r) => r.status === 'completed').length;
  // Once a teacher has reviewed every graded phase (P5b) nothing on screen is
  // an unreviewed proposal any more; the per-phase chips then say who decided.
  const hasProposals = phaseResults.some(
    (r) => r.status === 'completed' && r.review_status === 'proposed',
  );
  const ordered = orderPhaseResults(phaseResults, templateQuery.data?.phases);

  return (
    <Paper variant="outlined" sx={{ p: 2 }} data-testid="portfolio-grading-panel">
      <Stack spacing={2}>
        <Typography variant="h6" component="h2">
          {t('pages.portfolio.grading.title')}
        </Typography>

        {canStart && (
          <Typography variant="body2">{t('pages.portfolio.grading.readyHint')}</Typography>
        )}
        {canResume && (
          <Alert severity="warning" data-testid="portfolio-grading-resumable">
            {t('pages.portfolio.grading.resumeHint')}
          </Alert>
        )}

        {(canStart || canResume) &&
          (canManage ? (
            <Box>
              <Button
                variant="contained"
                onClick={() => gradeMutation.mutate()}
                disabled={gradeMutation.isPending}
              >
                {t(
                  canResume
                    ? 'pages.portfolio.grading.resume'
                    : 'pages.portfolio.grading.start',
                )}
              </Button>
            </Box>
          ) : (
            <Typography variant="body2" color="textSecondary">
              {t('pages.portfolio.grading.manageRequired')}
            </Typography>
          ))}

        <PortfolioMutationError
          error={gradeMutation.error}
          message={
            gradeMutation.error
              ? translateError(gradeMutation.error, t, 'errors.portfolio_assessment_grade_failed')
              : ''
          }
        />

        {phaseResults.length > 0 && (
          <>
            <Typography variant="body2" color="textSecondary">
              {t('pages.portfolio.grading.phasesDone', {
                done: completedCount,
                total: phaseResults.length,
              })}
            </Typography>

            <PortfolioAggregateCard assessment={assessment} />

            {hasProposals && (
              <Alert severity="info" data-testid="portfolio-grading-ai-notice">
                {t('pages.portfolio.grading.aiNotice')}
              </Alert>
            )}

            {templateQuery.isError && (
              <Alert
                severity="warning"
                action={
                  <Button color="inherit" size="small" onClick={() => void templateQuery.refetch()}>
                    {t('pages.portfolio.detail.retry')}
                  </Button>
                }
              >
                {t('pages.portfolio.grading.templateFailed', {
                  reason: translateError(
                    templateQuery.error,
                    t,
                    'errors.portfolio_template_load_failed',
                  ),
                })}
              </Alert>
            )}

            {templateQuery.isLoading ? (
              <CircularProgress size={24} />
            ) : (
              ordered.map(({ result, phase }) => (
                <PortfolioPhaseResultCard
                  key={result.id}
                  result={result}
                  phase={phase}
                  review={review}
                />
              ))
            )}
          </>
        )}
      </Stack>
    </Paper>
  );
};
