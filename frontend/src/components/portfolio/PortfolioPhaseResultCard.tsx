/**
 * One phase of a portfolio grading (TF-991, P5a of TF-953).
 *
 * The phase result carries only ids; names, `max_points` and the rubric come
 * from the template (`phase`, `null` when the template could not be loaded or
 * no longer has the phase). Everything a completed phase shows is the LLM's
 * proposal until a teacher reviews it (EU AI Act, TF-947): the card marks it
 * as such and never shows a grade.
 *
 * Review (TF-992, P5b): a completed phase starts collapsed, and «Übernehmen»
 * and «Anpassen» sit inside the expanded part, so a teacher can only approve
 * after the criteria and rationales were on screen. There is deliberately no
 * bulk approve (Art. 6(3) EU AI Act, TF-947). Approve is offered only for a
 * proposal (the backend treats it as a no-op afterwards); an override stays
 * possible after a review to correct it.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  Divider,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import {
  Check as CheckIcon,
  Close as CloseIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { portfolioApi } from '../../api/portfolioApi';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';
import type {
  PortfolioCriterionResult,
  PortfolioPhaseResult,
  PortfolioPhaseResultCompleted,
  PortfolioPhaseReviewResponse,
  PortfolioPhaseStatus,
  PortfolioTemplateCriterion,
  PortfolioTemplatePhase,
} from '../../types/portfolio';
import { PortfolioMutationError } from './PortfolioMutationError';
import { PortfolioPhaseOverrideDialog } from './PortfolioPhaseOverrideDialog';
import { describePortfolioJobEntry, portfolioJobEntryFiles } from './portfolioJobMessages';
import { PHASE_REVIEW_STATUSES, PHASE_STATUSES, portfolioLabel } from './portfolioLabels';

const STATUS_COLOR: Record<PortfolioPhaseStatus, 'default' | 'info' | 'success' | 'error'> = {
  pending: 'default',
  running: 'info',
  completed: 'success',
  failed: 'error',
};

function FileList({ files }: { files: string[] }) {
  if (files.length === 0) return null;
  return (
    <Box component="ul" sx={{ m: 0, mt: 0.5, pl: 2.5 }}>
      {files.map((file) => (
        <li key={file}>
          <Typography variant="body2" component="span" sx={{ fontFamily: 'monospace' }}>
            {file}
          </Typography>
        </li>
      ))}
    </Box>
  );
}

function TextList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <Box>
      <Typography variant="body2" fontWeight={600}>
        {title}
      </Typography>
      <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
        {items.map((item, index) => (
          <li key={index}>
            <Typography variant="body2" component="span">
              {item}
            </Typography>
          </li>
        ))}
      </Box>
    </Box>
  );
}

interface CriterionResultProps {
  result: PortfolioCriterionResult;
  criterion: PortfolioTemplateCriterion | undefined;
}

const CriterionResult: React.FC<CriterionResultProps> = ({ result, criterion }) => {
  const { t } = useTranslation();
  // Scores are integers and the rubric is keyed by their string form.
  const rubric = criterion?.rubric_by_score[String(result.score)];
  const checklist = Object.entries(result.checklist ?? {});

  return (
    <Box data-testid={`portfolio-criterion-${result.criterion_id}`}>
      <Stack direction="row" spacing={1} alignItems="baseline" justifyContent="space-between">
        <Typography variant="subtitle2">
          {criterion?.name ?? t('pages.portfolio.grading.unknownCriterion')}
        </Typography>
        <Typography variant="subtitle2" sx={{ whiteSpace: 'nowrap' }}>
          {criterion
            ? t('pages.portfolio.grading.points', { score: result.score, max: criterion.max_points })
            : t('pages.portfolio.grading.pointsWithoutMax', { score: result.score })}
        </Typography>
      </Stack>

      {result.llm_score !== undefined && (
        <Chip
          size="small"
          variant="outlined"
          color="secondary"
          sx={{ mt: 0.5 }}
          label={t('pages.portfolio.review.criterionAdjusted', { score: result.llm_score })}
        />
      )}

      {rubric && (
        <Typography variant="body2" color="textSecondary" sx={{ mt: 0.5 }}>
          {t('pages.portfolio.grading.rubric', { text: rubric })}
        </Typography>
      )}

      <Stack spacing={1} sx={{ mt: 1 }}>
        <Box>
          <Typography variant="body2" fontWeight={600}>
            {t('pages.portfolio.grading.rationale')}
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {result.rationale}
          </Typography>
        </Box>

        {result.llm_rationale !== undefined && result.llm_rationale !== result.rationale && (
          <Box>
            <Typography variant="body2" fontWeight={600}>
              {t('pages.portfolio.review.llmRationale')}
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ whiteSpace: 'pre-wrap' }}>
              {result.llm_rationale}
            </Typography>
          </Box>
        )}

        {checklist.length > 0 && (
          <Box>
            <Typography variant="body2" fontWeight={600}>
              {t('pages.portfolio.grading.checklist')}
            </Typography>
            <Box component="ul" sx={{ m: 0, pl: 0, listStyle: 'none' }}>
              {checklist.map(([item, fulfilled]) => (
                <Stack key={item} component="li" direction="row" spacing={0.5} alignItems="center">
                  {fulfilled ? (
                    <CheckIcon
                      fontSize="small"
                      color="success"
                      titleAccess={t('pages.portfolio.grading.checklistFulfilled')}
                    />
                  ) : (
                    <CloseIcon
                      fontSize="small"
                      color="error"
                      titleAccess={t('pages.portfolio.grading.checklistNotFulfilled')}
                    />
                  )}
                  <Typography variant="body2" component="span">
                    {item}
                  </Typography>
                </Stack>
              ))}
            </Box>
          </Box>
        )}

        <TextList title={t('pages.portfolio.grading.strengths')} items={result.strengths ?? []} />
        <TextList
          title={t('pages.portfolio.grading.improvements')}
          items={result.improvements ?? []}
        />
      </Stack>
    </Box>
  );
};

/**
 * `reviewed_at` comes from a naive `datetime.utcnow()` without an offset;
 * read it as UTC instead of local time.
 */
function parseServerUtc(value: string): Date {
  return new Date(/(Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`);
}

interface ReviewInfoProps {
  result: PortfolioPhaseResultCompleted;
}

/** Who reviewed when, and the reviewer's note; nothing for a proposal. */
const ReviewInfo: React.FC<ReviewInfoProps> = ({ result }) => {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  if (result.review_status === 'proposed') return null;

  const date = result.reviewed_at
    ? parseServerUtc(result.reviewed_at).toLocaleString(i18n.language)
    : null;
  // The API returns only the reviewer's id; other teachers stay anonymous.
  const bySelf = user != null && result.reviewer_id === user.id;
  // Literal keys, so `i18n:check` can see them.
  const reviewedText = bySelf
    ? date
      ? t('pages.portfolio.review.reviewedBySelfAt', { date })
      : t('pages.portfolio.review.reviewedBySelf')
    : date
      ? t('pages.portfolio.review.reviewedAt', { date })
      : null;

  return (
    <Stack spacing={0.5} sx={{ mt: 1 }} data-testid={`portfolio-review-info-${result.phase_id}`}>
      {reviewedText && (
        <Typography variant="body2" color="textSecondary">
          {reviewedText}
        </Typography>
      )}
      {result.reviewer_note && (
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
          {t('pages.portfolio.review.reviewerNote', { note: result.reviewer_note })}
        </Typography>
      )}
    </Stack>
  );
};

interface ReviewActionsProps {
  assessmentId: string;
  result: PortfolioPhaseResultCompleted;
  phase: PortfolioTemplatePhase | null;
  onReviewed: (response: PortfolioPhaseReviewResponse) => void;
  onReviewFailed: () => void;
}

const ReviewActions: React.FC<ReviewActionsProps> = ({
  assessmentId,
  result,
  phase,
  onReviewed,
  onReviewFailed,
}) => {
  const { t } = useTranslation();
  const [overrideOpen, setOverrideOpen] = useState(false);
  const approveMutation = useMutation({
    mutationFn: () => portfolioApi.approvePhaseResult(assessmentId, result.id),
    onSuccess: onReviewed,
    // A 409/404 means the phase changed meanwhile (e.g. re-graded): reload.
    onError: onReviewFailed,
  });
  const proposed = result.review_status === 'proposed';

  return (
    <Stack spacing={1} sx={{ mt: 2 }} data-testid={`portfolio-review-actions-${result.phase_id}`}>
      {proposed && (
        <Typography variant="body2" color="textSecondary">
          {t('pages.portfolio.review.approveHint')}
        </Typography>
      )}
      <Stack direction="row" spacing={1}>
        {proposed && (
          <Button
            variant="contained"
            onClick={() => approveMutation.mutate()}
            disabled={approveMutation.isPending}
          >
            {t('pages.portfolio.review.approve')}
          </Button>
        )}
        <Button
          variant="outlined"
          onClick={() => setOverrideOpen(true)}
          // Without the template the bounds of the scores are unknown.
          disabled={phase == null || approveMutation.isPending}
        >
          {t('pages.portfolio.review.override')}
        </Button>
      </Stack>
      <PortfolioMutationError
        error={approveMutation.error}
        message={
          approveMutation.error
            ? translateError(approveMutation.error, t, 'errors.portfolio_assessment_review_failed')
            : ''
        }
      />
      {phase && (
        <PortfolioPhaseOverrideDialog
          open={overrideOpen}
          assessmentId={assessmentId}
          result={result}
          phase={phase}
          onClose={() => setOverrideOpen(false)}
          onSuccess={(response) => {
            approveMutation.reset();
            onReviewed(response);
          }}
        />
      )}
    </Stack>
  );
};

/** Present only for teachers who may review (`portfolio_assessments:manage`). */
export interface PortfolioPhaseReviewProps {
  assessmentId: string;
  onReviewed: (response: PortfolioPhaseReviewResponse) => void;
  onReviewFailed: () => void;
}

interface PortfolioPhaseResultCardProps {
  result: PortfolioPhaseResult;
  phase: PortfolioTemplatePhase | null;
  review?: PortfolioPhaseReviewProps;
}

export const PortfolioPhaseResultCard: React.FC<PortfolioPhaseResultCardProps> = ({
  result,
  phase,
  review,
}) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const criteria = new Map((phase?.criteria ?? []).map((c) => [c.id, c]));
  // Template order; a criterion the template does not know goes last.
  const position = (id: string) => criteria.get(id)?.position ?? Number.MAX_SAFE_INTEGER;
  const criterionResults =
    result.status === 'completed'
      ? [...result.criterion_results].sort(
          (a, b) => position(a.criterion_id) - position(b.criterion_id),
        )
      : [];
  const warnings = result.warnings ?? [];
  const detailsId = `portfolio-phase-details-${result.id}`;

  return (
    <Paper variant="outlined" sx={{ p: 2 }} data-testid={`portfolio-phase-result-${result.phase_id}`}>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
        <Typography variant="subtitle1" component="h3" sx={{ flexGrow: 1 }}>
          {phase?.name ?? t('pages.portfolio.grading.unknownPhase')}
        </Typography>
        {result.status === 'completed' && (
          <Typography variant="subtitle1" sx={{ whiteSpace: 'nowrap' }}>
            {t('pages.portfolio.grading.points', {
              score: result.total_points,
              max: result.max_points,
            })}
          </Typography>
        )}
        <Chip
          size="small"
          color={STATUS_COLOR[result.status] ?? 'default'}
          label={portfolioLabel(t, 'phaseStatus', result.status, PHASE_STATUSES)}
        />
        {result.status === 'completed' &&
          (result.review_status === 'proposed' ? (
            <Chip
              size="small"
              color="warning"
              variant="outlined"
              label={t('pages.portfolio.grading.aiProposal')}
            />
          ) : (
            <Chip
              size="small"
              variant="outlined"
              color={result.review_status === 'manual_override' ? 'secondary' : 'success'}
              label={portfolioLabel(
                t,
                'phaseReviewStatus',
                result.review_status,
                PHASE_REVIEW_STATUSES,
              )}
            />
          ))}
      </Stack>

      {result.status === 'completed' && <ReviewInfo result={result} />}

      {result.status === 'failed' && (
        <Alert severity="error" sx={{ mt: 1.5 }}>
          {t('pages.portfolio.grading.phaseFailed')}
        </Alert>
      )}
      {result.status === 'running' && (
        <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
          {t('pages.portfolio.grading.phaseRunning')}
        </Typography>
      )}

      {warnings.length > 0 && (
        <Stack spacing={1} sx={{ mt: 1.5 }}>
          {warnings.map((entry, index) => (
            <Alert key={index} severity="warning">
              {describePortfolioJobEntry(entry, t)}
              <FileList files={portfolioJobEntryFiles(entry)} />
            </Alert>
          ))}
        </Stack>
      )}

      {result.status === 'completed' && (
        <>
          <Button
            size="small"
            sx={{ mt: 1 }}
            onClick={() => setExpanded((open) => !open)}
            endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            aria-expanded={expanded}
            aria-controls={detailsId}
          >
            {t(
              expanded
                ? 'pages.portfolio.review.hideDetails'
                : 'pages.portfolio.review.showDetails',
            )}
          </Button>
          <Collapse in={expanded} unmountOnExit>
            <Box id={detailsId}>
              {criterionResults.length > 0 && (
                <Stack spacing={2} divider={<Divider flexItem />} sx={{ mt: 1 }}>
                  {criterionResults.map((criterionResult) => (
                    <CriterionResult
                      key={criterionResult.criterion_id}
                      result={criterionResult}
                      criterion={criteria.get(criterionResult.criterion_id)}
                    />
                  ))}
                </Stack>
              )}
              {review && (
                <ReviewActions
                  assessmentId={review.assessmentId}
                  result={result}
                  phase={phase}
                  onReviewed={review.onReviewed}
                  onReviewFailed={review.onReviewFailed}
                />
              )}
            </Box>
          </Collapse>
        </>
      )}
    </Paper>
  );
};
