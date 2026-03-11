/**
 * Subscription Tier Overview Component
 * Displays all subscription tiers with quotas and pricing
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper
} from '@mui/material';
import {
  Cancel as CancelIcon,
  AllInclusive as InfinityIcon
} from '@mui/icons-material';
import { SubscriptionTier, TierQuota, TIER_COLORS, RESOURCE_TYPE_LABELS } from '../../types/rbac';
import RBACService from '../../services/RBACService';

const SubscriptionTierOverview: React.FC = () => {
  const [tiers, setTiers] = useState<SubscriptionTier[]>([]);
  const [quotas, setQuotas] = useState<Record<string, TierQuota[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load tiers
      const tiersData = await RBACService.listSubscriptionTiers();
      setTiers(tiersData);

      // Load quotas for each tier
      const quotasData: Record<string, TierQuota[]> = {};
      await Promise.all(
        tiersData.map(async (tier) => {
          const tierQuotas = await RBACService.getTierQuotas(tier.id);
          quotasData[tier.id] = tierQuotas;
        })
      );
      setQuotas(quotasData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load subscription tiers');
    } finally {
      setLoading(false);
    }
  };

  const formatQuotaValue = (value: number): string => {
    if (value === -1) return 'Unlimited';
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return value.toString();
  };

  const formatPrice = (price: number): string => {
    return new Intl.NumberFormat('de-CH', {
      style: 'currency',
      currency: 'CHF'
    }).format(price);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h5" component="h2" gutterBottom>
        Subscription Tiers
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Übersicht über alle verfügbaren Subscription-Stufen mit Preisen und Ressourcen-Limits.
      </Typography>

      <Grid container spacing={3} mb={4}>
        {tiers.map((tier) => (
          <Grid item xs={12} sm={6} md={3} key={tier.id}>
            <Card
              sx={{
                height: '100%',
                borderTop: `4px solid ${TIER_COLORS[tier.id] || '#9E9E9E'}`,
                '&:hover': {
                  boxShadow: 6
                }
              }}
            >
              <CardContent>
                <Typography variant="h6" component="h3" gutterBottom>
                  {tier.display_name}
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  {tier.description}
                </Typography>

                <Box mb={2}>
                  <Typography variant="h4" component="div" color="primary">
                    {formatPrice(tier.price_monthly)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    pro Monat
                  </Typography>
                </Box>

                {tier.price_yearly > 0 && (
                  <Box mb={2}>
                    <Typography variant="body2" color="text.secondary">
                      {formatPrice(tier.price_yearly)} / Jahr
                    </Typography>
                    <Typography variant="caption" color="success.main">
                      Spare {formatPrice(tier.price_monthly * 12 - tier.price_yearly)}
                    </Typography>
                  </Box>
                )}

                <Box mt={2}>
                  {tier.is_active ? (
                    <Chip label="Verfügbar" size="small" color="success" />
                  ) : (
                    <Chip label="Nicht verfügbar" size="small" color="default" />
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Typography variant="h6" component="h3" gutterBottom>
        Ressourcen-Limits pro Tier
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Ressource</TableCell>
              {tiers.map((tier) => (
                <TableCell key={tier.id} align="center">
                  <Box
                    sx={{
                      fontWeight: 'bold',
                      color: TIER_COLORS[tier.id] || '#9E9E9E'
                    }}
                  >
                    {tier.display_name}
                  </Box>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(RESOURCE_TYPE_LABELS).map(([resourceType, label]) => (
              <TableRow key={resourceType}>
                <TableCell component="th" scope="row">
                  {label}
                </TableCell>
                {tiers.map((tier) => {
                  const quota = quotas[tier.id]?.find(q => q.resource_type === resourceType);
                  const value = quota?.quota_limit ?? 0;

                  return (
                    <TableCell key={tier.id} align="center">
                      {value === -1 ? (
                        <Box display="flex" alignItems="center" justifyContent="center">
                          <InfinityIcon sx={{ mr: 0.5 }} />
                          <Typography variant="body2">Unlimited</Typography>
                        </Box>
                      ) : value > 0 ? (
                        <Typography variant="body2" fontWeight="medium">
                          {formatQuotaValue(value)}
                        </Typography>
                      ) : (
                        <CancelIcon color="disabled" />
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Box mt={4}>
        <Alert severity="info">
          <Typography variant="body2">
            <strong>Hinweis:</strong> Ressourcen-Limits werden monatlich zurückgesetzt.
            Unlimited bedeutet keine Beschränkung.
          </Typography>
        </Alert>
      </Box>
    </Box>
  );
};

export default SubscriptionTierOverview;
