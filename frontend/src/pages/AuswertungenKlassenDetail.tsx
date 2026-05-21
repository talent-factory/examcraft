/**
 * Klassen-Detail mit Cross-Exam-Verlauf (TF-336 G2 / Subarea B).
 *
 * Layout:
 *  - Header: Klassenname, Member-Count, "Studi zuweisen"-Action
 *  - Tab "Verlauf": LineChart der Klassen-Durchschnitte pro Prüfung
 *    + BarChart für Topic-Coverage + Tabelle der Member-Performance
 *  - Tab "Mitglieder": Studi-Liste mit Remove-Action
 *
 * Recharts liefert die Charts; Daten kommen aus
 * ``/api/v1/student-classes/{id}/stats`` (Enterprise-only — 402 wird
 * über den QuotaBanner an den Nutzer durchgereicht).
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  Paper,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  PersonRemove as PersonRemoveIcon,
  PersonAdd as PersonAddIcon,
} from '@mui/icons-material';
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
import { StudentClassesService } from '../services/studentClassesService';
import type {
  ClassHistoryStats,
  StudentClassDetail,
} from '../types/studentClass';
import AssignStudentDialog from '../components/auswertungen/AssignStudentDialog';
import QuotaBanner, {
  isQuotaError,
} from '../components/auswertungen/QuotaBanner';

const AuswertungenKlassenDetail: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { classId: classIdParam } = useParams<{ classId: string }>();
  const classId = Number(classIdParam);

  const [tab, setTab] = useState<'history' | 'members'>('history');
  const [detail, setDetail] = useState<StudentClassDetail | null>(null);
  const [history, setHistory] = useState<ClassHistoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [assignOpen, setAssignOpen] = useState(false);

  const [reloadKey, setReloadKey] = useState(0);
  const reload = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    if (!Number.isFinite(classId)) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setErrorText(null);
    Promise.allSettled([
      StudentClassesService.get(classId),
      StudentClassesService.getHistory(classId),
    ])
      .then(([detailRes, historyRes]) => {
        if (cancelled) return;
        if (detailRes.status === 'fulfilled') {
          setDetail(detailRes.value);
        } else if (detailRes.reason instanceof ApiError) {
          setError(detailRes.reason);
          setErrorText(detailRes.reason.message);
        }
        if (historyRes.status === 'fulfilled') {
          setHistory(historyRes.value);
        } else if (historyRes.reason instanceof ApiError) {
          // Tier-Quota auf der Stats-Route ist normal; nur den Banner
          // anzeigen, ohne den Members-Tab zu blockieren.
          if (historyRes.reason.status === 402) {
            setError(historyRes.reason);
          } else if (detailRes.status === 'fulfilled') {
            setErrorText(historyRes.reason.message);
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [classId, reloadKey]);

  const handleRemoveMember = async (studentId: number) => {
    try {
      await StudentClassesService.removeMember(classId, studentId);
      reload();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorText(err.message);
      }
    }
  };

  const trendData = (history?.exam_aggregates ?? []).map((a) => ({
    name: a.exam_title,
    avg: a.avg_percentage,
    pass: a.pass_rate !== null ? a.pass_rate * 100 : null,
  }));
  const topicData = (history?.topic_coverage ?? []).map((t) => ({
    topic: t.topic,
    percentage: t.percentage,
  }));

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (errorText && !detail) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{errorText}</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <IconButton onClick={() => navigate('/auswertungen/klassen')}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" component="h1">
          {detail?.name ?? '—'}
        </Typography>
        <Chip
          size="small"
          label={t('auswertungen.klassen.detail.memberCount', {
            count: detail?.member_count ?? 0,
          })}
          sx={{ ml: 1 }}
        />
        <Box sx={{ flexGrow: 1 }} />
        <Button
          variant="contained"
          startIcon={<PersonAddIcon />}
          onClick={() => setAssignOpen(true)}
          data-testid="class-detail-assign"
        >
          {t('auswertungen.klassen.detail.actionAssign')}
        </Button>
      </Box>

      {error && isQuotaError(error) && (
        <Box sx={{ mb: 2 }}>
          <QuotaBanner error={error} onDismiss={() => setError(null)} />
        </Box>
      )}

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 2 }}
        data-testid="class-detail-tabs"
      >
        <Tab
          value="history"
          label={t('auswertungen.klassen.detail.tabHistory')}
        />
        <Tab
          value="members"
          label={t('auswertungen.klassen.detail.tabMembers')}
        />
      </Tabs>

      {tab === 'history' && (
        <Box>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              {t('auswertungen.klassen.detail.examTrendTitle')}
            </Typography>
            {trendData.length === 0 ? (
              <Alert severity="info">
                {t('auswertungen.klassen.detail.examTrendNoData')}
              </Alert>
            ) : (
              <Box sx={{ height: 300 }} data-testid="class-trend-chart">
                <ResponsiveContainer>
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} unit="%" />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="avg"
                      name="Ø %"
                      stroke="#1976d2"
                      strokeWidth={2}
                      dot
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            )}
          </Paper>

          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              {t('auswertungen.klassen.detail.topicCoverageTitle')}
            </Typography>
            {topicData.length === 0 ? (
              <Alert severity="info">
                {t('auswertungen.klassen.detail.topicCoverageNoData')}
              </Alert>
            ) : (
              <Box sx={{ height: 250 }} data-testid="class-topic-chart">
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

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              {t('auswertungen.klassen.detail.memberPerformanceTitle')}
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>
                      {t('auswertungen.studierende.colExternalId')}
                    </TableCell>
                    <TableCell>
                      {t('auswertungen.studierende.colDisplayName')}
                    </TableCell>
                    <TableCell align="right">
                      {t('auswertungen.klassen.detail.colSubmissions')}
                    </TableCell>
                    <TableCell align="right">
                      {t('auswertungen.klassen.detail.colAvg')}
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(history?.members ?? []).map((m) => (
                    <TableRow
                      key={m.student_id}
                      hover
                      onClick={() =>
                        navigate(`/auswertungen/studierende/${m.student_id}`)
                      }
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell>{m.external_id}</TableCell>
                      <TableCell>{m.display_name ?? '—'}</TableCell>
                      <TableCell align="right">{m.submission_count}</TableCell>
                      <TableCell align="right">
                        {m.avg_percentage !== null
                          ? `${m.avg_percentage.toFixed(1)}%`
                          : '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Box>
      )}

      {tab === 'members' && detail && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            {t('auswertungen.klassen.detail.membersTitle')}
          </Typography>
          {detail.members.length === 0 ? (
            <Alert severity="info">
              {t('auswertungen.klassen.detail.emptyMembers')}
            </Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>
                      {t('auswertungen.studierende.colExternalId')}
                    </TableCell>
                    <TableCell>
                      {t('auswertungen.studierende.colDisplayName')}
                    </TableCell>
                    <TableCell align="right">
                      {t('auswertungen.klassen.colActions')}
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {detail.members.map((m) => (
                    <TableRow key={m.id} hover>
                      <TableCell>{m.external_id}</TableCell>
                      <TableCell>{m.display_name ?? '—'}</TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleRemoveMember(m.id)}
                          title={t(
                            'auswertungen.klassen.detail.actionRemoveMember',
                          )}
                          data-testid={`class-member-${m.id}-remove`}
                        >
                          <PersonRemoveIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      )}

      <AssignStudentDialog
        open={assignOpen}
        classId={classId}
        onClose={() => setAssignOpen(false)}
        onAssigned={() => reload()}
      />
    </Box>
  );
};

export default AuswertungenKlassenDetail;
