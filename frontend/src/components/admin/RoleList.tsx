/**
 * Role List Component
 * Displays list of all roles with features
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  IconButton,
  Button,
  CircularProgress,
  Alert,
  Grid,
  Tooltip
} from '@mui/material';
import {
  Edit as EditIcon,
  Add as AddIcon,
  Lock as LockIcon
} from '@mui/icons-material';
import { Role } from '../../types/rbac';
import RBACService from '../../services/RBACService';

interface RoleListProps {
  onEditRole: (role: Role) => void;
  onCreateRole: () => void;
}

const RoleList: React.FC<RoleListProps> = ({ onEditRole, onCreateRole }) => {
  const { t } = useTranslation();
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRoles();
  }, []);

  const loadRoles = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await RBACService.listRoles(true, false);
      setRoles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.roleList.failedLoad'));
    } finally {
      setLoading(false);
    }
  };

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
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          {t('admin.roleList.title')}
        </Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={onCreateRole}
        >
          {t('admin.roleList.btnCreate')}
        </Button>
      </Box>

      <Grid container spacing={3}>
        {roles.map((role) => (
          <Grid item xs={12} md={6} lg={4} key={role.id}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                '&:hover': {
                  boxShadow: 6
                }
              }}
            >
              <CardContent sx={{ flexGrow: 1 }}>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                  <Box>
                    <Typography variant="h6" component="h3" gutterBottom>
                      {role.display_name}
                      {role.is_system_role && (
                        <Tooltip title={t('admin.roleList.tooltipSystemRole')}>
                          <LockIcon
                            fontSize="small"
                            sx={{ ml: 1, verticalAlign: 'middle', color: 'text.secondary' }}
                          />
                        </Tooltip>
                      )}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {role.name}
                    </Typography>
                  </Box>
                  <Tooltip title={role.is_system_role ? t('admin.roleList.tooltipEditSystemRole') : t('admin.roleList.tooltipEditRole')}>
                    <IconButton
                      size="small"
                      onClick={() => onEditRole(role)}
                    >
                      <EditIcon />
                    </IconButton>
                  </Tooltip>
                </Box>

                {role.description && (
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {role.description}
                  </Typography>
                )}

                <Box mt={2}>
                  <Typography variant="subtitle2" gutterBottom>
                    {t('admin.roleList.featuresCount', { count: role.features.length })}
                  </Typography>
                  <Box display="flex" flexWrap="wrap" gap={0.5}>
                    {role.features.length === 0 ? (
                      <Typography variant="body2" color="text.secondary">
                        {t('admin.roleList.noFeatures')}
                      </Typography>
                    ) : (
                      role.features.slice(0, 5).map((feature) => (
                        <Chip
                          key={feature.id}
                          label={feature.display_name}
                          size="small"
                          sx={{
                            backgroundColor: getCategoryColor(feature.category || 'other'),
                            color: 'white',
                            fontSize: '0.7rem'
                          }}
                        />
                      ))
                    )}
                    {role.features.length > 5 && (
                      <Chip
                        label={t('admin.roleList.moreFeatures', { count: role.features.length - 5 })}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                </Box>

                <Box mt={2}>
                  <Typography variant="caption" color="text.secondary">
                    {role.is_active ? (
                      <Chip label={t('admin.roleList.active')} size="small" color="success" />
                    ) : (
                      <Chip label={t('admin.roleList.inactive')} size="small" color="default" />
                    )}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {roles.length === 0 && (
        <Box textAlign="center" py={8}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            {t('admin.roleList.emptyTitle')}
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            {t('admin.roleList.emptySubtitle')}
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={onCreateRole}
          >
            {t('admin.roleList.btnCreateFirst')}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default RoleList;
