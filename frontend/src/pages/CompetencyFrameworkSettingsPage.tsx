import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  ToggleButtonGroup,
  ToggleButton,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { competencyFrameworksApi } from '../api/competencyFrameworksApi';
import type {
  CompetencyFramework,
  FrameworkCreatePayload,
} from '../types/competencyFramework';
import CompetencyFrameworkCard from '../components/competencyFrameworks/CompetencyFrameworkCard';
import CompetencyFrameworkForm from '../components/competencyFrameworks/CompetencyFrameworkForm';

type FilterMode = 'all' | 'active' | 'archived';
const FILTER_KEY = 'competencyFrameworks.filter';
const QUERY_KEY = 'competency-frameworks';

const extractApiDetail = (err: unknown, fallback: string): string => {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
  }
  return fallback;
};

const loadFilter = (): FilterMode => {
  const stored = localStorage.getItem(FILTER_KEY) as FilterMode | null;
  return stored === 'all' || stored === 'archived' ? stored : 'active';
};

const CompetencyFrameworkSettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const { user, hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [filter, setFilterState] = useState<FilterMode>(loadFilter);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<CompetencyFramework | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const setFilter = (value: FilterMode | null) => {
    if (!value) return;
    localStorage.setItem(FILTER_KEY, value);
    setFilterState(value);
  };

  const includeArchived = filter !== 'active';
  const query = useQuery({
    queryKey: [QUERY_KEY, includeArchived],
    queryFn: () => competencyFrameworksApi.listFrameworks(includeArchived),
  });

  const frameworks = (query.data ?? []).filter((fw) =>
    filter === 'archived' ? fw.is_archived : true
  );

  const invalidate = () => queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });

  const createMutation = useMutation({
    mutationFn: (payload: FrameworkCreatePayload) =>
      competencyFrameworksApi.createFramework(payload),
    onSuccess: () => { invalidate(); setDialogOpen(false); },
    onError: (e) => setActionError(extractApiDetail(e, t('competencyFrameworks.errorCreate'))),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: FrameworkCreatePayload }) =>
      competencyFrameworksApi.updateFramework(id, payload),
    onSuccess: () => { invalidate(); setDialogOpen(false); setEditing(null); },
    onError: (e) => setActionError(extractApiDetail(e, t('competencyFrameworks.errorUpdate'))),
  });

  const archiveMutation = useMutation({
    mutationFn: (fw: CompetencyFramework) =>
      fw.is_archived
        ? competencyFrameworksApi.unarchiveFramework(fw.id)
        : competencyFrameworksApi.archiveFramework(fw.id),
    onSuccess: () => { setActionError(null); invalidate(); },
    onError: (e) => setActionError(extractApiDetail(e, t('competencyFrameworks.errorArchive'))),
  });

  const canManage = (fw: CompetencyFramework) =>
    fw.created_by === user?.id || hasPermission('manage_settings');

  const openCreate = () => { setEditing(null); setActionError(null); setDialogOpen(true); };
  const openEdit = (fw: CompetencyFramework) => { setEditing(fw); setActionError(null); setDialogOpen(true); };

  const handleSubmit = (payload: FrameworkCreatePayload) => {
    if (editing) updateMutation.mutate({ id: editing.id, payload });
    else createMutation.mutate(payload);
  };

  return (
    <Box sx={{ maxWidth: 'lg', mx: 'auto', p: 3 }} data-testid="competency-frameworks-content">
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="h4">{t('competencyFrameworks.title')}</Typography>
        <Button variant="contained" onClick={openCreate}>
          {t('competencyFrameworks.new')}
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t('competencyFrameworks.subtitle')}
      </Typography>

      <ToggleButtonGroup
        size="small"
        exclusive
        value={filter}
        onChange={(_, v) => setFilter(v)}
        sx={{ mb: 3 }}
      >
        <ToggleButton value="active">{t('competencyFrameworks.filter.active')}</ToggleButton>
        <ToggleButton value="all">{t('competencyFrameworks.filter.all')}</ToggleButton>
        <ToggleButton value="archived">{t('competencyFrameworks.filter.archived')}</ToggleButton>
      </ToggleButtonGroup>

      {actionError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      )}

      {query.isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : query.isError ? (
        <Alert severity="error">
          {extractApiDetail(query.error, t('competencyFrameworks.errorLoad'))}
        </Alert>
      ) : frameworks.length === 0 ? (
        <Alert severity="info">{t('competencyFrameworks.empty')}</Alert>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {frameworks.map((fw) => (
            <CompetencyFrameworkCard
              key={fw.id}
              framework={fw}
              canManage={canManage(fw)}
              onEdit={openEdit}
              onArchiveToggle={(f) => archiveMutation.mutate(f)}
            />
          ))}
        </Box>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editing ? t('competencyFrameworks.editTitle') : t('competencyFrameworks.new')}
        </DialogTitle>
        <DialogContent>
          <CompetencyFrameworkForm
            mode={editing ? 'edit' : 'create'}
            initial={
              editing
                ? {
                    name: editing.name,
                    module_code: editing.module_code ?? '',
                    description: editing.description ?? '',
                    rendered_text: editing.rendered_text,
                    language: editing.language,
                    visibility: editing.visibility,
                    org_unit_id: editing.org_unit_id,
                  }
                : undefined
            }
            submitting={createMutation.isPending || updateMutation.isPending}
            onSubmit={handleSubmit}
            onCancel={() => { setDialogOpen(false); setEditing(null); }}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default CompetencyFrameworkSettingsPage;
