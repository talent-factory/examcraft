/**
 * `/portfolio/:id` — detail scaffold (TF-987).
 *
 * Owns polling (`usePortfolioAssessment`), the status stepper and the job
 * panel; the body branches on the current step. The upload step is the
 * ingestion panel (TF-989), the classification step the review panel
 * (TF-990); grading and review show the grading panel with the phase
 * results (TF-991). The review actions follow in P5b (TF-992).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink, useParams } from 'react-router-dom';
import { Alert, Box, Button, CircularProgress, Paper, Stack, Typography } from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';
import { useFeatures } from '../../hooks/useFeatures';
import {
  isPortfolioJobActive,
  usePortfolioAssessment,
} from '../../hooks/usePortfolioAssessment';
import {
  PortfolioUpgradePrompt,
  isPortfolioTierError,
} from '../../components/portfolio/PortfolioGate';
import { PortfolioClassificationPanel } from '../../components/portfolio/PortfolioClassificationPanel';
import { PortfolioGradingPanel } from '../../components/portfolio/PortfolioGradingPanel';
import { PortfolioIngestionPanel } from '../../components/portfolio/PortfolioIngestionPanel';
import { PortfolioJobPanel } from '../../components/portfolio/PortfolioJobPanel';
import {
  PortfolioStatusStepper,
  portfolioStepFor,
} from '../../components/portfolio/PortfolioStatusStepper';

const PortfolioAssessmentDetailPage: React.FC = () => {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { tier } = useFeatures();
  const { hasPermission } = useAuth();
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
          {step === 'upload' &&
          hasPermission('portfolio_assessments:manage') &&
          !isPortfolioJobActive(assessment.job) ? (
            <Box data-testid="portfolio-detail-section-upload">
              <PortfolioIngestionPanel assessment={assessment} />
            </Box>
          ) : step === 'classification' ? (
            // Readers see the assignment too; the panel hides the actions.
            <Box data-testid="portfolio-detail-section-classification">
              <PortfolioClassificationPanel assessment={assessment} />
            </Box>
          ) : step === 'grading' || step === 'review' ? (
            <Box data-testid={`portfolio-detail-section-${step}`}>
              <PortfolioGradingPanel assessment={assessment} />
            </Box>
          ) : step ? (
            <Paper
              variant="outlined"
              sx={{ p: 2 }}
              data-testid={`portfolio-detail-section-${step}`}
            >
              <Typography color="textSecondary">
                {/* Only the upload step still ends up here: for readers, or
                    while its job runs. */}
                {t(
                  isPortfolioJobActive(assessment.job)
                    ? 'pages.portfolio.detail.sections.uploadRunning'
                    : 'pages.portfolio.detail.sections.upload',
                )}
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
