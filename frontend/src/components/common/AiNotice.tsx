import React from 'react';
import { Alert, Chip, Tooltip } from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { useTranslation } from 'react-i18next';

/**
 * EU AI Act Art. 50 labelling (TF-747). `kind` selects the wording under the
 * `aiAct.<kind>` i18n keys:
 * - `taskDraft`: AI-generated exam question drafts
 * - `gradingSuggestion`: AI-assisted grading proposals
 * - `chat`: conversational AI (help chat, document chat, prompt wizard)
 *
 * `chip` is the compact label for cards and dialogs (hint as tooltip);
 * `alert` shows label and hint as a visible info block.
 */
export type AiNoticeKind = 'taskDraft' | 'gradingSuggestion' | 'chat';

interface AiNoticeProps {
  kind: AiNoticeKind;
  variant?: 'chip' | 'alert';
  /** Applied to both variants. */
  sx?: React.ComponentProps<typeof Alert>['sx'];
}

export const AiNotice: React.FC<AiNoticeProps> = ({ kind, variant = 'alert', sx }) => {
  const { t } = useTranslation();
  const label = t(`aiAct.${kind}.label`);
  const hint = t(`aiAct.${kind}.hint`);

  if (variant === 'chip') {
    return (
      <Tooltip title={hint}>
        <Chip
          icon={<AutoAwesomeIcon />}
          label={label}
          size="small"
          variant="outlined"
          color="info"
          sx={sx}
          data-testid={`ai-notice-${kind}`}
        />
      </Tooltip>
    );
  }

  return (
    <Alert
      severity="info"
      // A static notice, not a live-region announcement (role="alert" would
      // also collide with real error/status alerts next to it).
      role="note"
      icon={<AutoAwesomeIcon fontSize="inherit" />}
      sx={sx}
      data-testid={`ai-notice-${kind}`}
    >
      <strong>{label}.</strong> {hint}
    </Alert>
  );
};

export default AiNotice;
