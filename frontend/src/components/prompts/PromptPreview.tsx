import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Chip,
  Skeleton,
  Alert,
  Box,
  Divider,
  Paper
} from '@mui/material';
import {
  Description,
  LocalOffer,
  CalendarToday,
  TrendingUp,
  Tag,
  Error
} from '@mui/icons-material';
import { promptsApi } from '../../api/promptsApi';
import type { Prompt, PromptPreviewProps } from '../../types/prompt';
import { formatPromptMetadata } from '../../types/prompt';

/**
 * PromptPreview Component
 * 
 * Displays a readonly preview of a prompt with metadata,
 * usage statistics, and version information.
 */
export const PromptPreview: React.FC<PromptPreviewProps> = ({
  promptId,
  showMetadata = true,
  showUsageStats = true,
  compact = false
}) => {
  // Fetch prompt data
  const {
    data: prompt,
    isLoading,
    error
  } = useQuery<Prompt>({
    queryKey: ['prompt', promptId],
    queryFn: () => promptsApi.getPrompt(promptId!),
    enabled: !!promptId
  });

  // No prompt selected
  if (!promptId) {
    return (
      <Card variant="outlined" sx={{ borderStyle: 'dashed' }}>
        <CardContent sx={{ py: 6, textAlign: 'center' }}>
          <Description sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.5 }} />
          <Typography color="text.secondary">
            Kein Prompt ausgewählt
          </Typography>
        </CardContent>
      </Card>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton variant="text" width="75%" height={32} />
          <Skeleton variant="text" width="50%" height={24} sx={{ mt: 1 }} />
        </CardHeader>
        <CardContent>
          <Skeleton variant="text" width="100%" />
          <Skeleton variant="text" width="100%" />
          <Skeleton variant="text" width="75%" />
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Alert severity="error" icon={<Error />}>
        Fehler beim Laden des Prompts: {(error as Error).message}
      </Alert>
    );
  }

  // No prompt found
  if (!prompt) {
    return (
      <Alert severity="warning" icon={<Error />}>
        Prompt nicht gefunden
      </Alert>
    );
  }

  const metadata = formatPromptMetadata(prompt);

  // Compact view
  if (compact) {
    return (
      <Card sx={{ borderLeft: 4, borderColor: 'primary.main' }}>
        <CardContent sx={{ pt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" fontWeight="medium">
              {prompt.name}
            </Typography>
            <Chip label={`v${prompt.version}`} size="small" variant="outlined" />
          </Box>
          {prompt.description && (
            <Typography variant="caption" color="text.secondary" sx={{
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden'
            }}>
              {prompt.description}
            </Typography>
          )}
        </CardContent>
      </Card>
    );
  }

  // Full view
  return (
    <Card>
      <CardHeader>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <Box sx={{ flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <Description />
              <Typography variant="h6">
                {prompt.name}
              </Typography>
            </Box>
            {prompt.description && (
              <Typography variant="body2" color="text.secondary">
                {prompt.description}
              </Typography>
            )}
          </Box>
          <Chip label={`v${prompt.version}`} color="secondary" size="small" sx={{ ml: 2 }} />
        </Box>
      </CardHeader>

      <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Metadata Section */}
        {showMetadata && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              <Chip
                icon={<LocalOffer sx={{ fontSize: 16 }} />}
                label={prompt.category}
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<Tag sx={{ fontSize: 16 }} />}
                label={prompt.use_case}
                size="small"
                variant="outlined"
              />
            </Box>

            {prompt.tags && prompt.tags.length > 0 && (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {prompt.tags.map((tag: string, index: number) => (
                  <Chip
                    key={index}
                    label={tag}
                    size="small"
                    color="secondary"
                    sx={{ fontSize: '0.75rem' }}
                  />
                ))}
              </Box>
            )}

            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.secondary' }}>
                <CalendarToday sx={{ fontSize: 16 }} />
                <Typography variant="body2">
                  {new Date(prompt.created_at).toLocaleDateString('de-DE')}
                </Typography>
              </Box>
              {showUsageStats && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.secondary' }}>
                  <TrendingUp sx={{ fontSize: 16 }} />
                  <Typography variant="body2">
                    {prompt.usage_count || 0} Verwendungen
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>
        )}

        <Divider />

        {/* Prompt Content */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Prompt-Inhalt:
          </Typography>
          <Paper
            variant="outlined"
            sx={{
              maxHeight: 200,
              overflow: 'auto',
              bgcolor: 'grey.50',
              p: 2
            }}
          >
            <Typography
              component="pre"
              variant="body2"
              sx={{
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                whiteSpace: 'pre-wrap',
                m: 0
              }}
            >
              {prompt.content}
            </Typography>
          </Paper>
        </Box>

        {/* Token Estimation */}
        {prompt.tokens_estimated && (
          <Typography variant="caption" color="text.secondary">
            Geschätzte Tokens: ~{prompt.tokens_estimated}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default PromptPreview;

