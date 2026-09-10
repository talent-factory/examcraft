# Release notes screenshots

Static images referenced by optional `screenshot` fields in
`src/data/releaseNotes.ts`, shown in the in-app "What's new" dialog
(TF-802).

## Convention

```
public/release-notes/<version>/<filename>
```

`<version>` matches the `version` field of a `ReleaseNoteEntry` (e.g.
`1.11.0`, no leading `v`). `<filename>` matches the `screenshot` field of a
`ReleaseNoteItem` — any common raster/vector format works (`.png`, `.jpg`,
`.webp`, `.svg`); the dialog just renders it as an `<img>`.

## Per-language screenshots (TF-810)

`screenshot` can be either a single filename (shown for every UI language —
the original TF-802 form) or a map keyed by language:

```ts
screenshot: { de: 'foo-de.png', en: 'foo-en.png' }
```

A language missing from the map falls back to `de`, then to whichever entry
the map has (`resolveScreenshotSrc` in `src/data/releaseNotes.ts`) — so an
item never renders a broken/empty image just because e.g. the FR crop
hasn't been captured yet. Every filename referenced anywhere in the map
still has to exist under this same `<version>/` folder; add languages to the
map incrementally as real crops for that language become available.

## Where the file comes from does not matter

The dialog only checks whether `screenshot` is set — it does not care how
the file got into this folder. Both are valid:

- **Manual**: drop a real screenshot here as part of writing the release
  note entry (crop it small, a few hundred px wide is plenty for the
  dialog's inline preview).
- **Automated** (not built yet, TF-802 scope explicitly excludes it): a
  future release-process script (e.g. a Playwright capture step) could
  write into the same folder using the same naming convention, and the
  dialog would pick it up without any code changes.

## Current example

`1.11.0/admin-kebab-menu.png` is a real crop of the admin panel's user table
(TF-801) with its "Aktionen" kebab menu open — the entry it illustrates.
Cropped to exclude the Benutzer/Institution columns so no real user name or
email address ends up in a screenshot shipped to every end user (review fix,
TF-802: an earlier version of this entry briefly shipped with a labelled
placeholder image instead).

Its `releaseNotes.ts` entry uses the map form with only `de` populated
(`{ de: 'admin-kebab-menu.png' }`, TF-810) — falls back to this same crop for
en/fr/it until real localized crops exist; it's the template for adding
those once captured.
