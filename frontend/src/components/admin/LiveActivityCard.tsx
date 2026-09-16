import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, Typography } from '@mui/material';
import { ActivityBucketId, ActivityBucketValue } from '../../types/liveActivity';

interface LiveActivityCardProps {
  bucketId: ActivityBucketId;
  bucket: ActivityBucketValue | undefined;
}

/**
 * One Live-Activity tile (TF-838): renders a bucket's active-person count
 * straight from the `{value, exact}` response contract — `exact === true`
 * shows the number, otherwise "< N" (the clamped Kleinstzahl-Schwelle, not a
 * raw count). No further small-number logic here; that threshold is clamped
 * server-side (TF-826/ADR-0006). A bucket absent from the snapshot means its
 * fetch failed server-side (see `LiveActivitySnapshot.buckets`'s comment in
 * `types/liveActivity.ts`) — shown as unavailable, never silently as zero.
 */
const LiveActivityCard: React.FC<LiveActivityCardProps> = ({ bucketId, bucket }) => {
  const { t } = useTranslation();

  return (
    <Card data-testid={`live-activity-card-${bucketId}`} variant="outlined">
      <CardContent>
        <Typography variant="body2" color="text.secondary">
          {t(`pages.admin.liveActivity.bucket.${bucketId}`)}
        </Typography>
        {bucket ? (
          <Typography variant="h4" data-testid={`live-activity-card-value-${bucketId}`}>
            {bucket.exact ? bucket.value : t('pages.admin.liveActivity.lessThan', { value: bucket.value })}
          </Typography>
        ) : (
          <Typography
            variant="body2"
            color="text.secondary"
            data-testid={`live-activity-card-unavailable-${bucketId}`}
          >
            {t('pages.admin.liveActivity.unavailable')}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default LiveActivityCard;
