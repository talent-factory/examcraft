/**
 * `/portfolio` — assessment list (TF-989).
 *
 * Server-side filters (status, review status, template) and paging on the
 * enriched list of TF-986. While any row on the page has an active job the
 * list refreshes itself, so the last job's progress stays current. Creating
 * opens the new assessment's detail page, where the upload happens.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import { Add as AddIcon, DeleteOutline as DeleteIcon } from '@mui/icons-material';
import { portfolioApi } from '../../api/portfolioApi';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';
import { useFeatures } from '../../hooks/useFeatures';
import {
  isPortfolioJobActive,
  portfolioAssessmentsQueryKey,
} from '../../hooks/usePortfolioAssessment';
import {
  PortfolioUpgradePrompt,
  isPortfolioTierError,
} from '../../components/portfolio/PortfolioGate';
import {
  ASSESSMENT_STATUSES,
  JOB_STATUSES,
  JOB_TYPES,
  REVIEW_STATUSES,
  portfolioLabel,
} from '../../components/portfolio/portfolioLabels';
import { PortfolioAssessmentCreateDialog } from '../../components/portfolio/PortfolioAssessmentCreateDialog';
import { PortfolioAssessmentDeleteDialog } from '../../components/portfolio/PortfolioAssessmentDeleteDialog';
import { portfolioTemplatesQueryKey } from './PortfolioTemplatesPage';
import type {
  PortfolioAssessmentListItem,
  PortfolioAssessmentListParams,
  PortfolioAssessmentReviewStatus,
  PortfolioAssessmentStatusFilter,
} from '../../types/portfolio';

export { portfolioAssessmentsQueryKey };

const LIST_REFRESH_MS = 5000;
const ROWS_PER_PAGE_OPTIONS = [10, 25, 50];

const STATUS_COLOR: Record<
  PortfolioAssessmentStatusFilter,
  'default' | 'info' | 'primary' | 'success' | 'error'
> = {
  uploading: 'default',
  classifying: 'info',
  ready_to_grade: 'primary',
  grading: 'info',
  grading_failed: 'error',
  completed: 'success',
  failed: 'error',
};

/**
 * TF-1000: a failed grade run leaves the assessment on `grading` so it can be
 * resumed. The list shows that as its own value (derived from the newest job,
 * the same one the backend's `grading_failed` filter looks at) instead of
 * «Bewertung läuft».
 */
const STATUS_FILTERS: readonly PortfolioAssessmentStatusFilter[] = [
  ...ASSESSMENT_STATUSES.slice(0, ASSESSMENT_STATUSES.indexOf('grading') + 1),
  'grading_failed',
  ...ASSESSMENT_STATUSES.slice(ASSESSMENT_STATUSES.indexOf('grading') + 1),
];

function displayStatus(item: PortfolioAssessmentListItem): PortfolioAssessmentStatusFilter {
  const job = item.job;
  return item.status === 'grading' && job?.job_type === 'grade' && job.status === 'failed'
    ? 'grading_failed'
    : item.status;
}

const REVIEW_COLOR: Record<PortfolioAssessmentReviewStatus, 'default' | 'warning' | 'success'> = {
  pending_review: 'default',
  partially_reviewed: 'warning',
  fully_reviewed: 'success',
};

const LastJobCell: React.FC<{ item: PortfolioAssessmentListItem }> = ({ item }) => {
  const { t } = useTranslation();
  const job = item.job;
  if (!job) {
    return (
      <Typography variant="body2" color="textSecondary">
        {t('pages.portfolio.list.noJob')}
      </Typography>
    );
  }
  const hasProgress = typeof job.files_total === 'number' && job.files_total > 0;
  return (
    <Box>
      <Typography variant="body2">
        {portfolioLabel(t, 'job.type', job.job_type, JOB_TYPES)}
        {' · '}
        {portfolioLabel(t, 'job.status', job.status, JOB_STATUSES)}
      </Typography>
      {hasProgress && (
        <Typography variant="caption" color="textSecondary">
          {t('pages.portfolio.job.progress', { done: job.files_done, total: job.files_total })}
        </Typography>
      )}
    </Box>
  );
};

const PortfolioAssessmentsPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const { tier } = useFeatures();
  const canManage = hasPermission('portfolio_assessments:manage');

  const [status, setStatus] = useState<PortfolioAssessmentStatusFilter | ''>('');
  const [reviewStatus, setReviewStatus] = useState<PortfolioAssessmentReviewStatus | ''>('');
  const [templateId, setTemplateId] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [createOpen, setCreateOpen] = useState(false);
  const [toDelete, setToDelete] = useState<PortfolioAssessmentListItem | null>(null);

  const params: PortfolioAssessmentListParams = {
    ...(status && { status }),
    ...(reviewStatus && { review_status: reviewStatus }),
    ...(templateId && { template_id: templateId }),
    limit: rowsPerPage,
    offset: page * rowsPerPage,
  };

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [...portfolioAssessmentsQueryKey, params],
    queryFn: () => portfolioApi.listAssessments(params),
    placeholderData: keepPreviousData,
    refetchInterval: (q) =>
      q.state.data?.items.some((item) => isPortfolioJobActive(item.job)) ? LIST_REFRESH_MS : false,
  });

  // All templates, inactive ones included: older assessments still use them.
  // `portfolio_templates:read` is a separate opt-in; without it the filter goes.
  const canReadTemplates = hasPermission('portfolio_templates:read');
  const templatesQuery = useQuery({
    queryKey: portfolioTemplatesQueryKey,
    queryFn: () => portfolioApi.listTemplates(),
    enabled: canReadTemplates,
  });

  // Deleting the last row of the last page would otherwise leave an empty page.
  const pageEmpty = !!data && data.items.length === 0 && page > 0;
  useEffect(() => {
    if (pageEmpty) setPage((current) => Math.max(0, current - 1));
  }, [pageEmpty]);

  if (isPortfolioTierError(error)) {
    return <PortfolioUpgradePrompt currentTier={tier} />;
  }

  const filtered = status !== '' || reviewStatus !== '' || templateId !== '';
  const items = data?.items ?? [];

  const onFilter = <T,>(setter: (value: T) => void) => (value: T) => {
    setter(value);
    setPage(0);
  };

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
        {canManage && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateOpen(true)}
            data-testid="portfolio-create-open"
          >
            {t('pages.portfolio.list.create')}
          </Button>
        )}
      </Box>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel id="portfolio-filter-status-label" shrink>
            {t('pages.portfolio.list.filterStatus')}
          </InputLabel>
          <Select
            displayEmpty
            notched
            labelId="portfolio-filter-status-label"
            label={t('pages.portfolio.list.filterStatus')}
            value={status}
            onChange={(e) => onFilter(setStatus)(e.target.value as PortfolioAssessmentStatusFilter | '')}
            data-testid="portfolio-filter-status"
          >
            <MenuItem value="">{t('pages.portfolio.list.filterAll')}</MenuItem>
            {STATUS_FILTERS.map((value) => (
              <MenuItem key={value} value={value}>
                {t(`pages.portfolio.status.${value}`)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel id="portfolio-filter-review-label" shrink>
            {t('pages.portfolio.list.filterReview')}
          </InputLabel>
          <Select
            displayEmpty
            notched
            labelId="portfolio-filter-review-label"
            label={t('pages.portfolio.list.filterReview')}
            value={reviewStatus}
            onChange={(e) =>
              onFilter(setReviewStatus)(e.target.value as PortfolioAssessmentReviewStatus | '')
            }
            data-testid="portfolio-filter-review"
          >
            <MenuItem value="">{t('pages.portfolio.list.filterAll')}</MenuItem>
            {REVIEW_STATUSES.map((value) => (
              <MenuItem key={value} value={value}>
                {t(`pages.portfolio.reviewStatus.${value}`)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        {canReadTemplates && (
          <FormControl size="small" sx={{ minWidth: 240 }}>
            <InputLabel id="portfolio-filter-template-label" shrink>
              {t('pages.portfolio.list.filterTemplate')}
            </InputLabel>
            <Select
              displayEmpty
              notched
              labelId="portfolio-filter-template-label"
              label={t('pages.portfolio.list.filterTemplate')}
              value={templateId}
              onChange={(e) => onFilter(setTemplateId)(e.target.value)}
              data-testid="portfolio-filter-template"
            >
              <MenuItem value="">{t('pages.portfolio.list.filterAll')}</MenuItem>
              {(templatesQuery.data ?? []).map((template) => (
                <MenuItem key={template.id} value={template.id}>
                  {template.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </Stack>

      {isLoading && <CircularProgress />}

      {error != null && !data && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {translateError(error, t, 'errors.portfolio_assessment_list_failed')}
        </Alert>
      )}
      {/* A failed refresh keeps the last page on screen: say it may be outdated. */}
      {error != null && data && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => void refetch()}>
              {t('pages.portfolio.detail.retry')}
            </Button>
          }
        >
          {t('pages.portfolio.detail.refreshFailed', {
            reason: translateError(error, t, 'errors.portfolio_assessment_list_failed'),
          })}
        </Alert>
      )}
      {templatesQuery.isError && (
        <Typography variant="body2" color="error" sx={{ mb: 2 }}>
          {translateError(templatesQuery.error, t, 'errors.portfolio_template_list_failed')}
        </Typography>
      )}

      {data && items.length === 0 && (
        <Typography color="textSecondary">
          {t(filtered ? 'pages.portfolio.list.emptyFiltered' : 'pages.portfolio.list.empty')}
        </Typography>
      )}

      {data && items.length > 0 && (
        <>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t('pages.portfolio.list.columnStudent')}</TableCell>
                <TableCell>{t('pages.portfolio.list.columnTemplate')}</TableCell>
                <TableCell>{t('pages.portfolio.list.columnStatus')}</TableCell>
                <TableCell>{t('pages.portfolio.list.columnReview')}</TableCell>
                <TableCell>{t('pages.portfolio.list.columnLastJob')}</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => {
                const jobActive = isPortfolioJobActive(item.job);
                return (
                  <TableRow key={item.id} data-testid={`portfolio-row-${item.id}`}>
                    <TableCell>
                      <Typography variant="body2">{item.student_name}</Typography>
                      {item.student_name !== item.student_external_id && (
                        <Typography variant="caption" color="textSecondary">
                          {item.student_external_id}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{item.template_name}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={STATUS_COLOR[displayStatus(item)] ?? 'default'}
                        label={portfolioLabel(t, 'status', displayStatus(item), STATUS_FILTERS)}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        variant="outlined"
                        color={REVIEW_COLOR[item.review_status] ?? 'default'}
                        label={portfolioLabel(
                          t,
                          'reviewStatus',
                          item.review_status,
                          REVIEW_STATUSES,
                        )}
                      />
                    </TableCell>
                    <TableCell>
                      <LastJobCell item={item} />
                    </TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <Button component={RouterLink} to={`/portfolio/${item.id}`} size="small">
                        {t('pages.portfolio.list.open')}
                      </Button>
                      {canManage && (
                        <Tooltip
                          title={t(
                            jobActive
                              ? 'pages.portfolio.list.deleteBlocked'
                              : 'pages.portfolio.list.delete',
                          )}
                        >
                          {/* span: a disabled button fires no events for the tooltip. */}
                          <span>
                            <IconButton
                              size="small"
                              aria-label={t('pages.portfolio.list.delete')}
                              disabled={jobActive}
                              onClick={() => setToDelete(item)}
                              data-testid={`portfolio-delete-${item.id}`}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={data.total}
            page={page}
            rowsPerPage={rowsPerPage}
            rowsPerPageOptions={ROWS_PER_PAGE_OPTIONS}
            onPageChange={(_, next) => setPage(next)}
            onRowsPerPageChange={(e) => {
              setRowsPerPage(Number(e.target.value));
              setPage(0);
            }}
            labelRowsPerPage={t('pages.portfolio.list.rowsPerPage')}
            labelDisplayedRows={({ from, to, count }) =>
              t('pages.portfolio.list.displayedRows', { from, to, count })
            }
          />
        </>
      )}

      <PortfolioAssessmentCreateDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(id) => {
          setCreateOpen(false);
          navigate(`/portfolio/${id}`);
        }}
      />
      <PortfolioAssessmentDeleteDialog assessment={toDelete} onClose={() => setToDelete(null)} />
    </Box>
  );
};

export default PortfolioAssessmentsPage;
