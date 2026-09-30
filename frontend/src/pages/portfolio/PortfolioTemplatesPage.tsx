/**
 * `/portfolio/templates` — template list (TF-987 scaffold).
 *
 * A sub-page of `/portfolio`, not an admin tab: `/admin` is behind
 * `RoleGuard` (admins only), while the template permissions are opt-in per
 * role. P2 (TF-988) adds the editor.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import { portfolioApi } from '../../api/portfolioApi';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';

export const portfolioTemplatesQueryKey = ['portfolioTemplates'] as const;

const PortfolioTemplatesPage: React.FC = () => {
  const { t } = useTranslation();
  const { hasPermission } = useAuth();
  const { data, isLoading, error } = useQuery({
    queryKey: portfolioTemplatesQueryKey,
    queryFn: () => portfolioApi.listTemplates(),
  });

  return (
    <Box sx={{ p: 3 }} data-testid="portfolio-templates-page">
      {hasPermission('portfolio_assessments:read') && (
        <Button component={RouterLink} to="/portfolio" size="small" sx={{ mb: 1 }}>
          {t('pages.portfolio.templates.back')}
        </Button>
      )}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1">
          {t('pages.portfolio.templates.title')}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {t('pages.portfolio.templates.subtitle')}
        </Typography>
      </Box>

      {isLoading && <CircularProgress />}

      {error != null && (
        <Alert severity="error">
          {translateError(error, t, 'errors.portfolio_template_list_failed')}
        </Alert>
      )}

      {data && data.length === 0 && (
        <Typography color="textSecondary">{t('pages.portfolio.templates.empty')}</Typography>
      )}

      {data && data.length > 0 && (
        <List dense>
          {data.map((template) => (
            <ListItem key={template.id} divider>
              <ListItemText
                primary={template.name}
                secondary={t('pages.portfolio.templates.version', { version: template.version })}
              />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
};

export default PortfolioTemplatesPage;
