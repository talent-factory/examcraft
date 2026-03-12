import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  TextField,
  Card,
  CardContent,
  CardActions,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent
} from '@mui/material';
import { Add, Search, Edit, Delete, History } from '@mui/icons-material';
import { promptsApi, Prompt } from '../../api/promptsApi';

interface PromptLibraryProps {
  onEditPrompt?: (promptId: string) => void;
  onCreateNew?: () => void;
  onShowVersions?: (promptName: string) => void;
}

export const PromptLibrary: React.FC<PromptLibraryProps> = ({
  onEditPrompt,
  onCreateNew,
  onShowVersions
}) => {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all'); // all, active, inactive

  const loadPrompts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Build filters
      const filters: any = {};
      if (categoryFilter !== 'all') {
        filters.category = categoryFilter;
      }
      // Don't filter by is_active - we want to see all prompts
      // Filter will be applied in UI

      const data = await promptsApi.listPrompts(filters);

      // Apply status filter in frontend
      let filteredData = data;
      if (statusFilter === 'active') {
        filteredData = data.filter(p => p.is_active);
      } else if (statusFilter === 'inactive') {
        filteredData = data.filter(p => !p.is_active);
      }

      setPrompts(filteredData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Prompts');
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, statusFilter]);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const handleDelete = async (id: string) => {
    if (!window.confirm('Möchten Sie diesen Prompt wirklich löschen?')) {
      return;
    }

    try {
      await promptsApi.deletePrompt(id);
      await loadPrompts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Löschen');
    }
  };

  const handleToggleActive = async (id: string, currentStatus: boolean) => {
    const action = currentStatus ? 'deaktivieren' : 'aktivieren';
    if (!window.confirm(`Möchten Sie diesen Prompt wirklich ${action}?`)) {
      return;
    }

    try {
      await promptsApi.toggleActive(id, !currentStatus);
      await loadPrompts();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Fehler beim ${action}`);
    }
  };

  const filteredPrompts = prompts.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'system_prompt': return 'primary';
      case 'user_prompt': return 'secondary';
      case 'few_shot_example': return 'success';
      case 'template': return 'warning';
      default: return 'default';
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'system_prompt': return 'System Prompt';
      case 'user_prompt': return 'User Prompt';
      case 'few_shot_example': return 'Few-Shot Example';
      case 'template': return 'Template';
      default: return category;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Prompt Knowledge Base
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Verwalte System- und User-Prompts für KI-Agents
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={onCreateNew}
          size="large"
        >
          Neuer Prompt
        </Button>
      </Box>

      {/* Search and Filter */}
      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              placeholder="Prompts durchsuchen..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
              }}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Kategorie</InputLabel>
              <Select
                value={categoryFilter}
                label="Kategorie"
                onChange={(e: SelectChangeEvent) => setCategoryFilter(e.target.value)}
              >
                <MenuItem value="all">Alle Kategorien</MenuItem>
                <MenuItem value="system_prompt">System Prompts</MenuItem>
                <MenuItem value="user_prompt">User Prompts</MenuItem>
                <MenuItem value="few_shot_example">Few-Shot Examples</MenuItem>
                <MenuItem value="template">Templates</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e: SelectChangeEvent) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="all">Alle</MenuItem>
                <MenuItem value="active">Aktiv</MenuItem>
                <MenuItem value="inactive">Inaktiv (Review)</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Loading State */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Error State */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Prompts Grid */}
      {!loading && !error && (
        <>
          {filteredPrompts.length === 0 ? (
            <Paper elevation={1} sx={{ p: 8, textAlign: 'center' }}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Keine Prompts gefunden
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                {searchQuery ? 'Versuchen Sie eine andere Suche' : 'Erstellen Sie Ihren ersten Prompt'}
              </Typography>
              {!searchQuery && (
                <Button variant="contained" startIcon={<Add />} onClick={onCreateNew}>
                  Ersten Prompt erstellen
                </Button>
              )}
            </Paper>
          ) : (
            <Grid container spacing={3}>
              {filteredPrompts.map((prompt) => (
                <Grid item xs={12} md={6} lg={4} key={prompt.id}>
                  <Card
                    elevation={2}
                    sx={{
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      transition: 'transform 0.2s, box-shadow 0.2s',
                      '&:hover': {
                        transform: 'translateY(-4px)',
                        boxShadow: 4
                      }
                    }}
                  >
                    <CardContent sx={{ flexGrow: 1 }}>
                      {/* Header */}
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                        <Typography variant="h6" component="h3" sx={{ fontWeight: 600 }}>
                          {prompt.name}
                        </Typography>
                        <Chip
                          label={`v${prompt.version}`}
                          size="small"
                          color={prompt.is_active ? 'success' : 'default'}
                        />
                      </Box>

                      {/* Description */}
                      {prompt.description && (
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                          {prompt.description}
                        </Typography>
                      )}

                      {/* Category and Use Case */}
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                        <Chip
                          label={getCategoryLabel(prompt.category)}
                          size="small"
                          color={getCategoryColor(prompt.category)}
                        />
                        {prompt.use_case && (
                          <Chip
                            label={prompt.use_case}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {!prompt.is_active && (
                          <Chip
                            label="Inaktiv (Review)"
                            size="small"
                            color="warning"
                            sx={{ fontWeight: 600 }}
                          />
                        )}
                      </Box>

                      {/* Tags */}
                      {prompt.tags.length > 0 && (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                          {prompt.tags.slice(0, 3).map(tag => (
                            <Chip
                              key={tag}
                              label={`#${tag}`}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.7rem' }}
                            />
                          ))}
                          {prompt.tags.length > 3 && (
                            <Chip
                              label={`+${prompt.tags.length - 3}`}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.7rem' }}
                            />
                          )}
                        </Box>
                      )}

                      {/* Usage Stats */}
                      <Typography variant="caption" color="text.secondary">
                        Verwendet: {prompt.usage_count || 0} mal
                      </Typography>
                    </CardContent>

                    <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
                      <Box>
                        <Button
                          size="small"
                          startIcon={<Edit />}
                          onClick={() => onEditPrompt?.(prompt.id)}
                        >
                          Bearbeiten
                        </Button>
                        <Button
                          size="small"
                          color={prompt.is_active ? 'warning' : 'success'}
                          onClick={() => handleToggleActive(prompt.id, prompt.is_active)}
                        >
                          {prompt.is_active ? 'Deaktivieren' : 'Aktivieren'}
                        </Button>
                      </Box>
                      <Box>
                        <Button
                          size="small"
                          startIcon={<History />}
                          onClick={() => onShowVersions?.(prompt.name)}
                        >
                          Versionen
                        </Button>
                        <Button
                          size="small"
                          color="error"
                          startIcon={<Delete />}
                          onClick={() => handleDelete(prompt.id)}
                        >
                          Löschen
                        </Button>
                      </Box>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </>
      )}
    </Container>
  );
};
