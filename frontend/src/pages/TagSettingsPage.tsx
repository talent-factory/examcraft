import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  ToggleButtonGroup,
  ToggleButton,
  Chip,
  IconButton,
  Button,
  Tooltip,
  Checkbox,
  Paper,
  Alert,
  CircularProgress,
  Divider,
  InputAdornment,
} from '@mui/material';
import { Edit, Archive, Unarchive, Merge, Delete as DeleteIcon, Search as SearchIcon } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { tagsApi, type Tag } from '../api/tagsApi';
import { useAuth } from '../contexts/AuthContext';
import TagRenameInline from '../components/tags/TagRenameInline';
import TagMergeModal from '../components/tags/TagMergeModal';
import TagCreateForm from '../components/tags/TagCreateForm';
import { apiDetail, translateError } from '../errors';

type FilterMode = 'all' | 'active' | 'archived';

const VALID_FILTERS: FilterMode[] = ['all', 'active', 'archived'];
const FILTER_STORAGE_KEY = 'tagSettings.filter';

const loadFilter = (): FilterMode => {
  const stored = localStorage.getItem(FILTER_STORAGE_KEY);
  return VALID_FILTERS.includes(stored as FilterMode) ? (stored as FilterMode) : 'active';
};

const TagSettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  const { hasPermission, user } = useAuth();
  const isAdmin = hasPermission('manage_settings');
  const isSuperuser = user?.is_superuser === true;

  const [filter, setFilterState] = useState<FilterMode>(loadFilter);
  const setFilter = (v: FilterMode) => {
    localStorage.setItem(FILTER_STORAGE_KEY, v);
    setFilterState(v);
  };

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const [search, setSearch] = useState('');
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [mergeOpen, setMergeOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: allTags = [], isLoading } = useQuery({
    queryKey: ['tags', 'settings'],
    queryFn: () => tagsApi.listTags(true),
    staleTime: 0,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['tags'] });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      tagsApi.renameTag(id, name),
    onSuccess: () => {
      invalidate();
      setRenamingId(null);
    },
    onError: (err) => setError(apiDetail(err) ?? translateError(err, t, 'components.tags.renameFailed')),
  });

  const archiveMutation = useMutation({
    mutationFn: (id: number) => tagsApi.archiveTag(id),
    onSuccess: invalidate,
    onError: (err) => setError(apiDetail(err) ?? translateError(err, t, 'components.tags.archiveFailed')),
  });

  const unarchiveMutation = useMutation({
    mutationFn: (id: number) => tagsApi.unarchiveTag(id),
    onSuccess: invalidate,
    onError: (err) => setError(apiDetail(err) ?? translateError(err, t, 'components.tags.restoreFailed')),
  });

  const mergeMutation = useMutation({
    mutationFn: ({ sourceIds, targetId }: { sourceIds: number[]; targetId: number }) =>
      tagsApi.mergeTags(sourceIds, targetId),
    onSuccess: () => {
      invalidate();
      setSelectedIds(new Set());
      setMergeOpen(false);
    },
    onError: (err) => setError(apiDetail(err) ?? translateError(err, t, 'components.tags.mergeFailed')),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => tagsApi.deleteTag(id),
    onSuccess: () => {
      invalidate();
      setSelectedIds(new Set());
    },
    onError: (err) => setError(apiDetail(err) ?? translateError(err, t, 'components.tags.deleteFailed')),
  });

  const filteredTags = allTags
    .filter((t) => {
      if (filter === 'active') return !t.is_archived;
      if (filter === 'archived') return t.is_archived;
      return true;
    })
    .filter((t) => t.name.toLowerCase().includes(search.toLowerCase()));

  const filteredInstitution = filteredTags.filter((t) => t.scope === 'institution');
  const filteredGlobal = filteredTags.filter((t) => t.scope === 'global');

  const ownInstitutionTags = filteredInstitution.filter((t) => t.is_own);
  const othersInstitutionTags = filteredInstitution.filter((t) => !t.is_own);

  const selectedTags = allTags.filter((t) => selectedIds.has(t.id));

  const countAll = allTags.length;
  const countActive = allTags.filter((t) => !t.is_archived).length;
  const countArchived = allTags.filter((t) => t.is_archived).length;

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <Box sx={{ p: 3, maxWidth: 800 }} data-testid="tag-settings-content">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        {/* TF-506: Titel nutzt den Sidebar-Key, damit Seitentitel und Navigation synchron bleiben */}
        <Typography variant="h5" fontWeight="bold">
          {t('nav.sidebar.tagSettings')}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Neuen Tag erstellen — isolierte Komponente, re-rendert die Liste nicht */}
      <TagCreateForm existingTags={allTags} />

      {/* Trennlinie */}
      <Divider sx={{ mb: 2 }}>
        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
          {t('components.tags.existingTags')}
        </Typography>
      </Divider>

      {/* Suchfeld + Filter */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
        <TextField
          size="small"
          placeholder={t('components.tags.searchPlaceholder')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ flex: 1 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: 'text.disabled' }} />
              </InputAdornment>
            ),
          }}
        />
        <ToggleButtonGroup
          size="small"
          value={filter}
          exclusive
          onChange={(_, v) => v && setFilter(v)}
        >
          <ToggleButton value="all">{t('components.tags.filterAll')} ({countAll})</ToggleButton>
          <ToggleButton value="active">{t('components.tags.filterActive')} ({countActive})</ToggleButton>
          <ToggleButton value="archived">{t('components.tags.filterArchived')} ({countArchived})</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Merge-Aktion — nur für Admins */}
      {isAdmin && selectedIds.size >= 2 && (
        <Box sx={{ mb: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Merge />}
            onClick={() => setMergeOpen(true)}
            color="secondary"
          >
            {t('components.tags.mergeSelectionButton', { count: selectedIds.size })}
          </Button>
        </Box>
      )}

      {/* Tag-Liste */}
      {isLoading ? (
        <CircularProgress />
      ) : (
        <Paper variant="outlined">
          {filteredTags.length === 0 && (
            <Box sx={{ p: 2 }}>
              <Typography variant="body2" color="text.secondary">
                {t('components.tags.noneFound')}
              </Typography>
            </Box>
          )}
          {(() => {
            type DisplayItem =
              | { type: 'header'; label: string; scope?: 'institution' | 'global'; count: number }
              | { type: 'tag'; tag: Tag; readonly: boolean };

            const items: DisplayItem[] = [];

            if (isAdmin) {
              if (filteredInstitution.length > 0) {
                items.push({ type: 'header', label: t('components.tags.groupInstitution'), scope: 'institution', count: filteredInstitution.length });
              }
              filteredInstitution.forEach((tag) => items.push({ type: 'tag', tag, readonly: false }));
              if (filteredGlobal.length > 0) {
                items.push({ type: 'header', label: t('components.tags.groupGlobal'), scope: 'global', count: filteredGlobal.length });
              }
              filteredGlobal.forEach((tag) => items.push({ type: 'tag', tag, readonly: !isSuperuser }));
            } else {
              if (ownInstitutionTags.length > 0) {
                items.push({ type: 'header', label: t('components.tags.myTags'), scope: 'institution', count: ownInstitutionTags.length });
                ownInstitutionTags.forEach((tag) => items.push({ type: 'tag', tag, readonly: false }));
              }
              if (othersInstitutionTags.length > 0) {
                items.push({ type: 'header', label: t('components.tags.institutionTags'), scope: 'institution', count: othersInstitutionTags.length });
                othersInstitutionTags.forEach((tag) => items.push({ type: 'tag', tag, readonly: true }));
              }
              if (filteredGlobal.length > 0) {
                items.push({ type: 'header', label: t('components.tags.groupGlobal'), scope: 'global', count: filteredGlobal.length });
                filteredGlobal.forEach((tag) => items.push({ type: 'tag', tag, readonly: true }));
              }
            }

            return items.map((item, idx) => {
              if (item.type === 'header') {
                return (
                  <Box
                    key={`header-${item.label}`}
                    sx={{
                      px: 2,
                      py: 0.75,
                      bgcolor: item.scope === 'institution' ? '#e8f4ff' : '#f5f5f5',
                      borderBottom: '1px solid',
                      borderTop: idx > 0 ? '1px solid' : 'none',
                      borderColor: 'divider',
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        fontWeight: 700,
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                        color: item.scope === 'institution' ? '#1565c0' : '#757575',
                      }}
                    >
                      {item.label} ({item.count})
                    </Typography>
                  </Box>
                );
              }

              const tag = item.tag;
              const prevItem = items[idx - 1];
              const showDivider = idx > 0 && prevItem?.type === 'tag';

              return (
                <React.Fragment key={tag.id}>
                  {showDivider && <Divider />}
                  <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                    {(tag.scope === 'global' ? isSuperuser : isAdmin) && (
                      !tag.is_archived ? (
                        <Checkbox
                          size="small"
                          checked={selectedIds.has(tag.id)}
                          onChange={() => toggleSelect(tag.id)}
                        />
                      ) : (
                        <Box sx={{ width: 34 }} />
                      )
                    )}

                    {renamingId === tag.id ? (
                      <TagRenameInline
                        currentName={tag.name}
                        // mutateAsync rejects on failure even though onError above
                        // already sets the error state — swallow it here so
                        // TagRenameInline's uncaught `await onSave(...)` doesn't
                        // surface as an unhandled promise rejection. The `async`
                        // wrapper (rather than .catch(() => {}), which would still
                        // leak mutateAsync's Tag resolution type through the union)
                        // is what makes this satisfy the Promise<void> prop type.
                        onSave={async (name) => {
                          try {
                            await renameMutation.mutateAsync({ id: tag.id, name });
                          } catch {
                            // already surfaced via onError above
                          }
                        }}
                        onCancel={() => setRenamingId(null)}
                      />
                    ) : (
                      <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip
                          label={`#${tag.name}`}
                          size="small"
                          sx={{
                            opacity: tag.is_archived ? 0.5 : 1,
                            bgcolor: tag.is_archived
                              ? 'action.disabledBackground'
                              : tag.scope === 'global' ? '#e8f4ff' : 'secondary.50',
                            color: tag.is_archived
                              ? 'text.disabled'
                              : tag.scope === 'global' ? '#1565c0' : 'secondary.dark',
                          }}
                        />
                        {tag.is_archived && (
                          <Typography variant="caption" color="text.disabled">
                            {t('components.tags.archivedMarker')}
                          </Typography>
                        )}
                        <Typography
                          variant="caption"
                          sx={{
                            ml: 1,
                            color: tag.usage_count === 0 && tag.scope !== 'global'
                              ? 'warning.main'
                              : 'text.secondary',
                            fontWeight: tag.usage_count === 0 && tag.scope !== 'global'
                              ? 600
                              : 400,
                          }}
                        >
                          {t('components.tags.questionCount', { count: tag.usage_count })}
                        </Typography>
                      </Box>
                    )}

                    {renamingId !== tag.id && !item.readonly && (
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {!tag.is_archived && (tag.scope === 'global' ? isSuperuser : true) && (
                          <>
                            <Tooltip title={t('components.tags.rename')}>
                              <IconButton size="small" onClick={() => setRenamingId(tag.id)}>
                                <Edit fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title={t('components.tags.archive')}>
                              <IconButton size="small" onClick={() => archiveMutation.mutate(tag.id)}>
                                <Archive fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                        {tag.is_archived && (tag.scope === 'global' ? isSuperuser : true) && (
                          <Tooltip title={t('components.tags.restore')}>
                            <IconButton size="small" onClick={() => unarchiveMutation.mutate(tag.id)}>
                              <Unarchive fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {tag.is_archived && (tag.is_own || isAdmin) && tag.usage_count === 0 && (tag.scope === 'global' ? isSuperuser : true) && (
                          <Tooltip title={t('components.tags.delete')}>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => {
                                if (window.confirm(t('components.tags.confirmDelete', { name: tag.name }))) {
                                  deleteMutation.mutate(tag.id);
                                }
                              }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    )}
                  </Box>
                </React.Fragment>
              );
            });
          })()}
        </Paper>
      )}

      {/* Merge-Modal */}
      <TagMergeModal
        open={mergeOpen}
        selectedTags={selectedTags}
        // Deliberately still lets the rejection through (unlike
        // TagRenameInline's onSave above, which has no success-only
        // follow-up action): TagMergeModal.handleConfirm relies on it to
        // skip onClose() and keep the modal open on failure. The `async`
        // wrapper (rather than returning mutateAsync's Promise<Tag[]>
        // directly) is what makes this satisfy the Promise<void> prop type
        // without swallowing the rejection — see TagMergeModal.tsx for
        // where it's actually caught.
        onConfirm={async (sourceIds, targetId) => {
          await mergeMutation.mutateAsync({ sourceIds, targetId });
        }}
        onClose={() => setMergeOpen(false)}
      />
    </Box>
  );
};

export default TagSettingsPage;
