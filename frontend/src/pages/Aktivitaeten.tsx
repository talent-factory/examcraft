/**
 * /aktivitaeten — paginated activity feed.
 *
 * The effect uses an AbortController to cancel the previous in-flight
 * request whenever it re-runs; without it, fast chip-toggles can race
 * and render stale results last.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { de, enUS, fr, it } from 'date-fns/locale';
import * as Sentry from '@sentry/react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  TableContainer,
  TablePagination,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import { Notifications as NotificationsIcon } from '@mui/icons-material';

import { ApiError, ActivityService } from '../services/activityService';
import {
  ACTIVITY_TYPES,
  ActivityListResponse,
  ActivityScope,
  ActivityType,
} from '../types/activity';

const DATE_FNS_LOCALES: Record<string, Locale> = { de, en: enUS, fr, it };

const ACTIVITY_ICONS: Record<ActivityType, string> = {
  document_uploaded: '📄',
  document_deleted: '🗑️',
  questions_generated: '✨',
  question_approved: '✅',
  question_rejected: '❌',
  exam_created: '📝',
  exam_deleted: '🗑️',
};

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;

const Aktivitaeten: React.FC = () => {
  const { t, i18n } = useTranslation();

  const [scope, setScope] = useState<ActivityScope>('own');
  const [selectedTypes, setSelectedTypes] = useState<Set<ActivityType>>(
    () => new Set(ACTIVITY_TYPES),
  );
  const [rowsPerPage, setRowsPerPage] = useState<number>(25);
  const [page, setPage] = useState<number>(0);
  const [data, setData] = useState<ActivityListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Bumped to force a re-fetch on the "Erneut laden"-Button click.
  const [reloadTick, setReloadTick] = useState(0);

  // Serialise Set → array for a stable useEffect dep (Set identity
  // changes on every render).
  const typesParam = useMemo(() => {
    const arr = ACTIVITY_TYPES.filter((t_) => selectedTypes.has(t_));
    // All types selected → omit the param so the backend's implicit
    // "all supported types" path runs.
    if (arr.length === ACTIVITY_TYPES.length) return undefined;
    return arr;
  }, [selectedTypes]);

  // Track the latest in-flight request so React's StrictMode
  // double-mount doesn't leave a dangling AbortController on the
  // page level.
  const inFlightRef = useRef<AbortController | null>(null);

  useEffect(() => {
    inFlightRef.current?.abort();
    const controller = new AbortController();
    inFlightRef.current = controller;

    setLoading(true);
    setError(null);

    ActivityService.list({
      scope,
      types: typesParam,
      limit: rowsPerPage,
      offset: page * rowsPerPage,
      signal: controller.signal,
    })
      .then((response) => {
        if (controller.signal.aborted) return;
        setData(response);
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (err instanceof ApiError) {
          // Aborts are user-triggered (filter changes, unmount);
          // suppress them rather than rendering a red alert.
          if (err.kind === 'aborted') return;
          console.error('ActivityService.list failed', err);
          // Surface non-network errors to Sentry. The Sentry config
          // already filters NetworkError / cancelled requests, so
          // a kind=='network' will be dropped by beforeSend.
          Sentry.captureException(err, {
            tags: { feature: 'aktivitaeten', kind: err.kind },
            extra: { status: err.status, detail: err.detail },
          });
          setError(err.message);
        } else {
          console.error('ActivityService.list failed (non-ApiError)', err);
          // Non-ApiError throwables are programming bugs (TypeError
          // in the parser, etc.) — always escalate to Sentry.
          Sentry.captureException(err, {
            tags: { feature: 'aktivitaeten', kind: 'non-api-error' },
          });
          setError(
            err instanceof Error ? err.message : t('aktivitaeten.errorLoad'),
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
    // ``t`` is intentionally excluded: react-i18next's `useTranslation`
    // returns a new ``t`` reference per render. Including it in the dep
    // tuple turns this effect into an infinite refetch loop. ``t`` is
    // only read inside the catch fallback, where the latest closure
    // wins anyway.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, typesParam, rowsPerPage, page, reloadTick]);

  const locale =
    DATE_FNS_LOCALES[i18n.language?.substring(0, 2)] ?? de;

  const handleScopeChange = (
    _: React.MouseEvent<HTMLElement>,
    next: ActivityScope | null,
  ) => {
    // MUI's ToggleButtonGroup emits ``null`` when the user clicks the
    // already-active button — keep the current scope rather than
    // crashing or resetting to "own".
    if (!next) return;
    setScope(next);
    setPage(0);
  };

  const toggleType = (type: ActivityType) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
    setPage(0);
  };

  const resetFilters = () => {
    setSelectedTypes(new Set(ACTIVITY_TYPES));
    setScope('own');
    setPage(0);
  };

  const filtersActive = useMemo(
    () =>
      scope !== 'own' ||
      selectedTypes.size !== ACTIVITY_TYPES.length,
    [scope, selectedTypes],
  );

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const showEmptyAllFresh =
    !loading && !error && total === 0 && !filtersActive;
  const showEmptyFiltered =
    !loading && !error && total === 0 && filtersActive;

  return (
    <Box sx={{ p: 3 }} data-testid="aktivitaeten-page">
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
        <NotificationsIcon color="primary" />
        <Typography variant="h4" component="h1">
          {t('aktivitaeten.title')}
        </Typography>
      </Box>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        {t('aktivitaeten.subtitle')}
      </Typography>

      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={2}
        alignItems={{ xs: 'flex-start', md: 'center' }}
        sx={{ mb: 2 }}
      >
        <ToggleButtonGroup
          value={scope}
          exclusive
          onChange={handleScopeChange}
          size="small"
          aria-label={t('aktivitaeten.scopeAria')}
          data-testid="aktivitaeten-scope-toggle"
        >
          <ToggleButton value="own" data-testid="aktivitaeten-scope-own">
            {t('aktivitaeten.scopeOwn')}
          </ToggleButton>
          <ToggleButton
            value="institution"
            data-testid="aktivitaeten-scope-institution"
          >
            {t('aktivitaeten.scopeInstitution')}
          </ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      <Stack
        direction="row"
        spacing={1}
        useFlexGap
        flexWrap="wrap"
        sx={{ mb: 2 }}
        data-testid="aktivitaeten-type-chips"
      >
        {ACTIVITY_TYPES.map((type) => {
          const active = selectedTypes.has(type);
          return (
            <Chip
              key={type}
              label={`${ACTIVITY_ICONS[type]} ${t(`aktivitaeten.types.${type}`)}`}
              onClick={() => toggleType(type)}
              color={active ? 'primary' : 'default'}
              variant={active ? 'filled' : 'outlined'}
              data-testid={`aktivitaeten-chip-${type}`}
            />
          );
        })}
      </Stack>

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          data-testid="aktivitaeten-error"
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => setReloadTick((x) => x + 1)}
              data-testid="aktivitaeten-reload"
            >
              {t('aktivitaeten.reload')}
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress data-testid="aktivitaeten-loading" />
        </Box>
      )}

      {showEmptyAllFresh && (
        <Box
          sx={{ textAlign: 'center', py: 6 }}
          data-testid="aktivitaeten-empty-fresh"
        >
          <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
            {t('aktivitaeten.emptyFresh')}
          </Typography>
          <Stack direction="row" spacing={2} justifyContent="center">
            <Button component={RouterLink} to="/documents" variant="outlined">
              {t('aktivitaeten.shortcutDocuments')}
            </Button>
            <Button
              component={RouterLink}
              to="/questions/generate"
              variant="contained"
            >
              {t('aktivitaeten.shortcutGenerate')}
            </Button>
          </Stack>
        </Box>
      )}

      {showEmptyFiltered && (
        <Box
          sx={{ textAlign: 'center', py: 6 }}
          data-testid="aktivitaeten-empty-filtered"
        >
          <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
            {t('aktivitaeten.emptyFiltered')}
          </Typography>
          <Button
            variant="outlined"
            onClick={resetFilters}
            data-testid="aktivitaeten-reset-filters"
          >
            {t('aktivitaeten.resetFilters')}
          </Button>
        </Box>
      )}

      {!loading && !error && items.length > 0 && (
        <TableContainer component={Paper} data-testid="aktivitaeten-list">
          <Box component="ul" sx={{ listStyle: 'none', m: 0, p: 0 }}>
            {items.map((item) => (
              <Box
                component="li"
                key={item.id}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 2,
                  px: 2,
                  py: 1.5,
                  borderBottom: 1,
                  borderColor: 'divider',
                  '&:last-of-type': { borderBottom: 0 },
                }}
                data-testid={`aktivitaeten-item-${item.id}`}
              >
                <Box sx={{ fontSize: 24 }}>{ACTIVITY_ICONS[item.type]}</Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    fontWeight={500}
                    noWrap
                    title={item.title}
                  >
                    {item.title}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t(`aktivitaeten.types.${item.type}`)}
                  </Typography>
                </Box>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ whiteSpace: 'nowrap' }}
                >
                  {formatDistanceToNow(new Date(item.timestamp), {
                    addSuffix: true,
                    locale,
                  })}
                </Typography>
              </Box>
            ))}
          </Box>
          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={rowsPerPage}
            rowsPerPageOptions={[...PAGE_SIZE_OPTIONS]}
            onRowsPerPageChange={(event) => {
              setRowsPerPage(parseInt(event.target.value, 10));
              setPage(0);
            }}
            data-testid="aktivitaeten-pagination"
          />
        </TableContainer>
      )}
    </Box>
  );
};

export default Aktivitaeten;
