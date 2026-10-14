/**
 * TF-1058: MUI's built-in texts follow the app language, in Swiss orthography
 * for German.
 *
 * Rendered with the real i18next: the global react-i18next mock in
 * setupTests.ts always answers in German and never switches language, which
 * is exactly what these tests have to be able to see.
 */
import React from 'react';
import fs from 'fs';
import path from 'path';
import { act, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import Alert from '@mui/material/Alert';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import { deDE, enUS, frFR, itIT } from '@mui/material/locale';
import i18n from '../../i18n';
import { deCH, getMuiLocale } from '../../config/muiLocale';
import { MuiLocaleThemeProvider } from '../MuiLocaleThemeProvider';

// Hoisted above the imports by babel-plugin-jest-hoist.
jest.unmock('react-i18next');

/**
 * Every text a locale can render: its strings, plus what its label functions
 * return for each argument shape MUI passes them.
 */
const collectTexts = (value: unknown): string[] => {
  if (typeof value === 'string') return [value];
  if (typeof value === 'function') {
    const fn = value as (...args: unknown[]) => unknown;
    return ['first', 'last', 'next', 'previous', 'page']
      .flatMap((type) => [fn(type, 3, true), fn(type, 3, false)])
      .concat(fn({ from: 1, to: 10, count: 20, page: 0 }), fn({ from: 1, to: 10, count: -1, page: 0 }), fn(1), fn(3))
      .flatMap(collectTexts);
  }
  if (value && typeof value === 'object') return Object.values(value).flatMap(collectTexts);
  return [];
};

const renderMuiTexts = () =>
  render(
    <MuiLocaleThemeProvider>
      <Alert onClose={() => {}}>Hinweis</Alert>
      <Autocomplete options={['A']} renderInput={(params) => <TextField {...params} label="Tag" />} />
    </MuiLocaleThemeProvider>
  );

describe('MUI locale (TF-1058)', () => {
  afterEach(async () => {
    await act(async () => {
      await i18n.changeLanguage('de');
    });
  });

  it('deCH is deDE without any ß', () => {
    const texts = collectTexts(deCH);
    // The walk must actually reach the label functions, not only the strings.
    expect(texts).toEqual(expect.arrayContaining(['Zur nächsten Seite', '1–10 von mehr als 10']));
    expect(texts.filter((text) => text.includes('ß'))).toEqual([]);
    // Guards the test itself: deDE still carries the ß it is meant to replace.
    expect(collectTexts(deDE).some((text) => text.includes('ß'))).toBe(true);
    expect(deCH.components?.MuiAlert?.defaultProps?.closeText).toBe('Schliessen');
    expect(deCH.components?.MuiAutocomplete?.defaultProps?.openText).toBe('Öffnen');
  });

  it('the German app texts contain no ß', () => {
    const file = path.join(__dirname, '../../locales/de/translation.json');
    const lines = fs.readFileSync(file, 'utf8').split('\n');
    expect(lines.filter((line) => line.includes('ß'))).toEqual([]);
  });

  it.each([
    ['de', deCH],
    ['de-CH', deCH],
    ['fr', frFR],
    ['fr-CH', frFR],
    ['it', itIT],
    ['en', enUS],
    ['es', enUS],
    [undefined, enUS],
  ])('maps %s to its MUI locale', (language, locale) => {
    expect(getMuiLocale(language)).toBe(locale);
  });

  it('switches the MUI texts along with the app language', async () => {
    await act(async () => {
      await i18n.changeLanguage('de');
    });
    renderMuiTexts();
    expect(screen.getByRole('button', { name: 'Schliessen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Öffnen' })).toBeInTheDocument();

    await act(async () => {
      await i18n.changeLanguage('fr');
    });
    expect(screen.getByRole('button', { name: 'Fermer' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ouvrir' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Schliessen' })).not.toBeInTheDocument();
  });

  it('shows the German MUI texts for a detected de-CH', async () => {
    await act(async () => {
      await i18n.changeLanguage('de-CH');
    });
    renderMuiTexts();
    expect(screen.getByRole('button', { name: 'Schliessen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Öffnen' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument();
  });
});
