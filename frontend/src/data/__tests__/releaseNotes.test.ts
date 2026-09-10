import * as fs from 'fs';
import * as path from 'path';
import { RELEASE_NOTES, RELEASE_NOTE_GROUP_EMOJI, ReleaseNoteGroupKind } from '../releaseNotes';

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

  it('only declares screenshots that actually exist under public/release-notes/<version>/', () => {
    allItems.forEach(({ release, item }) => {
      if (!item.screenshot) return;
      const filePath = path.resolve(
        __dirname,
        '../../../public/release-notes',
        release.version,
        item.screenshot
      );
      expect(fs.existsSync(filePath)).toBe(true);
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
