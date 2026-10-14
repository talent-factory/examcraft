/**
 * MUI component locales for the app languages (TF-1058)
 *
 * MUI ships English default texts ("Rows per page", "No options", "Close")
 * unless a theme carries a locale. The app language decides which one.
 */
import { deDE, enUS, frFR, itIT } from '@mui/material/locale';
import type { Localization } from '@mui/material/locale';

/**
 * Applies Swiss orthography (ss instead of ß) to every text of a locale.
 * MUI locales hold strings and label functions (`getItemAriaLabel`,
 * `labelDisplayedRows`), so functions are wrapped and their result converted.
 */
const toSwissOrthography = <T>(value: T): T => {
  if (typeof value === 'string') {
    return value.replace(/ß/g, 'ss') as T;
  }
  if (typeof value === 'function') {
    const fn = value as unknown as (...args: unknown[]) => unknown;
    return ((...args: unknown[]) => toSwissOrthography(fn(...args))) as T;
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, entry]) => [key, toSwissOrthography(entry)])
    ) as T;
  }
  return value;
};

/** MUI's deDE in Swiss orthography: "Schliessen" instead of "Schließen". */
export const deCH: Localization = toSwissOrthography(deDE);

const MUI_LOCALES: Record<string, Localization> = {
  de: deCH,
  fr: frFR,
  it: itIT,
};

/**
 * Maps an i18next language ('de', 'de-CH', 'fr-FR', …) to its MUI locale.
 * Only the primary subtag counts; anything unmapped falls back to enUS.
 */
export const getMuiLocale = (language: string | undefined): Localization => {
  const primary = (language ?? '').split('-')[0].toLowerCase();
  return MUI_LOCALES[primary] ?? enUS;
};
