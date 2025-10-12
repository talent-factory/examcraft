import React, { useState, useEffect } from 'react';
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
  const [usageLogs, setUsageLogs] = useState<PromptUsageLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadUsageLogs();
  }, [promptId]);

  const loadUsageLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await promptsApi.getUsageLogs(promptId, 100);
      setUsageLogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Analytics');
    } finally {
      setLoading(false);
    }
  };

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
        Usage Analytics
      </Typography>

      <Grid container spacing={3}>
        {/* Total Usages */}
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={2}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <TrendingUp sx={{ color: 'primary.main', mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  Verwendungen
                </Typography>
              </Box>
              <Typography variant="h4" component="div">
                {totalUsages}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Gesamt
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
                  Erfolgsrate
                </Typography>
              </Box>
              <Typography variant="h4" component="div">
                {successRate.toFixed(1)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {successfulUsages} / {totalUsages} erfolgreich
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
                  Ø Latenz
                </Typography>
              </Box>
              <Typography variant="h4" component="div">
                {avgLatency.toFixed(0)}
                <Typography variant="h6" component="span" sx={{ ml: 0.5 }}>
                  ms
                </Typography>
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Durchschnitt
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
                  Tokens Total
                </Typography>
              </Box>
              <Typography variant="h4" component="div">
                {totalTokens.toLocaleString()}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Gesamt verwendet
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Usage Table */}
      {usageLogs.length > 0 && (
        <Paper elevation={2} sx={{ mt: 3, p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Letzte Verwendungen
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
                    {new Date(log.timestamp).toLocaleString('de-DE')}
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
            Noch keine Verwendungen aufgezeichnet
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

