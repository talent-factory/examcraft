/**
 * `/portfolio` — assessment list (TF-987 scaffold).
 *
 * P3 (TF-989) replaces the table with the enriched list from TF-986
 * (names, filters, paging) and adds creation and ingestion. Until TF-986 lands
 * the backend sends no names, hence the `student_name ?? #id` fallback.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { portfolioApi } from '../../api/portfolioApi';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';
import { useFeatures } from '../../hooks/useFeatures';
import {
  PortfolioUpgradePrompt,
  isPortfolioTierError,
} from '../../components/portfolio/PortfolioGate';
import {
  ASSESSMENT_STATUSES,
  REVIEW_STATUSES,
  portfolioLabel,
} from '../../components/portfolio/portfolioLabels';

export const portfolioAssessmentsQueryKey = ['portfolioAssessments'] as const;

const PortfolioAssessmentsPage: React.FC = () => {
  const { t } = useTranslation();
  const { hasPermission } = useAuth();
  const { tier } = useFeatures();
  const { data, isLoading, error } = useQuery({
    queryKey: portfolioAssessmentsQueryKey,
    queryFn: () => portfolioApi.listAssessments(),
  });

  if (isPortfolioTierError(error)) {
    return <PortfolioUpgradePrompt currentTier={tier} />;
  }

  return (
    <Box sx={{ p: 3 }} data-testid="portfolio-assessments-page">
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box>
          <Typography variant="h4" component="h1">
            {t('pages.portfolio.title')}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {t('pages.portfolio.subtitle')}
          </Typography>
        </Box>
        <Box sx={{ flexGrow: 1 }} />
        {hasPermission('portfolio_templates:read') && (
          <Button component={RouterLink} to="/portfolio/templates" variant="outlined">
            {t('pages.portfolio.list.templatesLink')}
          </Button>
        )}
      </Box>

      {isLoading && <CircularProgress />}

      {error != null && (
        <Alert severity="error">
          {translateError(error, t, 'errors.portfolio_assessment_list_failed')}
        </Alert>
      )}

      {data && data.length === 0 && (
        <Typography color="textSecondary">{t('pages.portfolio.list.empty')}</Typography>
      )}

      {data && data.length > 0 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('pages.portfolio.list.columnStudent')}</TableCell>
              <TableCell>{t('pages.portfolio.list.columnStatus')}</TableCell>
              <TableCell>{t('pages.portfolio.list.columnReview')}</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((assessment) => (
              <TableRow key={assessment.id}>
                <TableCell>
                  {assessment.student_name ??
                    t('pages.portfolio.list.studentFallback', { id: assessment.student_id })}
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={portfolioLabel(t, 'status', assessment.status, ASSESSMENT_STATUSES)}
                  />
                </TableCell>
                <TableCell>
                  {portfolioLabel(t, 'reviewStatus', assessment.review_status, REVIEW_STATUSES)}
                </TableCell>
                <TableCell align="right">
                  <Button component={RouterLink} to={`/portfolio/${assessment.id}`} size="small">
                    {t('pages.portfolio.list.open')}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Box>
  );
};

export default PortfolioAssessmentsPage;
