/**
 * One phase of a portfolio grading (TF-991, P5a of TF-953).
 *
 * The phase result carries only ids; names, `max_points` and the rubric come
 * from the template (`phase`, `null` when the template could not be loaded or
 * no longer has the phase). Everything a completed phase shows is the LLM's
 * proposal until a teacher reviews it (EU AI Act, TF-947): the card marks it
 * as such and never shows a grade. Approve/override follow in P5b (TF-992).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Box, Chip, Divider, Paper, Stack, Typography } from '@mui/material';
import { Check as CheckIcon, Close as CloseIcon } from '@mui/icons-material';
import type {
  PortfolioCriterionResult,
  PortfolioPhaseResult,
  PortfolioPhaseStatus,
  PortfolioTemplateCriterion,
  PortfolioTemplatePhase,
} from '../../types/portfolio';
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

interface PortfolioPhaseResultCardProps {
  result: PortfolioPhaseResult;
  phase: PortfolioTemplatePhase | null;
}

export const PortfolioPhaseResultCard: React.FC<PortfolioPhaseResultCardProps> = ({
  result,
  phase,
}) => {
  const { t } = useTranslation();
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
              label={portfolioLabel(
                t,
                'phaseReviewStatus',
                result.review_status,
                PHASE_REVIEW_STATUSES,
              )}
            />
          ))}
      </Stack>

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

      {criterionResults.length > 0 && (
        <Stack spacing={2} divider={<Divider flexItem />} sx={{ mt: 2 }}>
          {criterionResults.map((criterionResult) => (
            <CriterionResult
              key={criterionResult.criterion_id}
              result={criterionResult}
              criterion={criteria.get(criterionResult.criterion_id)}
            />
          ))}
        </Stack>
      )}
    </Paper>
  );
};
