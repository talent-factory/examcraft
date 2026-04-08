import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Button,
  Box,
} from '@mui/material';
import { useTranslation } from 'react-i18next';

interface OnboardingModalProps {
  open: boolean;
  titleDe: string;
  titleEn: string;
  descriptionDe: string;
  descriptionEn: string;
  onStart: () => void;
  onLater: () => void;
}

const OnboardingModal: React.FC<OnboardingModalProps> = ({
  open,
  titleDe,
  titleEn,
  descriptionDe,
  descriptionEn,
  onStart,
  onLater,
}) => {
  const { i18n, t } = useTranslation();
  const locale = i18n.language?.substring(0, 2) || 'de';
  const title = locale === 'en' ? titleEn : titleDe;
  const description = locale === 'en' ? descriptionEn : descriptionDe;

  return (
    <Dialog
      open={open}
      disableEscapeKeyDown
      PaperProps={{ sx: { borderRadius: 2, maxWidth: 480, width: '100%', mx: 2 } }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Typography variant="h5" component="span">
          {title}
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" color="text.secondary">
          {description}
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button variant="outlined" onClick={onLater} size="large">
          {t('help.onboarding.later', 'Später')}
        </Button>
        <Button variant="contained" onClick={onStart} size="large" autoFocus>
          {t('help.onboarding.startTour', 'Tour starten')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default OnboardingModal;
