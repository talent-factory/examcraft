/**
 * Upload step of the detail page (TF-989): ZIP upload and/or GitHub import,
 * and the retry after a failed ingestion.
 *
 * Shown only while no job is active. A successful start writes the returned
 * summary (with its `queued` job) into the detail query, which turns on
 * `usePortfolioAssessment`'s polling at once; the job panel above then shows
 * the file progress until the assessment reaches `classifying`.
 *
 * With a repository URL on the assessment, every ingestion — with or without
 * archive — also fetches the repository, and the worker reads the GitHub
 * token of the assessment's creator (`created_by`). The credential endpoint
 * only knows the viewer's own token, so the token gate applies to the
 * creator alone: both start buttons wait for a stored token, which can be
 * entered right here (`PUT /portfolio-github-credential`; viewing and
 * deleting it in the profile is TF-994). Anyone else gets a note that the
 * creator's token is used and cannot fix a token failure from here.
 *
 * Only ingestion ever sets an assessment to `failed` (task, watchdog,
 * enqueue fallback); classify and grade failures only fail their job. That
 * is why `failed` means «retry the upload» here.
 */
import React, { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Divider,
  LinearProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { portfolioApi } from '../../api/portfolioApi';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';
import {
  portfolioAssessmentQueryKey,
  portfolioAssessmentsQueryKey,
} from '../../hooks/usePortfolioAssessment';
import type {
  PortfolioAssessmentDetail,
  PortfolioAssessmentSummary,
} from '../../types/portfolio';
import { PortfolioMutationError } from './PortfolioMutationError';

/** `MAX_ARCHIVE_BYTES` in `portfolio_ingestion_validation.py`. */
export const PORTFOLIO_MAX_ARCHIVE_MB = 500;
const MAX_ARCHIVE_BYTES = PORTFOLIO_MAX_ARCHIVE_MB * 1024 * 1024;

export const portfolioGithubCredentialQueryKey = ['portfolioGithubCredential'] as const;

/** Job codes a new token can fix. */
const TOKEN_JOB_CODES = new Set([
  'portfolio_github_auth_failed',
  'portfolio_github_token_decrypt_failed',
  'portfolio_github_token_missing',
]);

function formatMegabytes(bytes: number): string {
  return (bytes / (1024 * 1024)).toFixed(1);
}

interface GithubTokenFormProps {
  replacing: boolean;
  onSaved: () => void;
}

const GithubTokenForm: React.FC<GithubTokenFormProps> = ({ replacing, onSaved }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [token, setToken] = useState('');

  const saveMutation = useMutation({
    mutationFn: () => portfolioApi.setGithubCredential(token.trim()),
    onSuccess: () => {
      setToken('');
      queryClient.setQueryData(portfolioGithubCredentialQueryKey, { configured: true });
      onSaved();
    },
  });

  return (
    <Box data-testid="portfolio-github-token-form">
      <Typography variant="body2" sx={{ mb: 1 }}>
        {t(
          replacing
            ? 'pages.portfolio.ingestion.tokenReplace'
            : 'pages.portfolio.ingestion.tokenMissing',
        )}
      </Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems="flex-start">
        <TextField
          size="small"
          type="password"
          autoComplete="off"
          label={t('pages.portfolio.ingestion.tokenLabel')}
          value={token}
          onChange={(e) => setToken(e.target.value)}
          // The backend's `CredentialIn` caps at 255.
          inputProps={{ maxLength: 255, 'data-testid': 'portfolio-github-token-input' }}
          sx={{ flexGrow: 1 }}
        />
        <Button
          variant="outlined"
          onClick={() => saveMutation.mutate()}
          disabled={token.trim() === '' || saveMutation.isPending}
        >
          {t('pages.portfolio.ingestion.tokenSave')}
        </Button>
      </Stack>
      <Typography variant="caption" color="textSecondary" component="p" sx={{ mt: 0.5 }}>
        {t('pages.portfolio.ingestion.tokenHelp')}
      </Typography>
      <Box sx={{ mt: 1 }}>
        <PortfolioMutationError
          error={saveMutation.error}
          message={saveMutation.error ? translateError(saveMutation.error, t, 'errors.portfolio_assessment_github_credential_save_failed') : ''}
        />
      </Box>
    </Box>
  );
};

interface PortfolioIngestionPanelProps {
  assessment: PortfolioAssessmentDetail;
}

export const PortfolioIngestionPanel: React.FC<PortfolioIngestionPanelProps> = ({ assessment }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [tokenSaved, setTokenSaved] = useState(false);

  const { user } = useAuth();
  const repositoryUrl = assessment.source_repository_url;
  const isCreator = user != null && assessment.created_by === user.id;
  const credentialQuery = useQuery({
    queryKey: portfolioGithubCredentialQueryKey,
    queryFn: () => portfolioApi.getGithubCredentialStatus(),
    enabled: !!repositoryUrl && isCreator,
  });
  const tokenConfigured = credentialQuery.data?.configured === true;
  const lastJobFailedOnToken =
    assessment.job?.status === 'failed' &&
    (assessment.job.error_log ?? []).some(
      (entry) => typeof entry.code === 'string' && TOKEN_JOB_CODES.has(entry.code),
    );
  // Also on a failed status load: saving a token settles the state either way.
  const showTokenForm =
    !!repositoryUrl &&
    isCreator &&
    (credentialQuery.isError ||
      (credentialQuery.isSuccess && (!tokenConfigured || (lastJobFailedOnToken && !tokenSaved))));
  const waitingForToken = !!repositoryUrl && isCreator && !tokenConfigured;

  const onStarted = (summary: PortfolioAssessmentSummary) => {
    queryClient.setQueryData<PortfolioAssessmentDetail>(
      portfolioAssessmentQueryKey(assessment.id),
      (current) => (current ? { ...current, ...summary } : current),
    );
    void queryClient.invalidateQueries({ queryKey: portfolioAssessmentQueryKey(assessment.id) });
    void queryClient.invalidateQueries({ queryKey: portfolioAssessmentsQueryKey });
  };

  // A refusal can mean a job exists after all (409 from another tab, or an
  // upload timeout after the server had queued it): reload so the job panel
  // and polling take over if it does.
  const onStartFailed = () => {
    void queryClient.invalidateQueries({ queryKey: portfolioAssessmentQueryKey(assessment.id) });
  };

  const uploadMutation = useMutation({
    mutationFn: (archive: File) =>
      portfolioApi.uploadArchive(assessment.id, archive, (fraction) => setProgress(fraction)),
    onMutate: () => setProgress(0),
    onSuccess: (summary) => {
      setFile(null);
      onStarted(summary);
    },
    onError: onStartFailed,
    onSettled: () => setProgress(null),
  });

  const ingestMutation = useMutation({
    mutationFn: () => portfolioApi.startRepositoryIngestion(assessment.id),
    onSuccess: onStarted,
    onError: onStartFailed,
  });

  const busy = uploadMutation.isPending || ingestMutation.isPending;
  const fileTooLarge = file !== null && file.size > MAX_ARCHIVE_BYTES;

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null);
    uploadMutation.reset();
    ingestMutation.reset();
    // Lets the same file be picked again after a failure.
    event.target.value = '';
  };

  return (
    <Paper variant="outlined" sx={{ p: 2 }} data-testid="portfolio-ingestion-panel">
      <Stack spacing={2}>
        <Typography variant="h6" component="h2">
          {t('pages.portfolio.ingestion.title')}
        </Typography>

        {assessment.status === 'failed' && (
          <Alert severity="info">{t('pages.portfolio.ingestion.retryHint')}</Alert>
        )}

        {repositoryUrl && (
          <Box>
            <Typography variant="body2">
              {t('pages.portfolio.ingestion.repository')}{' '}
              <Box component="span" sx={{ fontFamily: 'monospace' }}>
                {repositoryUrl}
              </Box>
            </Typography>
            <Typography variant="caption" color="textSecondary">
              {t('pages.portfolio.ingestion.repositoryAlwaysFetched')}
            </Typography>
          </Box>
        )}

        {repositoryUrl && !isCreator && (
          <Alert severity={lastJobFailedOnToken ? 'warning' : 'info'}>
            {t(
              lastJobFailedOnToken
                ? 'pages.portfolio.ingestion.creatorTokenFailed'
                : 'pages.portfolio.ingestion.creatorToken',
            )}
          </Alert>
        )}

        {credentialQuery.isError && (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={() => void credentialQuery.refetch()}>
                {t('pages.portfolio.detail.retry')}
              </Button>
            }
          >
            {translateError(
              credentialQuery.error,
              t,
              'errors.portfolio_assessment_github_credential_load_failed',
            )}
          </Alert>
        )}

        {showTokenForm && (
          <GithubTokenForm replacing={tokenConfigured} onSaved={() => setTokenSaved(true)} />
        )}

        <Box>
          <Typography variant="subtitle2" gutterBottom>
            {t('pages.portfolio.ingestion.zipTitle')}
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 1 }}>
            {t('pages.portfolio.ingestion.zipHelp', { max_mb: PORTFOLIO_MAX_ARCHIVE_MB })}
          </Typography>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,application/zip"
            hidden
            onChange={handleFileChange}
            data-testid="portfolio-ingestion-file-input"
          />
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Button variant="outlined" onClick={() => fileInputRef.current?.click()} disabled={busy}>
              {t('pages.portfolio.ingestion.chooseFile')}
            </Button>
            {file && (
              <Typography variant="body2" data-testid="portfolio-ingestion-file-name">
                {t('pages.portfolio.ingestion.fileInfo', {
                  name: file.name,
                  size: formatMegabytes(file.size),
                })}
              </Typography>
            )}
            <Button
              variant="contained"
              onClick={() => file && uploadMutation.mutate(file)}
              disabled={!file || fileTooLarge || waitingForToken || busy}
              data-testid="portfolio-ingestion-upload"
            >
              {t('pages.portfolio.ingestion.upload')}
            </Button>
          </Stack>
          {fileTooLarge && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {t('errors.portfolio_assessment_archive_too_large', {
                max_mb: PORTFOLIO_MAX_ARCHIVE_MB,
              })}
            </Alert>
          )}
          {progress !== null && (
            <Box sx={{ mt: 1.5 }} data-testid="portfolio-ingestion-upload-progress">
              <LinearProgress variant="determinate" value={Math.round(progress * 100)} />
              <Typography variant="caption" color="textSecondary">
                {t('pages.portfolio.ingestion.uploading', { percent: Math.round(progress * 100) })}
              </Typography>
            </Box>
          )}
        </Box>

        {repositoryUrl && (
          <>
            <Divider />
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                {t('pages.portfolio.ingestion.githubTitle')}
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mb: 1 }}>
                {t('pages.portfolio.ingestion.githubHelp')}
              </Typography>
              <Button
                variant="contained"
                onClick={() => ingestMutation.mutate()}
                disabled={waitingForToken || busy}
                data-testid="portfolio-ingestion-github"
              >
                {t('pages.portfolio.ingestion.githubStart')}
              </Button>
            </Box>
          </>
        )}

        <PortfolioMutationError
          error={uploadMutation.error}
          message={uploadMutation.error ? translateError(uploadMutation.error, t, 'errors.portfolio_assessment_upload_failed') : ''}
        />
        <PortfolioMutationError
          error={ingestMutation.error}
          message={ingestMutation.error ? translateError(ingestMutation.error, t, 'errors.portfolio_assessment_ingest_failed') : ''}
        />
      </Stack>
    </Paper>
  );
};
