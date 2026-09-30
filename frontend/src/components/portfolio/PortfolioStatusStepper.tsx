/**
 * Upload → Klassifikation → Bewertung → Überprüfung (TF-987).
 *
 * Status mapping: only the ingestion ever sets an assessment to `failed`
 * (`portfolio_ingestion_tasks.py`, the ingest watchdog and the upload enqueue
 * fallback), so `failed` marks the upload step. A failed classify or grade job
 * leaves the assessment in `classifying`/`grading`; the job panel shows that.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Step, StepLabel, Stepper } from '@mui/material';
import type {
  PortfolioAssessmentReviewStatus,
  PortfolioAssessmentStatus,
} from '../../types/portfolio';

export const PORTFOLIO_STEPS = ['upload', 'classification', 'grading', 'review'] as const;
export type PortfolioStep = (typeof PORTFOLIO_STEPS)[number];

/** `null` for a status this frontend does not know (newer backend). */
export function portfolioStepFor(status: PortfolioAssessmentStatus): PortfolioStep | null {
  switch (status) {
    case 'uploading':
    case 'failed':
      return 'upload';
    case 'classifying':
      return 'classification';
    case 'ready_to_grade':
    case 'grading':
      return 'grading';
    case 'completed':
      return 'review';
    default:
      console.warn('[portfolio] Unknown assessment status:', status);
      return null;
  }
}

interface PortfolioStatusStepperProps {
  status: PortfolioAssessmentStatus;
  reviewStatus: PortfolioAssessmentReviewStatus;
}

export const PortfolioStatusStepper: React.FC<PortfolioStatusStepperProps> = ({
  status,
  reviewStatus,
}) => {
  const { t } = useTranslation();
  // Every step done once the teacher reviewed all phases (TF-947 gate).
  const currentStep = portfolioStepFor(status);
  const activeStep =
    reviewStatus === 'fully_reviewed'
      ? PORTFOLIO_STEPS.length
      : currentStep === null
        ? -1
        : PORTFOLIO_STEPS.indexOf(currentStep);

  return (
    <Stepper activeStep={activeStep} alternativeLabel>
      {PORTFOLIO_STEPS.map((step, index) => (
        <Step key={step}>
          <StepLabel error={status === 'failed' && index === activeStep}>
            {t(`pages.portfolio.steps.${step}`)}
          </StepLabel>
        </Step>
      ))}
    </Stepper>
  );
};
