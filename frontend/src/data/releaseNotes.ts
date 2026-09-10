/**
 * Release notes manifest for the in-app "What's new" dialog (TF-802).
 *
 * This is intentionally separate from `core/CHANGELOG.md`: the CHANGELOG is
 * the technical, developer-facing record (TF-/PR-referenced, German for
 * current releases) meant for `.github/workflows/release.yml` — and even
 * there only as a *fallback* source when no curated
 * `docs/release-notes-v<VERSION>.md` exists for that version; it does not
 * feed or generate this manifest. This manifest instead holds the
 * language-agnostic *structure* of a curated, end-user-facing subset —
 * translated strings live in the `releaseNotes` namespace of each locale's
 * `translation.json` (see `src/locales/{de,en,fr,it}/translation.json`),
 * keyed by each item's `id`. `src/data/__tests__/releaseNotes.test.ts`
 * checks that every `id`/`kind` used here actually has a translation, and
 * that every `screenshot` resolves to a real file.
 *
 * Screenshots are optional and origin-agnostic: `screenshot` is just a
 * filename (or, since TF-810, a per-language map of filenames — see
 * `resolveScreenshotSrc`) resolved under `/release-notes/<version>/`. It
 * makes no difference whether a file was placed there manually or produced
 * by an automated capture step in the future — the renderer only checks
 * whether the field is set.
 */

import { SupportedLanguage } from '../types/auth';

export type ReleaseNoteGroupKind = 'new' | 'improvements' | 'fixes' | 'security';

/** Emoji per group kind — matches this repo's own commit-prefix convention (see CLAUDE.md). */
export const RELEASE_NOTE_GROUP_EMOJI: Record<ReleaseNoteGroupKind, string> = {
  new: '✨',
  security: '🔐',
  improvements: '🧹',
  fixes: '🐛',
};

export interface ReleaseNoteItem {
  /** Stable id, translated at `releaseNotes.entries.<id>` in each locale. */
  readonly id: string;
  /**
   * Optional screenshot, resolved via `resolveScreenshotSrc` (TF-810) as
   * `/release-notes/<version>/<filename>`. Omit entirely when the entry has
   * no screenshot — no placeholder is rendered in that case.
   *
   * - `string`: a single filename shown for every language (unchanged
   *   pre-TF-810 behaviour — use this until per-language crops exist).
   * - Partial map keyed by `SupportedLanguage`: a different filename per UI
   *   language, e.g. `{ de: 'foo-de.png', en: 'foo-en.png' }`. A language
   *   missing from the map falls back to `de`, then to whichever entry is
   *   present — see `resolveScreenshotSrc`.
   */
  readonly screenshot?: string | Partial<Record<SupportedLanguage, string>>;
}

export interface ReleaseNoteGroup {
  readonly kind: ReleaseNoteGroupKind;
  readonly items: readonly ReleaseNoteItem[];
}

export interface ReleaseNoteEntry {
  /** e.g. "1.11.0" — without the leading "v" (added at render time). */
  readonly version: string;
  /** ISO date (YYYY-MM-DD); formatted per-locale at render time. */
  readonly date: string;
  readonly groups: readonly ReleaseNoteGroup[];
}

/**
 * Resolves a `ReleaseNoteItem.screenshot` to the filename to render for
 * `lang` (TF-810). A plain string is returned unchanged for every language.
 * A per-language map prefers `lang`, then falls back to `de` (the project's
 * primary language — see `CLAUDE.md`, "Language"), then to whichever
 * entry the map actually has — so a language missing a dedicated crop never
 * renders a broken/empty image instead of *some* screenshot. Returns
 * `undefined` only when `screenshot` itself is `undefined` or an empty map.
 */
export const resolveScreenshotSrc = (
  screenshot: ReleaseNoteItem['screenshot'],
  lang: string
): string | undefined => {
  if (screenshot === undefined) return undefined;
  if (typeof screenshot === 'string') return screenshot;
  return (
    screenshot[lang as SupportedLanguage] ?? screenshot.de ?? Object.values(screenshot)[0]
  );
};

/**
 * Newest first — `ReleaseNotesDialog` trusts index 0 for the "current
 * version" badge and the "new" pill (checked by
 * `src/data/__tests__/releaseNotes.test.ts`). Add a new entry here (plus
 * translated strings in every locale) as part of the release checklist —
 * see `docs/developer/contributing.adoc`, "Release Process" — matching the
 * `date` to what actually ends up in `core/CHANGELOG.md`, not the date the
 * entry happens to be written.
 */
export const RELEASE_NOTES: readonly ReleaseNoteEntry[] = [
  {
    version: '1.11.0',
    date: '2026-09-09',
    groups: [
      {
        kind: 'new',
        // Map form (TF-810): only `de` populated for now — falls back to it
        // for en/fr/it via resolveScreenshotSrc until real localized crops
        // exist. Template for adding e.g. `en: 'admin-kebab-menu-en.png'`
        // once one is captured.
        items: [{ id: 'v1_11_0_admin_kebab_menu', screenshot: { de: 'admin-kebab-menu.png' } }],
      },
      {
        kind: 'security',
        items: [{ id: 'v1_11_0_error_messages' }],
      },
      {
        kind: 'fixes',
        items: [{ id: 'v1_11_0_stability' }],
      },
    ],
  },
  {
    version: '1.8.4',
    date: '2026-06-01',
    groups: [
      {
        kind: 'improvements',
        items: [{ id: 'v1_8_4_result_import' }],
      },
      {
        kind: 'fixes',
        items: [{ id: 'v1_8_4_reasoning_formatting' }],
      },
    ],
  },
];
