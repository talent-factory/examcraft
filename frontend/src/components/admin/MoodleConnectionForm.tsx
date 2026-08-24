/**
 * MoodleConnectionForm — admin UI for `moodle_connections`
 * (TF-336 Subarea C).
 *
 * Dual mode:
 *  - no connection: form to create one (base_url + token)
 *  - connection exists: masked token status, "Test",
 *    "Rotate token", "Remove" buttons
 *
 * Token masking: ``****<last 4>`` — the backend never returns the
 * plaintext. When rotating, the admin types the new token into a
 * separate field; the old field stays empty (= no change).
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

import { ApiError } from '../../services/submissionsService';
import { MoodleConnectionsService } from '../../services/moodleConnectionsService';
import type {
  MoodleConnection,
  MoodleConnectionTestResult,
} from '../../types/moodleConnection';

const MoodleConnectionForm: React.FC = () => {
  const { t } = useTranslation();

  const [connection, setConnection] = useState<MoodleConnection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [testResult, setTestResult] =
    useState<MoodleConnectionTestResult | null>(null);
  const [testing, setTesting] = useState(false);

  const [baseUrl, setBaseUrl] = useState('');
  const [token, setToken] = useState('');

  const [reloadKey, setReloadKey] = useState(0);
  const reload = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    MoodleConnectionsService.list()
      .then((res) => {
        if (cancelled) return;
        const first = res.items[0] ?? null;
        setConnection(first);
        if (first) {
          setBaseUrl(first.base_url);
        } else {
          setBaseUrl('');
        }
        setToken('');
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : 'Verbindungen konnten nicht geladen werden.',
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // ``t`` is unstable in tests; we have no dynamic i18n switching
    // on this page, the string above is sufficient as a fallback.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey]);

  const handleSave = async () => {
    setError(null);
    setSuccess(null);
    setTestResult(null);
    try {
      if (connection) {
        await MoodleConnectionsService.update(connection.id, {
          base_url: baseUrl !== connection.base_url ? baseUrl : undefined,
          token: token || undefined,
        });
        setSuccess(t('admin.moodle.updateSuccess'));
      } else {
        if (!baseUrl || !token) {
          setError(t('admin.moodle.validationError'));
          return;
        }
        await MoodleConnectionsService.create({
          base_url: baseUrl,
          token,
        });
        setSuccess(t('admin.moodle.createSuccess'));
      }
      reload();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : t('admin.moodle.saveError'),
      );
    }
  };

  const handleDelete = async () => {
    if (!connection) return;
    if (!window.confirm(t('admin.moodle.actionDelete') + '?')) return;
    try {
      await MoodleConnectionsService.remove(connection.id);
      setSuccess(t('admin.moodle.deleteSuccess'));
      reload();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : t('admin.moodle.deleteError'),
      );
    }
  };

  const handleTest = async () => {
    if (!connection) return;
    setTesting(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await MoodleConnectionsService.test(connection.id);
      setTestResult(res);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : t('admin.moodle.testError'),
      );
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ mb: 1 }}>
        {t('admin.moodle.title')}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t('admin.moodle.subtitle')}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} data-testid="moodle-form-error">
          {error}
        </Alert>
      )}
      {success && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          onClose={() => setSuccess(null)}
        >
          {success}
        </Alert>
      )}
      {testResult && (
        <Alert
          severity={testResult.ok ? 'success' : 'error'}
          sx={{ mb: 2 }}
          onClose={() => setTestResult(null)}
          data-testid="moodle-test-result"
        >
          {testResult.ok
            ? t('admin.moodle.testSuccess', {
                site: testResult.site_name ?? '?',
                user: testResult.user_full_name ?? '?',
              })
            : t('admin.moodle.testFailure', {
                error: testResult.error ?? '?',
              })}
        </Alert>
      )}

      <Stack spacing={2}>
        <TextField
          label={t('admin.moodle.baseUrlLabel')}
          helperText={t('admin.moodle.baseUrlHelper')}
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          fullWidth
          inputProps={{ 'data-testid': 'moodle-base-url' }}
        />
        {connection ? (
          <>
            <Box>
              <Typography variant="body2" sx={{ mb: 0.5 }}>
                {t('admin.moodle.tokenLabel')}: {connection.token_masked}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t('admin.moodle.tokenMaskedHint')}
                {' · '}
                {connection.last_used_at
                  ? t('admin.moodle.lastUsedAt', {
                      when: new Date(
                        connection.last_used_at,
                      ).toLocaleString(),
                    })
                  : t('admin.moodle.lastUsedNever')}
              </Typography>
            </Box>
            <TextField
              label={t('admin.moodle.tokenRotateLabel')}
              helperText={t('admin.moodle.tokenRotateHelper')}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              type="password"
              fullWidth
              autoComplete="off"
              inputProps={{ 'data-testid': 'moodle-token' }}
            />
          </>
        ) : (
          <TextField
            label={t('admin.moodle.tokenLabel')}
            helperText={t('admin.moodle.tokenHelper')}
            value={token}
            onChange={(e) => setToken(e.target.value)}
            type="password"
            fullWidth
            inputProps={{ 'data-testid': 'moodle-token' }}
          />
        )}

        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={!baseUrl}
            data-testid="moodle-save"
          >
            {connection
              ? t('admin.moodle.actionUpdate')
              : t('admin.moodle.actionSave')}
          </Button>
          {connection && (
            <Button
              variant="outlined"
              onClick={handleTest}
              disabled={testing}
              data-testid="moodle-test"
            >
              {testing
                ? t('admin.moodle.testRunning')
                : t('admin.moodle.actionTest')}
            </Button>
          )}
          {connection && (
            <Button
              color="error"
              onClick={handleDelete}
              data-testid="moodle-delete"
            >
              {t('admin.moodle.actionDelete')}
            </Button>
          )}
        </Box>
      </Stack>
    </Paper>
  );
};

export default MoodleConnectionForm;
