/**
 * Confirmation for `DELETE /portfolio-assessments/{id}` (TF-989).
 *
 * The backend refuses with 409 `portfolio_assessment_delete_job_active` while
 * a job is queued or running; the list disables the button in that case, but
 * a job can start between the last poll and the click, so the dialog stays
 * open and shows the translated refusal.
 *
 * Every refusal reloads the list and the detail: a 409 means the cached row
 * missed a job, a 500 may follow a partial delete. A 404 means someone else
 * deleted it already, which is what the user wanted.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Stack,
} from '@mui/material';
import { portfolioApi } from '../../api/portfolioApi';
import { isAppError, translateError } from '../../errors';
import {
  portfolioAssessmentQueryKey,
  portfolioAssessmentsQueryKey,
} from '../../hooks/usePortfolioAssessment';
import type { PortfolioAssessmentListItem } from '../../types/portfolio';
import { PortfolioMutationError } from './PortfolioMutationError';

interface PortfolioAssessmentDeleteDialogProps {
  /** `null` keeps the dialog closed. */
  assessment: PortfolioAssessmentListItem | null;
  onClose: () => void;
}

export const PortfolioAssessmentDeleteDialog: React.FC<PortfolioAssessmentDeleteDialogProps> = ({
  assessment,
  onClose,
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const deleted = (id: string) => {
    queryClient.removeQueries({ queryKey: portfolioAssessmentQueryKey(id) });
    void queryClient.invalidateQueries({ queryKey: portfolioAssessmentsQueryKey });
    deleteMutation.reset();
    onClose();
  };

  const deleteMutation = useMutation({
    mutationFn: (id: string) => portfolioApi.deleteAssessment(id),
    onSuccess: (_, id) => deleted(id),
    onError: (error, id) => {
      if (isAppError(error) && error.code === 'portfolio_assessment_not_found') {
        deleted(id);
        return;
      }
      void queryClient.invalidateQueries({ queryKey: portfolioAssessmentsQueryKey });
      void queryClient.invalidateQueries({ queryKey: portfolioAssessmentQueryKey(id) });
    },
  });

  const handleClose = () => {
    if (deleteMutation.isPending) return;
    deleteMutation.reset();
    onClose();
  };

  return (
    <Dialog open={assessment !== null} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>{t('pages.portfolio.delete.title')}</DialogTitle>
      <DialogContent>
        <Stack spacing={2}>
          <DialogContentText>
            {t('pages.portfolio.delete.body', {
              student: assessment?.student_name ?? '',
              template: assessment?.template_name ?? '',
            })}
          </DialogContentText>
          <PortfolioMutationError
            error={deleteMutation.error}
            message={translateError(deleteMutation.error, t, 'errors.portfolio_assessment_delete_failed')}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={deleteMutation.isPending}>
          {t('common.cancel')}
        </Button>
        <Button
          color="error"
          variant="contained"
          onClick={() => assessment && deleteMutation.mutate(assessment.id)}
          disabled={deleteMutation.isPending}
          data-testid="portfolio-delete-confirm"
        >
          {t('pages.portfolio.delete.confirm')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
