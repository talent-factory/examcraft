import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../../utils/dateLocale';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert
} from '@mui/material';
import { TrendingUp, CheckCircle, AccessTime, Token } from '@mui/icons-material';
import { promptsApi, PromptUsageLog } from '../../api/promptsApi';

interface PromptUsageChartProps {
  promptId: string;
}

export const PromptUsageChart: React.FC<PromptUsageChartProps> = ({ promptId }) => {
  const { t, i18n } = useTranslation();
  const [usageLogs, setUsageLogs] = useState<PromptUsageLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadUsageLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await promptsApi.getUsageLogs(promptId, 100);
      setUsageLogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.promptUsageChart.failedLoad'));
    } finally {
      setLoading(false);
    }
  }, [promptId]);

  useEffect(() => {
    loadUsageLogs();
  }, [loadUsageLogs]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {error}
      </Alert>
    );
  }

  // Calculate metrics
  const totalUsages = usageLogs.length;
  const successfulUsages = usageLogs.filter(log => log.success).length;
  const successRate = totalUsages > 0 ? (successfulUsages / totalUsages) * 100 : 0;

  const logsWithLatency = usageLogs.filter(log => log.latency_ms !== undefined && log.latency_ms !== null);
  const avgLatency = logsWithLatency.length > 0
    ? logsWithLatency.reduce((sum, log) => sum + (log.latency_ms || 0), 0) / logsWithLatency.length
    : 0;

  const totalTokens = usageLogs.reduce((sum, log) => sum + (log.tokens_used || 0), 0);

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        {t('admin.promptUsageChart.title')}
      </Typography>

      <Grid container spacing={3}>
        {/* Total Usages */}
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={2}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <TrendingUp sx={{ color: 'primary.main', mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  {t('admin.promptUsageChart.metricUsages')}
                </Typography>
              </Box>
              <Typography variant="h4" component="div">
                {totalUsages}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t('admin.promptUsageChart.metricTotal')}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Success Rate */}
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={2}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <CheckCircle
                  sx={{
                    color: successRate > 95 ? 'success.main' : successRate > 80 ? 'warning.main' : 'error.main',
                    mr: 1
                  }}
                />
                <Typography variant="subtitle2" color="text.secondary">
                  {t('admin.promptUsageChart.metricSuccessRate')}
                </Typography>
              </Box>
              <Typography variant="h4" component="div">
                {successRate.toFixed(1)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t('admin.promptUsageChart.metricSuccessOf', { success: successfulUsages, total: totalUsages })}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Average Latency */}
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={2}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <AccessTime sx={{ color: 'info.main', mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  {t('admin.promptUsageChart.metricLatency')}
                </Typography>
              </Box>
              <Typography variant="h4" component="div">
                {avgLatency.toFixed(0)}
                <Typography variant="h6" component="span" sx={{ ml: 0.5 }}>
                  ms
                </Typography>
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t('admin.promptUsageChart.metricAvg')}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Total Tokens */}
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={2}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Token sx={{ color: 'secondary.main', mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  {t('admin.promptUsageChart.metricTokens')}
                </Typography>
              </Box>
              <Typography variant="h4" component="div">
                {totalTokens.toLocaleString()}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t('admin.promptUsageChart.metricTokensTotal')}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Usage Table */}
      {usageLogs.length > 0 && (
        <Paper elevation={2} sx={{ mt: 3, p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            {t('admin.promptUsageChart.recentUsages')}
          </Typography>
          <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
            {usageLogs.slice(0, 10).map((log, index) => (
              <Box
                key={log.id}
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  py: 1,
                  px: 2,
                  borderBottom: index < 9 ? '1px solid' : 'none',
                  borderColor: 'divider',
                  '&:hover': { bgcolor: 'action.hover' }
                }}
              >
                <Box>
                  <Typography variant="body2">
                    {log.use_case}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(log.timestamp).toLocaleString(getDateLocale(i18n.language))}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                  {log.tokens_used && (
                    <Typography variant="caption" color="text.secondary">
                      {log.tokens_used} tokens
                    </Typography>
                  )}
                  {log.latency_ms && (
                    <Typography variant="caption" color="text.secondary">
                      {log.latency_ms}ms
                    </Typography>
                  )}
                  <CheckCircle
                    sx={{
                      fontSize: 16,
                      color: log.success ? 'success.main' : 'error.main'
                    }}
                  />
                </Box>
              </Box>
            ))}
          </Box>
        </Paper>
      )}

      {usageLogs.length === 0 && (
        <Paper elevation={1} sx={{ p: 4, textAlign: 'center', mt: 3 }}>
          <Typography variant="body1" color="text.secondary">
            {t('admin.promptUsageChart.empty')}
          </Typography>
        </Paper>
      )}
    </Box>
  );
};
