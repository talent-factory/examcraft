/**
 * Evaluations overview — lists all exams of the institution with
 *   - "Auswerten" → /auswertungen/{examId}/submissions
 *   - "Resultate importieren" → opens the ImportDialog inline.
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Typography,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  Upload as UploadIcon,
} from '@mui/icons-material';

import { ComposerService } from '../services/ComposerService';
import { ApiError } from '../services/submissionsService';
import { Exam } from '../types/composer';
import ImportDialog from '../components/auswertungen/ImportDialog';

const Auswertungen: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [exams, setExams] = useState<Exam[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Preserve structured server-side hints so the user can act on them
  // (e.g. validation issues), mirroring ImportDialog.handleApiError.
  const [errorIssues, setErrorIssues] = useState<string[]>([]);
  const [importExam, setImportExam] = useState<Exam | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    // TF-335: real pagination — backend cap raised to 500, UI
    // sends limit=rowsPerPage + offset. Data arrives page by page,
    // ``total`` is supplied by the backend.
    ComposerService.listExams({ limit: rowsPerPage, offset: page * rowsPerPage })
      .then((response) => {
        if (cancelled) return;
        setExams(response.exams);
        setTotal(response.total);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError(err.message);
          setErrorIssues(err.issues);
        } else {
          setError(
            err instanceof Error
              ? err.message
              : t('auswertungen.overview.loadError'),
          );
          setErrorIssues([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [t, page, rowsPerPage]);

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
        <AssessmentIcon color="primary" />
        <Typography variant="h4" component="h1">
          {t('auswertungen.overview.title')}
        </Typography>
      </Box>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        {t('auswertungen.overview.subtitle')}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
          {errorIssues.length > 0 && (
            <Box
              component="ul"
              sx={{ mt: 1, mb: 0, pl: 3 }}
              data-testid="auswertungen-overview-error-issues"
            >
              {errorIssues.slice(0, 5).map((iss) => (
                <li key={iss}>{iss}</li>
              ))}
              {errorIssues.length > 5 && (
                <li>
                  {t('auswertungen.importDialog.errorListTruncated', {
                    count: errorIssues.length - 5,
                  })}
                </li>
              )}
            </Box>
          )}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : exams.length === 0 && page === 0 ? (
        <Alert severity="info">{t('auswertungen.overview.emptyHint')}</Alert>
      ) : (
        <TableContainer component={Paper} data-testid="auswertungen-exam-table">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('auswertungen.overview.colTitle')}</TableCell>
                <TableCell>{t('auswertungen.overview.colCourse')}</TableCell>
                <TableCell>{t('auswertungen.overview.colDate')}</TableCell>
                <TableCell>{t('auswertungen.overview.colStatus')}</TableCell>
                <TableCell align="right">
                  {t('auswertungen.overview.colActions')}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {exams.map((exam) => (
                <TableRow key={exam.id} hover>
                  <TableCell>{exam.title}</TableCell>
                  <TableCell>{exam.course ?? '—'}</TableCell>
                  <TableCell>{exam.exam_date ?? '—'}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={t(`auswertungen.overview.examStatus.${exam.status}`)}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      onClick={() => navigate(`/auswertungen/${exam.id}/submissions`)}
                      sx={{ mr: 1 }}
                      data-testid={`exam-${exam.id}-evaluate`}
                    >
                      {t('auswertungen.overview.actionEvaluate')}
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<UploadIcon />}
                      onClick={() => setImportExam(exam)}
                      data-testid={`exam-${exam.id}-import`}
                    >
                      {t('auswertungen.overview.actionImport')}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={rowsPerPage}
            rowsPerPageOptions={[25, 50, 100]}
            onRowsPerPageChange={(event) => {
              setRowsPerPage(parseInt(event.target.value, 10));
              setPage(0);
            }}
            data-testid="auswertungen-pagination"
          />
        </TableContainer>
      )}

      {importExam && (
        <ImportDialog
          open
          examId={importExam.id}
          examTitle={importExam.title}
          onClose={() => setImportExam(null)}
          onImported={() => {
            // Quick follow-up navigation — the user should see the submissions.
            const id = importExam.id;
            setImportExam(null);
            navigate(`/auswertungen/${id}/submissions`);
          }}
        />
      )}
    </Box>
  );
};

export default Auswertungen;
