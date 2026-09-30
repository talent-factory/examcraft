import de from '../../../locales/de/translation.json';
import en from '../../../locales/en/translation.json';
import fr from '../../../locales/fr/translation.json';
// Not `it` — that would shadow Jest's global (see AppErrorCode.i18n.test.ts).
import itLocale from '../../../locales/it/translation.json';
import {
  PORTFOLIO_JOB_CODES,
  describePortfolioJobEntry,
  isPortfolioJobCode,
  portfolioJobEntryFiles,
} from '../portfolioJobMessages';
import type { PortfolioJobLogEntry } from '../../../types/portfolio';

/**
 * The job/warning codes are not AppErrorCodes, so AppErrorCode.i18n.test.ts
 * does not cover them — this is their counterpart (TF-987).
 */

function resolveKey(obj: Record<string, unknown>, key: string): unknown {
  return key.split('.').reduce<unknown>((current, part) => {
    if (current == null || typeof current !== 'object') return undefined;
    return (current as Record<string, unknown>)[part];
  }, obj);
}

const LOCALES: Array<[string, Record<string, unknown>]> = [
  ['de', de],
  ['en', en],
  ['fr', fr],
  ['it', itLocale],
];

for (const [locale, translations] of LOCALES) {
  describe(`Portfolio-Jobcodes → pages.portfolio.jobCodes.<code> (${locale})`, () => {
    for (const code of PORTFOLIO_JOB_CODES) {
      it(`${code} hat einen Übersetzungs-Eintrag`, () => {
        const value = resolveKey(translations, `pages.portfolio.jobCodes.${code}`);
        expect(typeof value).toBe('string');
        expect((value as string).length).toBeGreaterThan(0);
      });
    }

    it('hat keine verwaisten jobCodes-Einträge', () => {
      const keys = Object.keys(
        resolveKey(translations, 'pages.portfolio.jobCodes') as Record<string, unknown>,
      );
      expect(keys.filter((key) => !isPortfolioJobCode(key))).toEqual([]);
    });
  });
}

it('PORTFOLIO_JOB_CODES ist alphabetisch und ohne Duplikate', () => {
  expect([...PORTFOLIO_JOB_CODES]).toEqual([...new Set(PORTFOLIO_JOB_CODES)].sort());
});

describe('describePortfolioJobEntry', () => {
  afterEach(() => jest.restoreAllMocks());

  const t = (key: string, params?: Record<string, unknown>) =>
    params ? `${key} ${JSON.stringify(params)}` : key;

  it('übersetzt einen bekannten Code und verschweigt den deutschen reason', () => {
    expect(
      describePortfolioJobEntry(
        { code: 'portfolio_grading_timeout', reason: 'Zeitlimit der Bewertung ueberschritten' },
        t,
      ),
    ).toBe('pages.portfolio.jobCodes.portfolio_grading_timeout');
  });

  it('stürzt bei einem Eintrag, der kein Objekt ist, nicht ab', () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    expect(describePortfolioJobEntry(null as unknown as PortfolioJobLogEntry, t)).toBe(
      'pages.portfolio.job.unknownEntry',
    );
    expect(describePortfolioJobEntry('boom' as unknown as PortfolioJobLogEntry, t)).toBe(
      'pages.portfolio.job.unknownEntry',
    );
    warn.mockRestore();
  });

  it('protokolliert einen unbekannten Code', () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    describePortfolioJobEntry({ code: 'portfolio_future_code' }, t);
    expect(warn).toHaveBeenCalledWith(
      '[portfolio] Unknown job code, using fallback:',
      'portfolio_future_code',
      expect.anything(),
    );
    warn.mockRestore();
  });

  it('zeigt bei einem unbekannten Code den generischen Text plus reason', () => {
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    expect(
      describePortfolioJobEntry({ code: 'portfolio_future_code', reason: 'Neu im Backend' }, t),
    ).toBe('pages.portfolio.job.unknownEntryWithReason {"reason":"Neu im Backend"}');
  });

  it('zeigt ohne Code und reason nur den generischen Text', () => {
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    expect(describePortfolioJobEntry({}, t)).toBe('pages.portfolio.job.unknownEntry');
  });
});

describe('portfolioJobEntryFiles', () => {
  it('liefert paths bzw. skipped_files und ignoriert Nicht-Strings', () => {
    expect(portfolioJobEntryFiles({ paths: ['a.pdf', 3 as unknown as string] })).toEqual(['a.pdf']);
    expect(portfolioJobEntryFiles({ skipped_files: ['b.md'] })).toEqual(['b.md']);
    expect(portfolioJobEntryFiles({ code: 'portfolio_grading_timeout' })).toEqual([]);
    expect(portfolioJobEntryFiles(null as unknown as PortfolioJobLogEntry)).toEqual([]);
  });
});
