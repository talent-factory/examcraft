import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box, FormControl, InputLabel, MenuItem, Select, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, TablePagination,
  Paper, TextField, CircularProgress, Alert, Chip, Checkbox, FormControlLabel,
} from '@mui/material';
import { fetchAuditLogs } from '../../services/auditService';
import { AuditCategory, AuditLogItem, AuditQueryParams } from '../../types/audit';

interface AuditLogViewProps {
  /** Drives which categories + filters are offered (server still enforces scope). */
  isSuperuser: boolean;
}

const CATEGORIES_BASE: AuditCategory[] = ['business', 'admin'];
const CATEGORIES_SUPER: AuditCategory[] = ['business', 'admin', 'auth', 'security'];

// TF-761: impersonation.start/impersonation.end live in the "admin" category
// alongside unrelated actions (create_user, assign_role, ...), so isolating
// them needs an exact action filter, not just category=admin. The backend
// OR-matches a CSV of actions (mirrors the `category` param).
const IMPERSONATION_ACTIONS = 'impersonation.start,impersonation.end';

const AuditLogView: React.FC<AuditLogViewProps> = ({ isSuperuser }) => {
  const { t } = useTranslation();
  const [rows, setRows] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [category, setCategory] = useState<AuditCategory | ''>('');
  const [status, setStatus] = useState<string>('');
  const [institutionId, setInstitutionId] = useState<string>('');
  const [impersonationOnly, setImpersonationOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const availableCategories = isSuperuser ? CATEGORIES_SUPER : CATEGORIES_BASE;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: AuditQueryParams = {
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      };
      if (impersonationOnly) {
        // This exact-action filter is a narrower subset of category=admin,
        // so sending both would be redundant at best — and would needlessly
        // restrict results (to nothing) if a stale category were ever set.
        params.action = IMPERSONATION_ACTIONS;
      } else if (category) {
        params.category = [category];
      }
      if (status) params.status = status as AuditQueryParams['status'];
      if (isSuperuser && institutionId) {
        const instId = Number(institutionId);
        if (Number.isFinite(instId)) params.institution_id = instId;
      }
      const data = await fetchAuditLogs(params);
      setRows(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('pages.admin.audit.loadError'));
    } finally {
      setLoading(false);
    }
  }, [category, status, institutionId, impersonationOnly, isSuperuser, page, rowsPerPage, t]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Box data-testid="audit-log-view">
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 160 }} disabled={impersonationOnly}>
          <InputLabel>{t('pages.admin.audit.filterCategory')}</InputLabel>
          <Select
            data-testid="audit-filter-category"
            value={category}
            label={t('pages.admin.audit.filterCategory')}
            onChange={(e) => { setPage(0); setCategory(e.target.value as AuditCategory | ''); }}
          >
            <MenuItem value="">{t('pages.admin.audit.filterAll')}</MenuItem>
            {availableCategories.map((c) => (
              <MenuItem key={c} value={c}>{t(`pages.admin.audit.category.${c}`)}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControlLabel
          sx={{ ml: 0 }}
          control={
            <Checkbox
              data-testid="audit-filter-impersonation-only"
              checked={impersonationOnly}
              onChange={(e) => {
                setPage(0);
                setImpersonationOnly(e.target.checked);
                if (e.target.checked) setCategory('');
              }}
            />
          }
          label={t('pages.admin.audit.filterImpersonationOnly')}
        />

        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>{t('pages.admin.audit.filterStatus')}</InputLabel>
          <Select
            data-testid="audit-filter-status"
            value={status}
            label={t('pages.admin.audit.filterStatus')}
            onChange={(e) => { setPage(0); setStatus(e.target.value); }}
          >
            <MenuItem value="">{t('pages.admin.audit.filterAll')}</MenuItem>
            <MenuItem value="success">success</MenuItem>
            <MenuItem value="failure">failure</MenuItem>
            <MenuItem value="error">error</MenuItem>
          </Select>
        </FormControl>

        {isSuperuser && (
          <TextField
            data-testid="audit-filter-institution"
            size="small"
            label={t('pages.admin.audit.filterInstitution')}
            value={institutionId}
            onChange={(e) => { setPage(0); setInstitutionId(e.target.value); }}
          />
        )}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading && <CircularProgress size={24} />}

      <TableContainer component={Paper}>
        <Table size="small" aria-label="audit-log">
          <TableHead>
            <TableRow>
              <TableCell>{t('pages.admin.audit.colTime')}</TableCell>
              <TableCell>{t('pages.admin.audit.colActor')}</TableCell>
              <TableCell>{t('pages.admin.audit.colCategory')}</TableCell>
              <TableCell>{t('pages.admin.audit.colAction')}</TableCell>
              <TableCell>{t('pages.admin.audit.colResource')}</TableCell>
              <TableCell>{t('pages.admin.audit.colStatus')}</TableCell>
              {isSuperuser && <TableCell>{t('pages.admin.audit.colIp')}</TableCell>}
              {isSuperuser && <TableCell>{t('pages.admin.audit.colUserAgent')}</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>{new Date(row.created_at).toLocaleString()}</TableCell>
                <TableCell>
                  {row.actor ?? '—'}
                  {row.impersonator && (
                    <Chip
                      data-testid="audit-impersonated-chip"
                      size="small"
                      color="warning"
                      sx={{ ml: 1 }}
                      label={t('pages.admin.audit.impersonatedBy', { name: row.impersonator })}
                      title={t('pages.admin.audit.impersonatedByTooltip', { name: row.impersonator })}
                    />
                  )}
                </TableCell>
                <TableCell><Chip size="small" label={row.category} /></TableCell>
                <TableCell>{row.action}</TableCell>
                <TableCell>{row.resource_type ? `${row.resource_type}#${row.resource_id ?? '?'}` : '—'}</TableCell>
                <TableCell>{row.status}</TableCell>
                {isSuperuser && <TableCell>{row.ip_address ?? '—'}</TableCell>}
                {isSuperuser && (
                  <TableCell
                    sx={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    title={row.user_agent ?? undefined}
                  >
                    {row.user_agent ?? '—'}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        component="div"
        count={total}
        page={page}
        onPageChange={(_e, p) => setPage(p)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
        rowsPerPageOptions={[25, 50, 100]}
      />
    </Box>
  );
};

export default AuditLogView;
