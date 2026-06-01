import React, { useState } from 'react';
import { Alert, Collapse } from '@mui/material';
import { useTranslation } from 'react-i18next';

const DISMISS_KEY = 'examcraft_tf354_privacy_banner_dismissed';

// The privacy roll-out banner (TF-354) self-retires one week after roll-out,
// regardless of dismissal state, so it doesn't linger for new users forever.
const BANNER_END = new Date('2026-06-05T00:00:00Z');

/**
 * One-time, dismissable info banner announcing the document visibility change
 * (TF-354): all existing uploads are now private. Dismissal persists in
 * localStorage; the banner also auto-expires after BANNER_END.
 */
const DocumentPrivacyBanner: React.FC = () => {
  const { t } = useTranslation();
  const [open, setOpen] = useState<boolean>(() => {
    if (Date.now() >= BANNER_END.getTime()) {
      return false;
    }
    try {
      return localStorage.getItem(DISMISS_KEY) !== 'true';
    } catch {
      // localStorage unavailable (private mode / disabled) — still show it.
      return true;
    }
  });

  const dismiss = () => {
    setOpen(false);
    try {
      localStorage.setItem(DISMISS_KEY, 'true');
    } catch {
      // Ignore storage failures — worst case the banner reappears next visit.
    }
  };

  return (
    <Collapse in={open}>
      <Alert severity="info" onClose={dismiss} sx={{ mb: 2 }} data-testid="privacy-banner">
        {t('components.documentPrivacyBanner.message')}
      </Alert>
    </Collapse>
  );
};

export default DocumentPrivacyBanner;
