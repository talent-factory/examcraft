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
import axios from 'axios';
import { tagsApi, type Tag } from '../api/tagsApi';
import { useAuth } from '../contexts/AuthContext';
import TagRenameInline from '../components/tags/TagRenameInline';
import TagMergeModal from '../components/tags/TagMergeModal';
import TagCreateForm from '../components/tags/TagCreateForm';

const extractApiDetail = (err: unknown, fallback: string): string => {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
  }
  return fallback;
};

type FilterMode = 'all' | 'active' | 'archived';

const VALID_FILTERS: FilterMode[] = ['all', 'active', 'archived'];
const FILTER_STORAGE_KEY = 'tagSettings.filter';

const loadFilter = (): FilterMode => {
  const stored = localStorage.getItem(FILTER_STORAGE_KEY);
  return VALID_FILTERS.includes(stored as FilterMode) ? (stored as FilterMode) : 'active';
};

const TagSettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
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
    onError: (err) => setError(extractApiDetail(err, 'Umbenennen fehlgeschlagen.')),
  });

  const archiveMutation = useMutation({
    mutationFn: (id: number) => tagsApi.archiveTag(id),
    onSuccess: invalidate,
    onError: (err) => setError(extractApiDetail(err, 'Archivieren fehlgeschlagen.')),
  });

  const unarchiveMutation = useMutation({
    mutationFn: (id: number) => tagsApi.unarchiveTag(id),
    onSuccess: invalidate,
    onError: (err) => setError(extractApiDetail(err, 'Wiederherstellen fehlgeschlagen.')),
  });

  const mergeMutation = useMutation({
    mutationFn: ({ sourceIds, targetId }: { sourceIds: number[]; targetId: number }) =>
      tagsApi.mergeTags(sourceIds, targetId),
    onSuccess: () => {
      invalidate();
      setSelectedIds(new Set());
      setMergeOpen(false);
    },
    onError: (err) => setError(extractApiDetail(err, 'Zusammenführen fehlgeschlagen.')),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => tagsApi.deleteTag(id),
    onSuccess: () => {
      invalidate();
      setSelectedIds(new Set());
    },
    onError: (err) => setError(extractApiDetail(err, 'Löschen fehlgeschlagen.')),
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
    <Box sx={{ p: 3, maxWidth: 800 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" fontWeight="bold">
          Tag-Verwaltung
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
          Bestehende Tags
        </Typography>
      </Divider>

      {/* Suchfeld + Filter */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
        <TextField
          size="small"
          placeholder="Tags suchen..."
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
          <ToggleButton value="all">Alle ({countAll})</ToggleButton>
          <ToggleButton value="active">Aktiv ({countActive})</ToggleButton>
          <ToggleButton value="archived">Archiviert ({countArchived})</ToggleButton>
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
            {selectedIds.size} Tags zusammenführen
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
                Keine Tags gefunden.
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
                items.push({ type: 'header', label: 'Tags dieser Institution', scope: 'institution', count: filteredInstitution.length });
              }
              filteredInstitution.forEach((t) => items.push({ type: 'tag', tag: t, readonly: false }));
              if (filteredGlobal.length > 0) {
                items.push({ type: 'header', label: 'Vorgegebene Tags', scope: 'global', count: filteredGlobal.length });
              }
              filteredGlobal.forEach((t) => items.push({ type: 'tag', tag: t, readonly: !isSuperuser }));
            } else {
              if (ownInstitutionTags.length > 0) {
                items.push({ type: 'header', label: 'Meine Tags', scope: 'institution', count: ownInstitutionTags.length });
                ownInstitutionTags.forEach((t) => items.push({ type: 'tag', tag: t, readonly: false }));
              }
              if (othersInstitutionTags.length > 0) {
                items.push({ type: 'header', label: 'Tags der Institution', scope: 'institution', count: othersInstitutionTags.length });
                othersInstitutionTags.forEach((t) => items.push({ type: 'tag', tag: t, readonly: true }));
              }
              if (filteredGlobal.length > 0) {
                items.push({ type: 'header', label: 'Vorgegebene Tags', scope: 'global', count: filteredGlobal.length });
                filteredGlobal.forEach((t) => items.push({ type: 'tag', tag: t, readonly: true }));
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
                        onSave={(name) => renameMutation.mutateAsync({ id: tag.id, name })}
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
                            (archiviert)
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
                          {tag.usage_count} {tag.usage_count === 1 ? 'Frage' : 'Fragen'}
                        </Typography>
                      </Box>
                    )}

                    {renamingId !== tag.id && !item.readonly && (
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {!tag.is_archived && (tag.scope === 'global' ? isSuperuser : true) && (
                          <>
                            <Tooltip title="Umbenennen">
                              <IconButton size="small" onClick={() => setRenamingId(tag.id)}>
                                <Edit fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Archivieren">
                              <IconButton size="small" onClick={() => archiveMutation.mutate(tag.id)}>
                                <Archive fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                        {tag.is_archived && (tag.scope === 'global' ? isSuperuser : true) && (
                          <Tooltip title="Wiederherstellen">
                            <IconButton size="small" onClick={() => unarchiveMutation.mutate(tag.id)}>
                              <Unarchive fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {tag.is_archived && (tag.is_own || isAdmin) && tag.usage_count === 0 && (tag.scope === 'global' ? isSuperuser : true) && (
                          <Tooltip title="Löschen">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => {
                                if (window.confirm(`Tag "#${tag.name}" permanent löschen?`)) {
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
        onConfirm={(sourceIds, targetId) =>
          mergeMutation.mutateAsync({ sourceIds, targetId })
        }
        onClose={() => setMergeOpen(false)}
      />
    </Box>
  );
};

export default TagSettingsPage;
