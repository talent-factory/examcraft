/**
 * Student detail with cross-exam history (TF-336 G3 / Subarea B).
 *
 * Layout:
 *  - Header: external_id + display_name + class membership
 *  - Submissions chronologically (LineChart % over time + table)
 *  - Bloom mix (BarChart)
 *  - Topic heatmap (BarChart)
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { ApiError } from '../services/submissionsService';
import { StudentsService } from '../services/studentsService';
import type { StudentHistoryStats } from '../types/student';
import QuotaBanner, {
  isQuotaError,
} from '../components/auswertungen/QuotaBanner';

const AuswertungenStudiDetail: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { studentId: studentIdParam } = useParams<{ studentId: string }>();
  const studentId = Number(studentIdParam);

  const [stats, setStats] = useState<StudentHistoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(studentId)) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setErrorText(null);
    StudentsService.getHistory(studentId)
      .then((res) => {
        if (!cancelled) setStats(res);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError(err);
          setErrorText(err.message);
        } else {
          setErrorText(
            err instanceof Error
              ? err.message
              : t('auswertungen.studierende.detail.loadError'),
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [studentId, t]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && isQuotaError(error)) {
    return (
      <Box sx={{ p: 3 }}>
        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton onClick={() => navigate('/auswertungen/studierende')}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4" component="h1">
            {t('auswertungen.studierende.title')}
          </Typography>
        </Box>
        <QuotaBanner error={error} />
      </Box>
    );
  }

  if (errorText && !stats) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{errorText}</Alert>
      </Box>
    );
  }

  if (!stats) return null;

  const submissionData = stats.submissions.map((s) => ({
    name: s.exam_title,
    date: s.exam_date,
    percentage: s.percentage,
  }));
  const bloomData = Object.entries(stats.bloom_mix)
    .map(([level, count]) => ({ level: `Bloom ${level}`, count }))
    .sort((a, b) => a.level.localeCompare(b.level));
  const topicData = stats.topic_heatmap.map((entry) => ({
    topic: entry.topic,
    percentage: entry.percentage,
  }));

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <IconButton onClick={() => navigate('/auswertungen/studierende')}>
          <ArrowBackIcon />
        </IconButton>
        <Box>
          <Typography variant="h4" component="h1">
            {stats.display_name ?? stats.external_id}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {stats.external_id}
          </Typography>
        </Box>
        <Box sx={{ flexGrow: 1 }} />
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          {stats.classes.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {t('auswertungen.studierende.detail.noClasses')}
            </Typography>
          ) : (
            stats.classes.map((c) => (
              <Chip
                key={c.class_id}
                size="small"
                label={c.class_name}
                onClick={() => navigate(`/auswertungen/klassen/${c.class_id}`)}
                data-testid={`studi-class-${c.class_id}`}
              />
            ))
          )}
        </Box>
      </Box>

      {stats.submission_count > 0 && stats.avg_percentage !== null && (
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          {t('auswertungen.studierende.detail.avgSummary', {
            count: stats.submission_count,
            percentage: stats.avg_percentage.toFixed(1),
          })}
        </Typography>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          {t('auswertungen.studierende.detail.submissionsTitle')}
        </Typography>
        {submissionData.length === 0 ? (
          <Alert severity="info">
            {t('auswertungen.studierende.detail.noSubmissions')}
          </Alert>
        ) : (
          <>
            <Box sx={{ height: 300, mb: 2 }} data-testid="studi-trend-chart">
              <ResponsiveContainer>
                <LineChart data={submissionData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 100]} unit="%" />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="percentage"
                    stroke="#1976d2"
                    strokeWidth={2}
                    dot
                  />
                </LineChart>
              </ResponsiveContainer>
            </Box>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>
                      {t('auswertungen.overview.colTitle')}
                    </TableCell>
                    <TableCell>
                      {t('auswertungen.overview.colDate')}
                    </TableCell>
                    <TableCell align="right">%</TableCell>
                    <TableCell>
                      {t('auswertungen.exam.colGradeStatus')}
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {stats.submissions.map((s) => (
                    <TableRow
                      key={s.submission_id}
                      hover
                      onClick={() =>
                        navigate(
                          `/auswertungen/${s.exam_id}/submissions`,
                        )
                      }
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell>{s.exam_title}</TableCell>
                      <TableCell>{s.exam_date ?? '—'}</TableCell>
                      <TableCell align="right">
                        {s.percentage.toFixed(1)}%
                      </TableCell>
                      <TableCell>{s.grade_status}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          {t('auswertungen.studierende.detail.bloomTitle')}
        </Typography>
        {bloomData.length === 0 ? (
          <Alert severity="info">
            {t('auswertungen.studierende.detail.bloomNoData')}
          </Alert>
        ) : (
          <Box sx={{ height: 220 }} data-testid="studi-bloom-chart">
            <ResponsiveContainer>
              <BarChart data={bloomData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="level" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#1976d2" />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        )}
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          {t('auswertungen.studierende.detail.topicHeatmapTitle')}
        </Typography>
        {topicData.length === 0 ? (
          <Alert severity="info">
            {t('auswertungen.studierende.detail.topicHeatmapNoData')}
          </Alert>
        ) : (
          <Box sx={{ height: 250 }} data-testid="studi-topic-chart">
            <ResponsiveContainer>
              <BarChart data={topicData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="topic" />
                <YAxis domain={[0, 100]} unit="%" />
                <Tooltip />
                <Bar dataKey="percentage" fill="#43a047" />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default AuswertungenStudiDetail;
