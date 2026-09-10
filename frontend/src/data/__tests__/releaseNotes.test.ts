import * as fs from 'fs';
import * as path from 'path';
import {
  RELEASE_NOTES,
  RELEASE_NOTE_GROUP_EMOJI,
  ReleaseNoteGroupKind,
  resolveScreenshotSrc,
} from '../releaseNotes';

// Review fix: the existing "translation completeness" test in
// ReleaseNotesDialog.test.tsx only compares the de/en/fr/it translation.json
// files against *each other* — it never reads RELEASE_NOTES at all, so a
// typo'd `item.id` or `group.kind` (which the renderer resolves to
// `t(`releaseNotes.entries.${item.id}`)` / `t(`releaseNotes.groups.${group.kind}`)`)
// passes every existing check and then silently renders the raw i18n key to
// users. This file closes that gap by checking the manifest itself, plus a
// few structural invariants (`version` uniqueness/ordering, `screenshot`
// files actually existing) that were previously enforced only by prose
// comments in releaseNotes.ts.

// eslint-disable-next-line @typescript-eslint/no-var-requires
const deTranslations = require('../../locales/de/translation.json').releaseNotes;

const allItems = RELEASE_NOTES.flatMap((release) =>
  release.groups.flatMap((group) => group.items.map((item) => ({ release, group, item })))
);

describe('RELEASE_NOTES manifest integrity', () => {
  it('has a releaseNotes.entries.<id> translation for every item id', () => {
    allItems.forEach(({ item }) => {
      expect(deTranslations.entries).toHaveProperty(item.id);
    });
  });

  it('has a releaseNotes.groups.<kind> translation and an emoji for every group kind used', () => {
    const kindsInUse = new Set<ReleaseNoteGroupKind>(
      RELEASE_NOTES.flatMap((release) => release.groups.map((group) => group.kind))
    );
    kindsInUse.forEach((kind) => {
      expect(deTranslations.groups).toHaveProperty(kind);
      expect(RELEASE_NOTE_GROUP_EMOJI).toHaveProperty(kind);
    });
  });

  // Review fix (TF-810): assert isFile() rather than existsSync() alone — an
  // empty-string or '.'/'..'-containing filename can resolve to a directory
  // (or escape the version folder entirely) and still pass a bare existsSync
  // check, silently defeating this test's "resolves to a real file under
  // this version's folder" guarantee. A plain basename check also rejects
  // any path-separator characters, so a value can't resolve outside
  // `<version>/` no matter how existsSync would treat the result.
  const expectResolvesToRealFile = (release: { version: string }, filename: string) => {
    expect(filename).not.toBe('');
    expect(path.basename(filename)).toBe(filename);
    const filePath = path.resolve(
      __dirname,
      '../../../public/release-notes',
      release.version,
      filename
    );
    expect(fs.existsSync(filePath) && fs.statSync(filePath).isFile()).toBe(true);
  };

  it('only declares screenshots that actually exist under public/release-notes/<version>/ — string form', () => {
    allItems.forEach(({ release, item }) => {
      if (typeof item.screenshot !== 'string') return;
      expectResolvesToRealFile(release, item.screenshot);
    });
  });

  // TF-810: a per-language screenshot map must have every referenced
  // filename actually present — same invariant as the string form, just
  // checked across all of the map's values instead of a single filename.
  it('only declares screenshots that actually exist under public/release-notes/<version>/ — per-language map form', () => {
    allItems.forEach(({ release, item }) => {
      if (typeof item.screenshot !== 'object' || item.screenshot === undefined) return;
      Object.values(item.screenshot).forEach((filename) => {
        expectResolvesToRealFile(release, filename as string);
      });
    });
  });

  it('has unique version numbers', () => {
    const versions = RELEASE_NOTES.map((release) => release.version);
    expect(new Set(versions).size).toBe(versions.length);
  });

  it('is ordered newest first by date — ReleaseNotesDialog trusts RELEASE_NOTES[0] for the "current version" badge and "new" pill', () => {
    const dates = RELEASE_NOTES.map((release) => new Date(`${release.date}T00:00:00`).getTime());
    const sortedDescending = [...dates].sort((a, b) => b - a);
    expect(dates).toEqual(sortedDescending);
  });

  it('has a parseable ISO date for every entry', () => {
    RELEASE_NOTES.forEach((release) => {
      const parsed = new Date(`${release.date}T00:00:00`);
      expect(Number.isNaN(parsed.getTime())).toBe(false);
    });
  });

  it('has no duplicate group kind within a single release entry', () => {
    RELEASE_NOTES.forEach((release) => {
      const kinds = release.groups.map((group) => group.kind);
      expect(new Set(kinds).size).toBe(kinds.length);
    });
  });

  it('has no duplicate item id within a single group', () => {
    RELEASE_NOTES.forEach((release) => {
      release.groups.forEach((group) => {
        const ids = group.items.map((item) => item.id);
        expect(new Set(ids).size).toBe(ids.length);
      });
    });
  });
});

describe('resolveScreenshotSrc (TF-810)', () => {
  it('returns undefined when screenshot is undefined', () => {
    expect(resolveScreenshotSrc(undefined, 'en')).toBeUndefined();
  });

  it('returns the filename unchanged for the string form, regardless of language', () => {
    expect(resolveScreenshotSrc('foo.png', 'en')).toBe('foo.png');
    expect(resolveScreenshotSrc('foo.png', 'fr')).toBe('foo.png');
  });

  it('picks the entry matching the requested language from a map', () => {
    const screenshot = { de: 'foo-de.png', en: 'foo-en.png' };
    expect(resolveScreenshotSrc(screenshot, 'en')).toBe('foo-en.png');
    expect(resolveScreenshotSrc(screenshot, 'de')).toBe('foo-de.png');
  });

  it('falls back to de when the requested language is missing from the map', () => {
    const screenshot = { de: 'foo-de.png', en: 'foo-en.png' };
    expect(resolveScreenshotSrc(screenshot, 'fr')).toBe('foo-de.png');
    expect(resolveScreenshotSrc(screenshot, 'it')).toBe('foo-de.png');
  });

  it('falls back to whichever entry is present when de itself is missing', () => {
    const screenshot = { fr: 'foo-fr.png' };
    expect(resolveScreenshotSrc(screenshot, 'en')).toBe('foo-fr.png');
  });

  // Review fix (TF-810): the doc comment explicitly calls out "an empty map"
  // as a case that returns undefined — assert it, since Object.values({})[0]
  // being undefined is exactly the kind of thing a future refactor could
  // silently break.
  it('returns undefined when the map is empty', () => {
    expect(resolveScreenshotSrc({}, 'en')).toBeUndefined();
  });
});
