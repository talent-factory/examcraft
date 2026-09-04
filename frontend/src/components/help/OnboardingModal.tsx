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
  /**
   * i18n key prefix of the welcome step; `.title` and `.description` are
   * looked up from it. Previously the four German/English strings were passed
   * in and picked apart here, which made the modal untranslatable beyond those
   * two languages (TF-670).
   */
  i18nKey: string;
  onStart: () => void;
  onLater: () => void;
}

const OnboardingModal: React.FC<OnboardingModalProps> = ({
  open,
  i18nKey,
  onStart,
  onLater,
}) => {
  const { t } = useTranslation();
  const title = t(`${i18nKey}.title`);
  const description = t(`${i18nKey}.description`);

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
