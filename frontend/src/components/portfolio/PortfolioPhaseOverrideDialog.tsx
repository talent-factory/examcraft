/**
 * Override of one graded portfolio phase (TF-992, P5b of TF-953), modelled on
 * `components/auswertungen/OverrideGradeDialog.tsx`.
 *
 * One score field per criterion (integer 0…`max_points`, the bounds of
 * `override_phase_result`) plus an optional new rationale, and a reviewer
 * note for the phase. Only criteria whose score changed or that got a new
 * rationale are sent (partial override); an empty rationale keeps the
 * current one. The bounds are checked here, a 422 of the backend is shown
 * all the same.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { portfolioApi } from '../../api/portfolioApi';
import { translateError } from '../../errors';
import AiNotice from '../common/AiNotice';
import type {
  NonEmptyArray,
  PortfolioPhaseOverrideItem,
  PortfolioPhaseResultCompleted,
  PortfolioPhaseReviewResponse,
  PortfolioTemplateCriterion,
  PortfolioTemplatePhase,
} from '../../types/portfolio';
import { PortfolioMutationError } from './PortfolioMutationError';

interface CriterionDraft {
  score: string;
  rationale: string;
}

interface CriterionRow {
  criterionId: string;
  criterion: PortfolioTemplateCriterion;
  currentScore: number;
}

/** `null` when the score is a valid integer in [0, max], else the error text key. */
function scoreError(value: string, max: number): 'invalid' | 'outOfBounds' | null {
  if (!/^\d+$/.test(value.trim())) return 'invalid';
  const score = Number(value);
  return score > max ? 'outOfBounds' : null;
}

interface PortfolioPhaseOverrideDialogProps {
  open: boolean;
  assessmentId: string;
  result: PortfolioPhaseResultCompleted;
  phase: PortfolioTemplatePhase;
  onClose: () => void;
  onSuccess: (response: PortfolioPhaseReviewResponse) => void;
}

export const PortfolioPhaseOverrideDialog: React.FC<PortfolioPhaseOverrideDialogProps> = ({
  open,
  assessmentId,
  result,
  phase,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const criteria = new Map(phase.criteria.map((c) => [c.id, c]));
  // Template order; a criterion missing from the template has no known
  // maximum, so it cannot be overridden here and is left out.
  const rows: CriterionRow[] = result.criterion_results
    .flatMap((cr) => {
      const criterion = criteria.get(cr.criterion_id);
      return criterion
        ? [{ criterionId: cr.criterion_id, criterion, currentScore: cr.score }]
        : [];
    })
    .sort((a, b) => a.criterion.position - b.criterion.position);

  const [drafts, setDrafts] = useState<Record<string, CriterionDraft>>({});
  const [note, setNote] = useState('');

  const mutation = useMutation({
    mutationFn: (overrides: NonEmptyArray<PortfolioPhaseOverrideItem>) =>
      portfolioApi.overridePhaseResult(assessmentId, result.id, {
        overrides,
        reviewer_note: note.trim() || null,
      }),
    onSuccess: (response) => {
      onSuccess(response);
      onClose();
    },
  });

  // Reset on open only, otherwise the dialog carries over the previous
  // values. Not on a new `result`: a background refetch (e.g. on window
  // focus) would otherwise wipe what the teacher is typing.
  useEffect(() => {
    if (open) {
      setDrafts(
        Object.fromEntries(
          result.criterion_results.map((cr) => [
            cr.criterion_id,
            { score: String(cr.score), rationale: '' },
          ]),
        ),
      );
      setNote(result.reviewer_note ?? '');
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const initialDraft = (row: CriterionRow): CriterionDraft => ({
    score: String(row.currentScore),
    rationale: '',
  });
  const draftOf = (row: CriterionRow): CriterionDraft =>
    drafts[row.criterionId] ?? initialDraft(row);
  const errors = rows.map((row) => scoreError(draftOf(row).score, row.criterion.max_points));
  const hasErrors = errors.some((e) => e !== null);
  const changed: PortfolioPhaseOverrideItem[] = hasErrors
    ? []
    : rows.flatMap((row) => {
        const draft = draftOf(row);
        const score = Number(draft.score);
        const rationale = draft.rationale.trim();
        if (score === row.currentScore && !rationale) return [];
        return [{ criterion_id: row.criterionId, score, rationale: rationale || null }];
      });

  const update = (row: CriterionRow, patch: Partial<CriterionDraft>) =>
    setDrafts((current) => ({
      ...current,
      [row.criterionId]: { ...(current[row.criterionId] ?? initialDraft(row)), ...patch },
    }));

  const submit = () => {
    const [first, ...rest] = changed;
    if (first) mutation.mutate([first, ...rest]);
  };

  return (
    <Dialog
      open={open}
      onClose={() => (mutation.isPending ? undefined : onClose())}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>{t('pages.portfolio.review.overrideTitle', { phase: phase.name })}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <AiNotice kind="gradingSuggestion" />
          <Typography variant="body2" color="textSecondary">
            {t('pages.portfolio.review.overrideHint')}
          </Typography>
          <Stack spacing={2} divider={<Divider flexItem />}>
            {rows.map((row, index) => {
              const draft = draftOf(row);
              const error = errors[index];
              return (
                <Box key={row.criterionId} data-testid={`portfolio-override-${row.criterionId}`}>
                  <Typography variant="subtitle2" gutterBottom>
                    {row.criterion.name}
                  </Typography>
                  <Stack spacing={1.5}>
                    <TextField
                      label={t('pages.portfolio.review.scoreLabel')}
                      type="number"
                      size="small"
                      value={draft.score}
                      onChange={(e) =>
                        update(row, { score: e.target.value })
                      }
                      error={error !== null}
                      helperText={
                        error === 'invalid'
                          ? t('pages.portfolio.review.scoreInvalid')
                          : error === 'outOfBounds'
                            ? t('pages.portfolio.review.scoreOutOfBounds', {
                                max: row.criterion.max_points,
                              })
                            : t('pages.portfolio.review.scoreHelp', {
                                max: row.criterion.max_points,
                                current: row.currentScore,
                              })
                      }
                      inputProps={{
                        min: 0,
                        max: row.criterion.max_points,
                        step: 1,
                        'aria-label': t('pages.portfolio.review.scoreAria', {
                          criterion: row.criterion.name,
                        }),
                      }}
                    />
                    <TextField
                      label={t('pages.portfolio.review.rationaleLabel')}
                      size="small"
                      multiline
                      minRows={2}
                      value={draft.rationale}
                      onChange={(e) =>
                        update(row, { rationale: e.target.value })
                      }
                      helperText={t('pages.portfolio.review.rationaleHelp')}
                      inputProps={{
                        'aria-label': t('pages.portfolio.review.rationaleAria', {
                          criterion: row.criterion.name,
                        }),
                      }}
                    />
                  </Stack>
                </Box>
              );
            })}
          </Stack>
          <TextField
            label={t('pages.portfolio.review.noteLabel')}
            multiline
            minRows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          {!hasErrors && changed.length === 0 && (
            <Typography variant="body2" color="textSecondary">
              {t('pages.portfolio.review.noChanges')}
            </Typography>
          )}
          <PortfolioMutationError
            error={mutation.error}
            message={
              mutation.error
                ? translateError(mutation.error, t, 'errors.portfolio_assessment_review_failed')
                : ''
            }
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={mutation.isPending}>
          {t('pages.portfolio.review.cancel')}
        </Button>
        <Button
          variant="contained"
          onClick={submit}
          disabled={mutation.isPending || hasErrors || changed.length === 0}
        >
          {t('pages.portfolio.review.overrideSubmit')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
