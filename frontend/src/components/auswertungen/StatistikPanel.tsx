/**
 * Statistics panel — TF-335 Spec 8.
 *
 * Three sections:
 *   - KPI cards: avg points, pass rate, submission count, reviewed
 *   - Recharts histogram of the score distribution (10% buckets)
 *   - "Per question" table with sortable columns for pass rate /
 *     discrimination / difficulty
 *
 * Loads the two endpoints `stats/overview` and `stats/per-question`
 * in parallel on mount; renders skeletons while loading and an
 * empty state when no submissions have been imported yet.
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Typography,
} from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';

import { StatisticsService } from '../../services/statisticsService';
import { ApiError } from '../../services/submissionsService';
import {
  OverviewStats,
  PerQuestionStat,
} from '../../types/statistics';

interface StatistikPanelProps {
  examId: number;
}

type SortKey = 'position' | 'success_rate' | 'difficulty' | 'discrimination';
type SortDir = 'asc' | 'desc';

function fmtPercent(value: number | null): string {
  if (value === null) return '—';
  return `${value.toFixed(1)}%`;
}

function fmtFraction(value: number | null): string {
  if (value === null) return '—';
  return value.toFixed(2);
}

function fmtSeconds(value: number | null): string {
  if (value === null) return '—';
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes}m ${seconds}s`;
}

const StatistikPanel: React.FC<StatistikPanelProps> = ({ examId }) => {
  const { t } = useTranslation();
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [perQuestion, setPerQuestion] = useState<PerQuestionStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('position');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    // ``allSettled`` so a flake on per-question doesn't hide the
    // overview KPIs (and vice versa). One panel section degrades
    // independently of the other.
    Promise.allSettled([
      StatisticsService.getOverview(examId),
      StatisticsService.getPerQuestion(examId),
    ])
      .then(([ovResult, pqResult]) => {
        if (cancelled) return;
        if (ovResult.status === 'fulfilled') {
          setOverview(ovResult.value);
        }
        if (pqResult.status === 'fulfilled') {
          setPerQuestion(pqResult.value.items);
        }
        const failed = [ovResult, pqResult].filter(
          (r): r is PromiseRejectedResult => r.status === 'rejected',
        );
        if (failed.length === 0) return;

        // Log every rejection (Promise.all only would have surfaced
        // the first); helps Sentry / browser console see all failure
        // modes when both endpoints flake at once.
        failed.forEach((r) =>
          console.warn('[StatistikPanel] section failed:', r.reason),
        );

        const first = failed[0].reason;
        const partial = failed.length === 1;
        if (first instanceof ApiError) {
          if (partial) {
            setError(t('auswertungen.statistik.errorPartial'));
            return;
          }
          switch (first.kind) {
            case 'auth':
              setError(t('auswertungen.statistik.errorAuth'));
              break;
            case 'permission':
              setError(t('auswertungen.statistik.errorPermission'));
              break;
            case 'not_found':
              setError(t('auswertungen.statistik.errorNotFound'));
              break;
            default:
              setError(t('auswertungen.statistik.errorServer'));
          }
        } else if (first instanceof Error) {
          setError(first.message);
        } else {
          setError(t('auswertungen.statistik.errorServer'));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [examId, t]);

  const sortedQuestions = useMemo(() => {
    const items = [...perQuestion];
    items.sort((a, b) => {
      const av = a[sortKey] ?? -Infinity;
      const bv = b[sortKey] ?? -Infinity;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return items;
  }, [perQuestion, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!overview || overview.submission_count === 0) {
    return (
      <Alert severity="info" data-testid="statistik-empty">
        {t('auswertungen.stats.empty')}
      </Alert>
    );
  }

  const histogramData = overview.histogram.map((b) => ({
    label: `${b.from_pct}–${b.to_pct}%`,
    count: b.count,
  }));

  return (
    <Box>
      {/* --- KPI Cards --- */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 2,
          mb: 3,
        }}
      >
        <Card data-testid="kpi-submissions">
          <CardContent>
            <Typography variant="overline" color="text.secondary">
              {t('auswertungen.stats.kpiSubmissions')}
            </Typography>
            <Typography variant="h4">{overview.submission_count}</Typography>
            <Typography variant="caption" color="text.secondary">
              {t('auswertungen.stats.kpiReviewed', {
                count: overview.fully_reviewed_count,
              })}
            </Typography>
          </CardContent>
        </Card>

        <Card data-testid="kpi-avg">
          <CardContent>
            <Typography variant="overline" color="text.secondary">
              {t('auswertungen.stats.kpiAvg')}
            </Typography>
            <Typography variant="h4">
              {fmtPercent(overview.avg_percentage)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t('auswertungen.stats.kpiMedian', {
                value: fmtPercent(overview.median_percentage),
              })}
            </Typography>
          </CardContent>
        </Card>

        <Card data-testid="kpi-pass">
          <CardContent>
            <Typography variant="overline" color="text.secondary">
              {t('auswertungen.stats.kpiPassRate')}
            </Typography>
            <Typography variant="h4">
              {overview.pass_rate === null
                ? '—'
                : `${(overview.pass_rate * 100).toFixed(1)}%`}
            </Typography>
          </CardContent>
        </Card>

        <Card data-testid="kpi-duration">
          <CardContent>
            <Typography variant="overline" color="text.secondary">
              {t('auswertungen.stats.kpiAvgDuration')}
            </Typography>
            <Typography variant="h4">
              {fmtSeconds(overview.avg_duration_seconds)}
            </Typography>
          </CardContent>
        </Card>
      </Box>

      {/* --- Histogram --- */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          {t('auswertungen.stats.histogramTitle')}
        </Typography>
        <Box sx={{ width: '100%', height: 280 }}>
          <ResponsiveContainer>
            <BarChart
              data={histogramData}
              margin={{ top: 8, right: 16, left: 8, bottom: 16 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#1976d2" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
      </Paper>

      {/* --- Per-question table --- */}
      <Paper>
        <Typography variant="subtitle1" sx={{ p: 2 }}>
          {t('auswertungen.stats.perQuestionTitle')}
        </Typography>
        <TableContainer>
          <Table size="small" data-testid="per-question-table">
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={sortKey === 'position'}
                    direction={sortDir}
                    onClick={() => handleSort('position')}
                  >
                    {t('auswertungen.stats.colPosition')}
                  </TableSortLabel>
                </TableCell>
                <TableCell>{t('auswertungen.stats.colQuestion')}</TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={sortKey === 'success_rate'}
                    direction={sortDir}
                    onClick={() => handleSort('success_rate')}
                  >
                    {t('auswertungen.stats.colSuccessRate')}
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={sortKey === 'difficulty'}
                    direction={sortDir}
                    onClick={() => handleSort('difficulty')}
                  >
                    {t('auswertungen.stats.colDifficulty')}
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={sortKey === 'discrimination'}
                    direction={sortDir}
                    onClick={() => handleSort('discrimination')}
                  >
                    {t('auswertungen.stats.colDiscrimination')}
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  {t('auswertungen.stats.colLearning')}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedQuestions.map((q) => (
                <TableRow key={q.exam_question_id}>
                  <TableCell>{q.position}</TableCell>
                  <TableCell sx={{ maxWidth: 320 }}>
                    <Typography variant="body2" noWrap title={q.question_text}>
                      {q.question_text}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    {q.success_rate === null
                      ? '—'
                      : `${(q.success_rate * 100).toFixed(1)}%`}
                  </TableCell>
                  <TableCell align="right">
                    {q.difficulty === null
                      ? '—'
                      : `${(q.difficulty * 100).toFixed(1)}%`}
                  </TableCell>
                  <TableCell align="right">
                    {fmtFraction(q.discrimination)}
                  </TableCell>
                  <TableCell align="right">
                    {q.learning_effect === null
                      ? '—'
                      : `${(q.learning_effect * 100).toFixed(1)}%`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
};

export default StatistikPanel;
