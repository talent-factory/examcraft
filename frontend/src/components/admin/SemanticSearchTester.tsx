import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  CircularProgress,
  Alert,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent
} from '@mui/material';
import { Search, TrendingUp } from '@mui/icons-material';
import { promptsApi, PromptSearchRequest, PromptSearchResult } from '../../api/promptsApi';

export const SemanticSearchTester: React.FC = () => {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<string>('');
  const [useCase, setUseCase] = useState('');
  const [limit, setLimit] = useState(5);
  const [scoreThreshold, setScoreThreshold] = useState(0.7);
  const [results, setResults] = useState<PromptSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      setError(t('admin.semanticSearch.errorEmpty'));
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const searchRequest: PromptSearchRequest = {
        query: query.trim(),
        limit,
        score_threshold: scoreThreshold
      };

      if (category) {
        searchRequest.category = category;
      }

      if (useCase) {
        searchRequest.use_case = useCase;
      }

      const data = await promptsApi.searchPrompts(searchRequest);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.semanticSearch.failedSearch'));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const getSimilarityColor = (score: number) => {
    if (score >= 0.9) return 'success';
    if (score >= 0.7) return 'primary';
    if (score >= 0.5) return 'warning';
    return 'default';
  };

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h5" gutterBottom>
        {t('admin.semanticSearch.title')}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t('admin.semanticSearch.subtitle')}
      </Typography>

      {/* Search Form */}
      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        <Grid container spacing={3}>
          {/* Query Input */}
          <Grid item xs={12}>
            <TextField
              fullWidth
              label={t('admin.semanticSearch.queryLabel')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={t('admin.semanticSearch.queryPlaceholder')}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
              }}
            />
          </Grid>

          {/* Filters */}
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>{t('admin.semanticSearch.categoryLabel')}</InputLabel>
              <Select
                value={category}
                label={t('admin.semanticSearch.categoryLabel')}
                onChange={(e: SelectChangeEvent) => setCategory(e.target.value)}
              >
                <MenuItem value="">{t('admin.semanticSearch.categoryAll')}</MenuItem>
                <MenuItem value="system_prompt">{t('admin.semanticSearch.categorySystem')}</MenuItem>
                <MenuItem value="user_prompt">{t('admin.semanticSearch.categoryUser')}</MenuItem>
                <MenuItem value="few_shot_example">{t('admin.semanticSearch.categoryFewShot')}</MenuItem>
                <MenuItem value="template">{t('admin.semanticSearch.categoryTemplate')}</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label={t('admin.semanticSearch.useCaseLabel')}
              value={useCase}
              onChange={(e) => setUseCase(e.target.value)}
              placeholder={t('admin.semanticSearch.useCasePlaceholder')}
            />
          </Grid>

          {/* Advanced Settings */}
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              {t('admin.semanticSearch.resultCount', { count: limit })}
            </Typography>
            <Slider
              value={limit}
              onChange={(_, value) => setLimit(value as number)}
              min={1}
              max={20}
              marks
              valueLabelDisplay="auto"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              {t('admin.semanticSearch.similarityThreshold', { value: scoreThreshold.toFixed(2) })}
            </Typography>
            <Slider
              value={scoreThreshold}
              onChange={(_, value) => setScoreThreshold(value as number)}
              min={0}
              max={1}
              step={0.05}
              marks={[
                { value: 0, label: '0' },
                { value: 0.5, label: '0.5' },
                { value: 1, label: '1' }
              ]}
              valueLabelDisplay="auto"
            />
          </Grid>

          {/* Search Button */}
          <Grid item xs={12}>
            <Button
              variant="contained"
              size="large"
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              startIcon={loading ? <CircularProgress size={20} /> : <Search />}
              fullWidth
            >
              {loading ? t('admin.semanticSearch.btnSearching') : t('admin.semanticSearch.btnSearch')}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Error Message */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Results */}
      {results.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom>
            {t('admin.semanticSearch.resultsTitle', { count: results.length })}
          </Typography>

          <Grid container spacing={2}>
            {results.map((result, index) => (
              <Grid item xs={12} key={result.prompt_id}>
                <Card
                  elevation={2}
                  sx={{
                    transition: 'transform 0.2s',
                    '&:hover': { transform: 'translateY(-2px)' }
                  }}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="h6" component="h3">
                          {index + 1}. {result.name}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                          <Chip label={result.category} size="small" color="primary" />
                          {result.use_case && (
                            <Chip label={result.use_case} size="small" variant="outlined" />
                          )}
                          <Chip label={`v${result.version}`} size="small" />
                        </Box>
                      </Box>
                      {result.similarity_score !== undefined && (
                        <Box sx={{ display: 'flex', alignItems: 'center', ml: 2 }}>
                          <TrendingUp sx={{ mr: 0.5, fontSize: 16 }} />
                          <Chip
                            label={`${(result.similarity_score * 100).toFixed(1)}%`}
                            color={getSimilarityColor(result.similarity_score)}
                            size="small"
                          />
                        </Box>
                      )}
                    </Box>

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {result.content_preview}
                    </Typography>

                    {result.tags.length > 0 && (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {result.tags.map(tag => (
                          <Chip
                            key={tag}
                            label={`#${tag}`}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                          />
                        ))}
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* No Results */}
      {!loading && results.length === 0 && query && (
        <Paper elevation={1} sx={{ p: 8, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            {t('admin.semanticSearch.emptyTitle')}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t('admin.semanticSearch.emptySubtitle')}
          </Typography>
        </Paper>
      )}
    </Box>
  );
};
