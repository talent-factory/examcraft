/**
 * Provides the MUI theme with the locale of the current app language (TF-1058),
 * so MUI's built-in texts (pagination, autocomplete, alert) follow i18next and
 * switch along with it.
 */
import React, { useMemo } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { useTranslation } from 'react-i18next';
import { getMuiLocale } from '../config/muiLocale';

export const MuiLocaleThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { i18n } = useTranslation();
  // resolvedLanguage is the language the texts actually render in ('de' for
  // a detected 'de-CH'); language covers the moment before it is resolved.
  const language = i18n.resolvedLanguage ?? i18n.language;
  const theme = useMemo(() => createTheme({}, getMuiLocale(language)), [language]);

  return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
};
