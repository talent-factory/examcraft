/**
 * Context hint — a page-specific tip at the top of the help panel.
 *
 * Collapsed to a single line by default. It sits above the tab strip so it
 * stays visible whichever pane is open, which is exactly why it must not be
 * tall: reported from the field as "it almost gets in the way in the widget
 * and is fairly large" — the full alert with two buttons ate roughly a
 * quarter of the panel before either pane got a pixel.
 *
 * Collapsed still shows the beginning of the tip, so it stays discoverable
 * rather than reduced to an anonymous bar the user has to gamble on.
 */
import React, { useState } from 'react';
import { Box, Typography, Button, Collapse } from '@mui/material';
import { LightbulbOutlined, ExpandMore } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService, ContextHint } from '../../services/HelpService';

interface HelpContextHintProps {
  hint: ContextHint;
  onDismiss: () => void;
  onDismissPermanently: () => void;
}

const HelpContextHint: React.FC<HelpContextHintProps> = ({
  hint,
  onDismiss,
  onDismissPermanently,
}) => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [expanded, setExpanded] = useState(false);

  if (!hint.i18n_key) return null;

  // Resolved here rather than delivered by the API: that way switching the
  // language switches the hint with the rest of the UI, instead of leaving it
  // in whatever language it happened to be fetched in (TF-625/TF-670).
  // The fallback only matters for `help.hints.unknown` — the migration
  // backfill's COALESCE default for a row whose route_pattern it didn't
  // recognize — which has no translation.json entry; without it the raw
  // key would render literally instead of failing soft.
  const hintText = t(hint.i18n_key, 'Tipp verfügbar');

  const handleDismissPermanently = async () => {
    if (accessToken && hint.hint_id) {
      try {
        await helpService.dismissHint(accessToken, hint.hint_id);
      } catch (err) {
        // Left displayed rather than dismissed client-side-only: a dismiss
        // that never reached the server would otherwise reappear at the next
        // fetch anyway, so silently hiding it here would just be a confusing
        // extra state with no persistence to back it up.
        console.warn('Failed to permanently dismiss hint:', err);
        return;
      }
    }
    onDismissPermanently();
  };

  return (
    <Box
      data-testid="help-context-hint"
      sx={{
        px: 1.5,
        py: 0.5,
        bgcolor: 'info.lighter',
        backgroundImage: (theme) =>
          `linear-gradient(${theme.palette.info.main}14, ${theme.palette.info.main}14)`,
        borderBottom: 1,
        borderColor: 'divider',
        flexShrink: 0,
      }}
    >
      <Box
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        data-testid="help-context-hint-toggle"
        onClick={() => setExpanded((prev) => !prev)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setExpanded((prev) => !prev);
          }
        }}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          cursor: 'pointer',
          minWidth: 0,
        }}
      >
        <LightbulbOutlined fontSize="small" color="info" sx={{ flexShrink: 0 }} />
        <Typography
          variant="caption"
          color="text.secondary"
          sx={
            expanded
              ? { flex: 1, minWidth: 0 }
              : {
                  // One line, cut off — the tip stays readable enough to
                  // decide whether to open it.
                  flex: 1,
                  minWidth: 0,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }
          }
        >
          {hintText}
        </Typography>
        {/* Purely decorative: the row above (role="button") is the one
            focusable, labeled control. A nested IconButton here would be an
            interactive element inside a button — invalid ARIA, a second tab
            stop that does nothing on its own, and a static aria-label that
            couldn't reflect `expanded` the way the row's aria-expanded does. */}
        <Box
          aria-hidden="true"
          sx={{
            flexShrink: 0,
            display: 'inline-flex',
            p: 0.25,
            transform: expanded ? 'rotate(180deg)' : 'none',
            transition: 'transform 150ms',
          }}
        >
          <ExpandMore fontSize="small" />
        </Box>
      </Box>

      <Collapse in={expanded} unmountOnExit>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', pb: 1, pt: 0.5, pl: 3.5 }}>
          <Button size="small" variant="outlined" onClick={onDismiss}>
            {t('help.context.understood', 'Verstanden')}
          </Button>
          <Button size="small" color="inherit" onClick={handleDismissPermanently}>
            {t('help.context.dontShowAgain', 'Nicht mehr anzeigen')}
          </Button>
        </Box>
      </Collapse>
    </Box>
  );
};

export default HelpContextHint;
