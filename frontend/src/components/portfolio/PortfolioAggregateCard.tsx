/**
 * Overall result of a portfolio grading (TF-992, P5b of TF-953).
 *
 * Human-in-the-loop gate (EU AI Act, TF-947): until every phase is reviewed
 * (`review_status === 'fully_reviewed'`) the points are marked as a
 * provisional AI proposal and no grade is shown — not even if one were in the
 * data. Afterwards `overall_grade` appears; it stays `null` without a valid
 * grading scheme, which the card says instead of a grade.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Box, Chip, Paper, Stack, Typography } from '@mui/material';
import type { PortfolioAssessmentDetail } from '../../types/portfolio';

interface PortfolioAggregateCardProps {
  assessment: PortfolioAssessmentDetail;
}

export const PortfolioAggregateCard: React.FC<PortfolioAggregateCardProps> = ({ assessment }) => {
  const { t, i18n } = useTranslation();
  const { overall_points_awarded: awarded, overall_points_max: max } = assessment;
  if (awarded == null || max == null) return null;

  const total = assessment.phase_results.length;
  const reviewed = assessment.phase_results.filter(
    (r) => r.status === 'completed' && r.review_status !== 'proposed',
  ).length;
  const fullyReviewed = assessment.review_status === 'fully_reviewed';
  const percentage =
    assessment.overall_percentage != null
      ? assessment.overall_percentage.toLocaleString(i18n.language, {
          maximumFractionDigits: 1,
        })
      : null;

  return (
    <Paper
      variant="outlined"
      sx={{ p: 2, borderColor: fullyReviewed ? 'success.main' : 'warning.main' }}
      data-testid="portfolio-aggregate"
    >
      <Stack spacing={1.5}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Typography variant="subtitle1" component="h3" sx={{ flexGrow: 1 }}>
            {t('pages.portfolio.aggregate.title')}
          </Typography>
          <Chip
            size="small"
            variant="outlined"
            color={fullyReviewed ? 'success' : 'warning'}
            label={
              fullyReviewed
                ? t('pages.portfolio.aggregate.reviewed')
                : t('pages.portfolio.aggregate.provisional')
            }
          />
        </Stack>

        <Box>
          <Typography variant="h6" component="p">
            {t('pages.portfolio.grading.points', { score: awarded, max })}
            {percentage != null &&
              ` · ${t('pages.portfolio.aggregate.percentage', { value: percentage })}`}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {t('pages.portfolio.aggregate.progress', { reviewed, total })}
          </Typography>
        </Box>

        {fullyReviewed ? (
          assessment.overall_grade != null ? (
            <Typography variant="h6" component="p" data-testid="portfolio-aggregate-grade">
              {t('pages.portfolio.aggregate.grade', { grade: assessment.overall_grade })}
            </Typography>
          ) : (
            <Typography variant="body2" color="textSecondary">
              {t(
                assessment.grading_scheme_id != null
                  ? 'pages.portfolio.aggregate.gradeUnavailable'
                  : 'pages.portfolio.aggregate.noScheme',
              )}
            </Typography>
          )
        ) : (
          <Alert severity="warning" data-testid="portfolio-aggregate-provisional">
            {t('pages.portfolio.aggregate.provisionalHint')}
          </Alert>
        )}
      </Stack>
    </Paper>
  );
};
