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
