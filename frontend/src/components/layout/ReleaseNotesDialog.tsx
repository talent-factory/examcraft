/**
 * "What's new" dialog (TF-802).
 *
 * Replaces the sidebar version link's previous behaviour of opening the
 * GitHub releases page in a new tab. Content comes from
 * `src/data/releaseNotes.ts` (structure) + the `releaseNotes` i18n
 * namespace in each locale's translation.json (translated strings) — see
 * that file's top comment for why this is kept separate from
 * `core/CHANGELOG.md`.
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  Button,
  IconButton,
  Box,
  Typography,
  Collapse,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CampaignIcon from '@mui/icons-material/Campaign';
import { useLanguageChange } from '../../hooks/useLanguageChange';
import {
  RELEASE_NOTES,
  RELEASE_NOTE_GROUP_EMOJI,
  ReleaseNoteEntry,
  resolveScreenshotSrc,
} from '../../data/releaseNotes';

interface ReleaseNotesDialogProps {
  open: boolean;
  onClose: () => void;
}

const RELEASES_URL = 'https://github.com/talent-factory/examcraft/releases';

const SUPPORTED_LANGUAGES = ['de', 'en', 'fr', 'it'] as const;

const DATE_LOCALES: Record<string, string> = {
  de: 'de-CH',
  en: 'en-US',
  fr: 'fr-CH',
  it: 'it-CH',
};

// Exported so its locale/fallback branches can be unit-tested directly —
// review fix: the component-level test suite's global react-i18next mock
// pins i18n.language to 'de', so en-US/fr-CH/it-CH and the `?? 'de-CH'`
// fallback were previously never exercised by any test.
export const formatReleaseDate = (isoDate: string, lang: string): string => {
  const locale = DATE_LOCALES[lang] ?? 'de-CH';
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString(locale, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

export const ReleaseNotesDialog: React.FC<ReleaseNotesDialogProps> = ({ open, onClose }) => {
  const { t, i18n } = useTranslation();
  const { changeLanguage } = useLanguageChange();
  const currentLang = i18n.language?.substring(0, 2) || 'de';
  // Newest release starts expanded; only one release open at a time keeps
  // the dialog scannable.
  const [expandedVersion, setExpandedVersion] = useState<string | null>(
    RELEASE_NOTES[0]?.version ?? null
  );

  const toggleRelease = (version: string) => {
    setExpandedVersion((current) => (current === version ? null : version));
  };

  // Review fix: this badge used to always read RELEASE_NOTES[0].version,
  // independent of the Sidebar footer's own `process.env.REACT_APP_VERSION`
  // — the two could (and already did in local dev) show different numbers.
  // Prefer the actual running build; fall back to the manifest only when the
  // env var isn't set at all (e.g. running outside the usual build/deploy
  // path).
  const currentVersion = process.env.REACT_APP_VERSION || RELEASE_NOTES[0]?.version;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <Box
        sx={{
          background: 'linear-gradient(to right, #2563eb, #9333ea)',
          color: '#fff',
          px: 3,
          py: 2.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <CampaignIcon sx={{ mt: '2px' }} />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.25 }}>
                {t('releaseNotes.dialog.title')}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                <Typography variant="caption" sx={{ opacity: 0.85 }}>
                  {t('releaseNotes.dialog.currentVersionLabel')}
                </Typography>
                {currentVersion && (
                  <Box
                    component="span"
                    data-testid="release-notes-current-version-badge"
                    sx={{
                      fontSize: 12,
                      fontWeight: 700,
                      bgcolor: 'rgba(255,255,255,0.2)',
                      px: 1,
                      py: 0.25,
                      borderRadius: 9999,
                    }}
                  >
                    {currentVersion}
                  </Box>
                )}
              </Box>
            </Box>
          </Box>
          <IconButton
            aria-label={t('releaseNotes.dialog.close') as string}
            onClick={onClose}
            size="small"
            sx={{ color: '#fff', flexShrink: 0 }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>

        <Box
          sx={{
            mt: 2,
            display: 'inline-flex',
            bgcolor: 'rgba(255,255,255,0.16)',
            borderRadius: 2,
            p: '3px',
            gap: '2px',
          }}
        >
          {SUPPORTED_LANGUAGES.map((lang) => (
            <Button
              key={lang}
              size="small"
              onClick={() => changeLanguage(lang)}
              sx={{
                minWidth: 40,
                px: 1.25,
                py: 0.5,
                borderRadius: 1.5,
                fontSize: 12,
                fontWeight: 700,
                color: currentLang === lang ? '#1d4ed8' : '#fff',
                bgcolor: currentLang === lang ? '#fff' : 'transparent',
                '&:hover': {
                  bgcolor: currentLang === lang ? '#fff' : 'rgba(255,255,255,0.16)',
                },
              }}
            >
              {lang.toUpperCase()}
            </Button>
          ))}
        </Box>
      </Box>

      <DialogContent sx={{ pt: 2.5 }}>
        {RELEASE_NOTES.map((release, index) => (
          <ReleaseSection
            key={release.version}
            release={release}
            isNew={index === 0}
            expanded={expandedVersion === release.version}
            onToggle={() => toggleRelease(release.version)}
            lang={currentLang}
          />
        ))}

        <Button
          component="a"
          href={RELEASES_URL}
          target="_blank"
          rel="noopener noreferrer"
          size="small"
          sx={{ mt: 0.5, mb: 1, color: 'text.secondary', textTransform: 'none', fontWeight: 500 }}
        >
          {t('releaseNotes.dialog.githubLink')}
        </Button>
      </DialogContent>
    </Dialog>
  );
};

interface ReleaseSectionProps {
  release: ReleaseNoteEntry;
  isNew: boolean;
  expanded: boolean;
  onToggle: () => void;
  lang: string;
}

const ReleaseSection: React.FC<ReleaseSectionProps> = ({ release, isNew, expanded, onToggle, lang }) => {
  const { t } = useTranslation();
  // Sidebar's own nav-group toggle already establishes this pattern
  // (aria-expanded + aria-controls) — this collapsible section had neither.
  const panelId = `release-notes-panel-${release.version}`;
  return (
    <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.75, overflow: 'hidden' }}>
      <Button
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={panelId}
        fullWidth
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          textTransform: 'none',
          color: 'text.primary',
          px: 2,
          py: 1.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
          <ExpandMoreIcon
            fontSize="small"
            sx={{
              color: 'text.secondary',
              transform: expanded ? 'rotate(0deg)' : 'rotate(-90deg)',
              transition: 'transform 180ms',
            }}
          />
          <Typography sx={{ fontWeight: 700 }}>{release.version}</Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {formatReleaseDate(release.date, lang)}
          </Typography>
        </Box>
        {isNew && (
          <Box
            component="span"
            sx={{
              fontSize: 10.5,
              fontWeight: 700,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              color: '#fff',
              bgcolor: '#16a34a',
              px: 1.1,
              py: 0.3,
              borderRadius: 9999,
            }}
          >
            {t('releaseNotes.dialog.newBadge')}
          </Box>
        )}
      </Button>

      <Collapse in={expanded} unmountOnExit>
        <Box id={panelId} sx={{ px: 2, pb: 2, display: 'flex', flexDirection: 'column', gap: 1.75 }}>
          {release.groups.map((group) => (
            <Box key={group.kind}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.875, mb: 0.75 }}>
                <span aria-hidden="true">{RELEASE_NOTE_GROUP_EMOJI[group.kind]}</span>
                <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary' }}>
                  {t(`releaseNotes.groups.${group.kind}`)}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75, pl: 2.6 }}>
                {group.items.map((item) => (
                  <Box key={item.id} sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                      <Box
                        component="span"
                        sx={{
                          width: 5,
                          height: 5,
                          mt: '7px',
                          borderRadius: 9999,
                          bgcolor: 'grey.300',
                          flexShrink: 0,
                        }}
                      />
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        {t(`releaseNotes.entries.${item.id}`)}
                      </Typography>
                    </Box>
                    {(() => {
                      // TF-810: `item.screenshot` may be a single filename or a
                      // per-language map — resolveScreenshotSrc picks the file
                      // for `lang`, falling back to `de` (see releaseNotes.ts).
                      const screenshotFile = resolveScreenshotSrc(item.screenshot, lang);
                      return (
                        screenshotFile && (
                          <Box
                            component="img"
                            src={`/release-notes/${release.version}/${screenshotFile}`}
                            // Review fix: the raw filename is not a description and isn't
                            // translated. The entry's own (already localized) text is the
                            // best description we have without adding a dedicated alt key
                            // per screenshot.
                            alt={t(`releaseNotes.entries.${item.id}`)}
                            sx={{
                              ml: 2.1,
                              maxWidth: '100%',
                              borderRadius: 1,
                              border: '1px solid',
                              borderColor: 'divider',
                            }}
                          />
                        )
                      );
                    })()}
                  </Box>
                ))}
              </Box>
            </Box>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
};
