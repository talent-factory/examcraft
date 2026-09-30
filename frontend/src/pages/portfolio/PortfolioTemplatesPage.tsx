/**
 * `/portfolio/templates` — template list with editor (TF-987 scaffold, TF-988).
 *
 * A sub-page of `/portfolio`, not an admin tab: `/admin` is behind
 * `RoleGuard` (admins only), while the template permissions are opt-in per
 * role. Modelled on `AdminGradingSchemes`.
 *
 * Rights mirror `_assert_owner_or_superuser` in the backend: only the owner
 * (or a SuperUser) with `portfolio_templates:manage` may edit or delete;
 * everybody else opens the editor read-only.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { portfolioApi } from '../../api/portfolioApi';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';
import type { PortfolioTemplate } from '../../types/portfolio';
import PortfolioTemplateEditor from '../../components/portfolio/templates/PortfolioTemplateEditor';

export const portfolioTemplatesQueryKey = ['portfolioTemplates'] as const;

const KEY = 'pages.portfolio.templates';

/** `null`: editor closed; `template: null`: creating. */
type EditorState = null | { template: PortfolioTemplate | null };

const PortfolioTemplatesPage: React.FC = () => {
  const { t } = useTranslation();
  const { user, hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: portfolioTemplatesQueryKey,
    queryFn: () => portfolioApi.listTemplates(),
  });

  const [editor, setEditor] = useState<EditorState>(null);
  const [deleteTarget, setDeleteTarget] = useState<PortfolioTemplate | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const canManage = hasPermission('portfolio_templates:manage');
  const isOwn = (template: PortfolioTemplate) => user != null && template.created_by === user.id;
  const canEdit = (template: PortfolioTemplate) =>
    canManage && (Boolean(user?.is_superuser) || isOwn(template));

  const invalidate = () => queryClient.invalidateQueries({ queryKey: portfolioTemplatesQueryKey });

  const remove = useMutation({
    mutationFn: (template: PortfolioTemplate) => portfolioApi.deleteTemplate(template.id),
    onSuccess: () => {
      setDeleteTarget(null);
      invalidate();
    },
    onError: (err) => {
      // Coded errors (e.g. `portfolio_template_delete_blocked`) bring their
      // own message; the fallback covers everything uncoded.
      setDeleteError(translateError(err, t, 'errors.portfolio_template_delete_failed'));
      setDeleteTarget(null);
      // A 404 (deleted elsewhere) or a new blocking assessment: show current data.
      invalidate();
    },
  });

  const editorTemplate = editor?.template ?? null;

  return (
    <Box sx={{ p: 3 }} data-testid="portfolio-templates-page">
      {hasPermission('portfolio_assessments:read') && (
        <Button component={RouterLink} to="/portfolio" size="small" sx={{ mb: 1 }}>
          {t(`${KEY}.back`)}
        </Button>
      )}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2 }}>
        <Box>
          <Typography variant="h4" component="h1">
            {t(`${KEY}.title`)}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {t(`${KEY}.subtitle`)}
          </Typography>
        </Box>
        {canManage && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setEditor({ template: null })}
            data-testid="pt-create"
          >
            {t(`${KEY}.create`)}
          </Button>
        )}
      </Box>

      {deleteError && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setDeleteError(null)} data-testid="pt-delete-error">
          {deleteError}
        </Alert>
      )}

      {isLoading && <CircularProgress />}

      {error != null && (
        <Alert severity="error">
          {translateError(error, t, 'errors.portfolio_template_list_failed')}
        </Alert>
      )}

      {data && data.length === 0 && (
        <Typography color="textSecondary">{t(`${KEY}.empty`)}</Typography>
      )}

      {data && data.length > 0 && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" data-testid="pt-table">
            <TableHead>
              <TableRow>
                <TableCell>{t(`${KEY}.columns.name`)}</TableCell>
                <TableCell>{t(`${KEY}.columns.visibility`)}</TableCell>
                <TableCell>{t(`${KEY}.columns.phases`)}</TableCell>
                <TableCell>{t(`${KEY}.columns.version`)}</TableCell>
                <TableCell>{t(`${KEY}.columns.status`)}</TableCell>
                <TableCell align="right">{t(`${KEY}.columns.actions`)}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((template) => {
                const editable = canEdit(template);
                return (
                  <TableRow key={template.id} data-testid={`pt-row-${template.id}`}>
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1}>
                        {template.name}
                        {isOwn(template) && (
                          <Chip label={t(`${KEY}.own`)} size="small" variant="outlined" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>{t(`${KEY}.visibility.${template.visibility}`)}</TableCell>
                    <TableCell>{template.phases.length}</TableCell>
                    <TableCell>{template.version}</TableCell>
                    <TableCell>
                      <Chip
                        label={template.is_active ? t(`${KEY}.active`) : t(`${KEY}.inactive`)}
                        size="small"
                        color={template.is_active ? 'success' : 'default'}
                        variant={template.is_active ? 'filled' : 'outlined'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title={editable ? t(`${KEY}.edit`) : t(`${KEY}.view`)}>
                        <IconButton
                          size="small"
                          aria-label={`${editable ? t(`${KEY}.edit`) : t(`${KEY}.view`)}: ${template.name}`}
                          onClick={() => setEditor({ template })}
                          data-testid={`pt-open-${template.id}`}
                        >
                          {editable ? <EditIcon fontSize="small" /> : <ViewIcon fontSize="small" />}
                        </IconButton>
                      </Tooltip>
                      {editable && (
                        <Tooltip title={t(`${KEY}.delete`)}>
                          <IconButton
                            size="small"
                            color="error"
                            aria-label={`${t(`${KEY}.delete`)}: ${template.name}`}
                            onClick={() => {
                              setDeleteError(null);
                              setDeleteTarget(template);
                            }}
                            data-testid={`pt-delete-${template.id}`}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <PortfolioTemplateEditor
        open={editor !== null}
        template={editorTemplate}
        readOnly={editorTemplate !== null && !canEdit(editorTemplate)}
        onClose={() => setEditor(null)}
        onSaved={invalidate}
        onDeleted={invalidate}
      />

      <Dialog
        open={deleteTarget !== null}
        onClose={remove.isPending ? undefined : () => setDeleteTarget(null)}
        aria-labelledby="pt-delete-title"
        data-testid="pt-delete-dialog"
      >
        <DialogTitle id="pt-delete-title">{t(`${KEY}.deleteDialog.title`)}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t(`${KEY}.deleteDialog.body`, { name: deleteTarget?.name ?? '' })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={remove.isPending}>
            {t(`${KEY}.deleteDialog.cancel`)}
          </Button>
          <Button
            color="error"
            variant="contained"
            disabled={remove.isPending}
            onClick={() => deleteTarget && remove.mutate(deleteTarget)}
            data-testid="pt-delete-confirm"
          >
            {t(`${KEY}.deleteDialog.confirm`)}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PortfolioTemplatesPage;
