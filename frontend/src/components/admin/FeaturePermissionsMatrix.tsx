/**
 * Feature Permissions Matrix Component
 * Matrix view showing which roles have access to which features
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Tooltip
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';
import { Role, Feature, FEATURE_CATEGORIES } from '../../types/rbac';
import RBACService from '../../services/RBACService';

const FeaturePermissionsMatrix: React.FC = () => {
  const { t } = useTranslation();
  const [roles, setRoles] = useState<Role[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [rolesData, featuresData] = await Promise.all([
        RBACService.listRoles(true, false),
        RBACService.listFeatures()
      ]);

      setRoles(rolesData);
      setFeatures(featuresData);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.featureMatrix.failedLoad'));
    } finally {
      setLoading(false);
    }
  };

  const hasFeature = (role: Role, featureId: string): boolean => {
    return role.features.some(f => f.id === featureId);
  };

  const groupedFeatures = features.reduce((acc, feature) => {
    const category = feature.category || 'other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(feature);
    return acc;
  }, {} as Record<string, Feature[]>);

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      generation: '#4CAF50',
      management: '#2196F3',
      administration: '#FF9800',
      integration: '#9C27B0',
      other: '#9E9E9E'
    };
    return colors[category] || colors.other;
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
        {t('admin.featureMatrix.title')}
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        {t('admin.featureMatrix.subtitle')}
      </Typography>

      <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  minWidth: 250,
                  fontWeight: 'bold',
                  backgroundColor: 'background.paper'
                }}
              >
                {t('admin.featureMatrix.colFeature')}
              </TableCell>
              {roles.map((role) => (
                <TableCell
                  key={role.id}
                  align="center"
                  sx={{
                    minWidth: 120,
                    fontWeight: 'bold',
                    backgroundColor: 'background.paper'
                  }}
                >
                  <Tooltip title={role.description || ''}>
                    <Box>
                      {role.display_name}
                      {role.is_system_role && (
                        <Chip
                          label={t('admin.featureMatrix.systemBadge')}
                          size="small"
                          sx={{ ml: 0.5, fontSize: '0.6rem' }}
                        />
                      )}
                    </Box>
                  </Tooltip>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(groupedFeatures).map(([category, categoryFeatures]) => (
              <React.Fragment key={category}>
                <TableRow>
                  <TableCell
                    colSpan={roles.length + 1}
                    sx={{
                      backgroundColor: getCategoryColor(category),
                      color: 'white',
                      fontWeight: 'bold',
                      py: 1
                    }}
                  >
                    {FEATURE_CATEGORIES[category as keyof typeof FEATURE_CATEGORIES] || category}
                  </TableCell>
                </TableRow>
                {categoryFeatures.map((feature) => (
                  <TableRow
                    key={feature.id}
                    hover
                    sx={{
                      '&:hover': {
                        backgroundColor: 'action.hover'
                      }
                    }}
                  >
                    <TableCell>
                      <Box>
                        <Typography variant="body2" fontWeight="medium">
                          {feature.display_name}
                        </Typography>
                        {feature.description && (
                          <Typography variant="caption" color="text.secondary">
                            {feature.description}
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                    {roles.map((role) => (
                      <TableCell key={role.id} align="center">
                        {hasFeature(role, feature.id) ? (
                          <CheckIcon color="success" />
                        ) : (
                          <CancelIcon color="disabled" />
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Box mt={2}>
        <Alert severity="info">
          <Typography variant="body2">
            <strong>{t('admin.featureMatrix.legend')}</strong> <CheckIcon fontSize="small" sx={{ verticalAlign: 'middle', color: 'success.main' }} /> = {t('admin.featureMatrix.legendAccess')}{' '}
            <CancelIcon fontSize="small" sx={{ verticalAlign: 'middle', color: 'text.disabled' }} /> = {t('admin.featureMatrix.legendNoAccess')}
          </Typography>
        </Alert>
      </Box>
    </Box>
  );
};

export default FeaturePermissionsMatrix;
