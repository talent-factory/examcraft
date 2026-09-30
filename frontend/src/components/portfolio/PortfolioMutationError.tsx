/**
 * Error of a portfolio mutation (TF-989).
 *
 * The reads are not tier-gated in the backend, so a tier refusal usually
 * surfaces on the first mutation — as `portfolio_assessment_tier_insufficient`.
 * That one renders the upgrade prompt instead of an error text; everything
 * else shows `message`.
 *
 * Callers translate the message themselves with a literal fallback key
 * (`translateError(err, t, 'errors.…')`): `bun run i18n:check` only verifies
 * fallback keys it can read as literals at the call site.
 */
import React from 'react';
import { Alert } from '@mui/material';
import { useFeatures } from '../../hooks/useFeatures';
import { PortfolioUpgradePrompt, isPortfolioTierError } from './PortfolioGate';

interface PortfolioMutationErrorProps {
  error: unknown;
  /** Translated text for any error except the tier refusal. */
  message: string;
}

export const PortfolioMutationError: React.FC<PortfolioMutationErrorProps> = ({
  error,
  message,
}) => {
  const { tier } = useFeatures();

  if (error == null) return null;
  if (isPortfolioTierError(error)) {
    return <PortfolioUpgradePrompt currentTier={tier} />;
  }
  return <Alert severity="error">{message}</Alert>;
};
