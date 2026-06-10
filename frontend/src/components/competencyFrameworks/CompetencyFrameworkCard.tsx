import React from 'react';
import { Card, CardContent, Box, Typography, Chip, Button, Tooltip } from '@mui/material';
import { useTranslation } from 'react-i18next';
import type { CompetencyFramework } from '../../types/competencyFramework';

interface Props {
  framework: CompetencyFramework;
  canManage: boolean;
  onEdit: (fw: CompetencyFramework) => void;
  onArchiveToggle: (fw: CompetencyFramework) => void;
}

const CompetencyFrameworkCard: React.FC<Props> = ({
  framework,
  canManage,
  onEdit,
  onArchiveToggle,
}) => {
  const { t } = useTranslation();

  return (
    <Card variant="outlined" sx={{ opacity: framework.is_archived ? 0.6 : 1 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="h6" sx={{ flex: 1 }}>
            {framework.name}
          </Typography>
          {framework.module_code && <Chip size="small" label={framework.module_code} />}
          <Chip
            size="small"
            variant="outlined"
            label={t(`competencyFrameworks.visibility.${framework.visibility}`)}
          />
          {framework.is_archived && (
            <Chip size="small" color="default" label={t('competencyFrameworks.archivedBadge')} />
          )}
        </Box>

        {framework.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {framework.description}
          </Typography>
        )}

        {framework.competencies.length > 0 && (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 2 }}>
            {framework.competencies.map((c) => {
              const lnLevels = (c.descriptors ?? [])
                .map((d) => d.ln_level)
                .filter((n): n is number => typeof n === 'number');
              const lnSuffix = lnLevels.length > 0 ? ` · LN ${Array.from(new Set(lnLevels)).sort().join(',')}` : '';
              return (
                <Tooltip key={c.id} title={c.title}>
                  <Chip size="small" label={`${c.code}${lnSuffix}`} />
                </Tooltip>
              );
            })}
          </Box>
        )}

        {canManage && (
          <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
            <Button size="small" onClick={() => onEdit(framework)}>
              {t('competencyFrameworks.edit')}
            </Button>
            <Button size="small" color="warning" onClick={() => onArchiveToggle(framework)}>
              {framework.is_archived
                ? t('competencyFrameworks.unarchive')
                : t('competencyFrameworks.archive')}
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default CompetencyFrameworkCard;
