/**
 * `/portfolio/:id` — detail scaffold (TF-987).
 *
 * Owns polling (`usePortfolioAssessment`), the status stepper and the job
 * panel; the body branches on the current step. Each branch is a placeholder
 * the later packages replace: upload → P3 (TF-989), classification → P4
 * (TF-990), grading → P5a (TF-991), review → P5b (TF-992).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink, useParams } from 'react-router-dom';
import { Alert, Box, Button, CircularProgress, Paper, Stack, Typography } from '@mui/material';
import { translateError } from '../../errors';
import { useFeatures } from '../../hooks/useFeatures';
import { usePortfolioAssessment } from '../../hooks/usePortfolioAssessment';
import {
  PortfolioUpgradePrompt,
  isPortfolioTierError,
} from '../../components/portfolio/PortfolioGate';
import { PortfolioJobPanel } from '../../components/portfolio/PortfolioJobPanel';
import {
  PortfolioStatusStepper,
  portfolioStepFor,
} from '../../components/portfolio/PortfolioStatusStepper';

const PortfolioAssessmentDetailPage: React.FC = () => {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { tier } = useFeatures();
  const { assessment, isLoading, error, refetch, runningSince } = usePortfolioAssessment(id);

  if (isPortfolioTierError(error)) {
    return <PortfolioUpgradePrompt currentTier={tier} />;
  }

  const step = assessment ? portfolioStepFor(assessment.status) : null;

  return (
    <Box sx={{ p: 3 }} data-testid="portfolio-detail-page">
      <Button component={RouterLink} to="/portfolio" size="small" sx={{ mb: 1 }}>
        {t('pages.portfolio.detail.back')}
      </Button>
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        {t('pages.portfolio.title')}
      </Typography>

      {isLoading && <CircularProgress />}

      {error != null && !assessment && (
        <Alert severity="error">
          {translateError(error, t, 'errors.portfolio_assessment_load_failed')}
        </Alert>
      )}

      {assessment && (
        <Stack spacing={3}>
          {/* A failed poll keeps the last known state on screen: say that it
              may be outdated instead of claiming nothing could be loaded. */}
          {error != null && (
            <Alert
              severity="warning"
              action={
                <Button color="inherit" size="small" onClick={refetch}>
                  {t('pages.portfolio.detail.retry')}
                </Button>
              }
            >
              {t('pages.portfolio.detail.refreshFailed', {
                reason: translateError(error, t, 'errors.portfolio_assessment_load_failed'),
              })}
            </Alert>
          )}
          <PortfolioStatusStepper
            status={assessment.status}
            reviewStatus={assessment.review_status}
          />
          {assessment.job && (
            <PortfolioJobPanel
              job={assessment.job}
              runningSince={runningSince}
            />
          )}
          {step ? (
            <Paper
              variant="outlined"
              sx={{ p: 2 }}
              data-testid={`portfolio-detail-section-${step}`}
            >
              <Typography color="textSecondary">
                {t(`pages.portfolio.detail.sections.${step}`)}
              </Typography>
            </Paper>
          ) : (
            <Alert severity="warning">
              {t('pages.portfolio.detail.unknownStatus', { status: assessment.status })}
            </Alert>
          )}
        </Stack>
      )}
    </Box>
  );
};

export default PortfolioAssessmentDetailPage;
