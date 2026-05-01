/**
 * Studi-Liste (TF-336 G3).
 *
 * Sucht institutionsweit alle Studierenden, optional gefiltert nach
 * Klasse oder Suchtext. Klick → Studi-Detail.
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { People as PeopleIcon } from '@mui/icons-material';

import { ApiError } from '../services/submissionsService';
import { StudentClassesService } from '../services/studentClassesService';
import { StudentsService } from '../services/studentsService';
import type { StudentClassSummary } from '../types/studentClass';
import type { StudentListItem } from '../types/student';
import QuotaBanner, {
  isQuotaError,
} from '../components/auswertungen/QuotaBanner';

const SEARCH_DEBOUNCE_MS = 250;

const AuswertungenStudierende: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [items, setItems] = useState<StudentListItem[]>([]);
  const [classes, setClasses] = useState<StudentClassSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState<number | ''>('');

  // Klassen einmal laden für den Filter-Dropdown.
  useEffect(() => {
    let cancelled = false;
    StudentClassesService.list({ limit: 200 })
      .then((res) => {
        if (!cancelled) setClasses(res.items);
      })
      .catch(() => {
        if (!cancelled) setClasses([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const handle = setTimeout(() => {
      setLoading(true);
      setError(null);
      setErrorText(null);
      StudentsService.list({
        search: search || undefined,
        classId: classFilter === '' ? undefined : classFilter,
        limit: 200,
      })
        .then((res) => {
          if (!cancelled) setItems(res.items);
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
                : t('auswertungen.studierende.loadError'),
            );
          }
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [search, classFilter, t]);

  const onClassFilter = (e: SelectChangeEvent<number | ''>) => {
    setClassFilter(e.target.value === '' ? '' : Number(e.target.value));
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
        <PeopleIcon color="primary" />
        <Typography variant="h4" component="h1">
          {t('auswertungen.studierende.title')}
        </Typography>
      </Box>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        {t('auswertungen.studierende.subtitle')}
      </Typography>

      <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField
          label={t('auswertungen.studierende.searchLabel')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          size="small"
          inputProps={{ 'data-testid': 'studi-search' }}
          sx={{ minWidth: 280 }}
        />
        <FormControl size="small" sx={{ minWidth: 220 }}>
          <InputLabel id="class-filter-label">
            {t('auswertungen.studierende.filterClass')}
          </InputLabel>
          <Select
            labelId="class-filter-label"
            label={t('auswertungen.studierende.filterClass')}
            value={classFilter}
            onChange={onClassFilter}
            data-testid="studi-class-filter"
          >
            <MenuItem value="">
              {t('auswertungen.studierende.filterAllClasses')}
            </MenuItem>
            {classes.map((cls) => (
              <MenuItem key={cls.id} value={cls.id}>
                {cls.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {error && isQuotaError(error) && (
        <Box sx={{ mb: 2 }}>
          <QuotaBanner error={error} onDismiss={() => setError(null)} />
        </Box>
      )}
      {errorText && !(error && isQuotaError(error)) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errorText}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : items.length === 0 ? (
        <Alert severity="info">{t('auswertungen.studierende.emptyHint')}</Alert>
      ) : (
        <TableContainer component={Paper} data-testid="studi-table">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  {t('auswertungen.studierende.colExternalId')}
                </TableCell>
                <TableCell>
                  {t('auswertungen.studierende.colDisplayName')}
                </TableCell>
                <TableCell>
                  {t('auswertungen.studierende.colClasses')}
                </TableCell>
                <TableCell align="right">
                  {t('auswertungen.studierende.colSubmissions')}
                </TableCell>
                <TableCell align="right">
                  {t('auswertungen.studierende.colAvg')}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((s) => (
                <TableRow
                  key={s.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/auswertungen/studierende/${s.id}`)}
                  data-testid={`studi-${s.id}`}
                >
                  <TableCell>{s.external_id}</TableCell>
                  <TableCell>{s.display_name ?? '—'}</TableCell>
                  <TableCell>
                    {s.classes.length === 0
                      ? t('auswertungen.studierende.noClasses')
                      : s.classes.map((c) => (
                          <Chip
                            key={c.class_id}
                            size="small"
                            label={c.class_name}
                            sx={{ mr: 0.5 }}
                          />
                        ))}
                  </TableCell>
                  <TableCell align="right">{s.submission_count}</TableCell>
                  <TableCell align="right">
                    {s.avg_percentage !== null
                      ? `${s.avg_percentage.toFixed(1)}%`
                      : '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default AuswertungenStudierende;
