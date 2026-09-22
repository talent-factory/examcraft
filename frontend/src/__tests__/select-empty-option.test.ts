/**
 * Guard: a labelled empty option must be displayed when it is selected.
 *
 * MUI's Select renders NOTHING for the value '' unless `displayEmpty` is set,
 * and its InputLabel then drops into the field as a placeholder — so a filter
 * whose default is `<MenuItem value="">Alle</MenuItem>` showed "Status" in
 * grey instead of "Alle", and nobody's test noticed because the option is
 * only missing from the closed field, never from the open menu.
 *
 * The fix at each site is `displayEmpty` + `notched` on the Select and
 * `shrink` on its InputLabel (for `TextField select`: `SelectProps.displayEmpty`
 * and `InputLabelProps.shrink`). This guard only checks the part that makes
 * the text appear — `displayEmpty` — because without `shrink` the label and
 * the value overlap, which a reviewer sees at a glance; a missing
 * `displayEmpty` is what stays invisible.
 */
import * as fs from 'fs';
import * as path from 'path';

import { SCAN_ROOTS, stripComments, walk } from '../../scripts/i18n-hardcoded-strings-scan';

// Attribute-order and quote-style tolerant: matches value="", value='',
// value={''} and value={""}, anywhere in the tag (e.g. `<MenuItem key={x}
// value="">`) and across line breaks (`[^>]` matches newlines too).
const EMPTY_OPTION = /<MenuItem\b[^>]*?\bvalue\s*=\s*(?:""|''|\{(['"])\1\})[^>]*>/g;

/** Every labelled empty option whose enclosing Select lacks displayEmpty. */
function missingDisplayEmpty(rawSrc: string): number[] {
  const src = stripComments(rawSrc);
  const lines: number[] = [];
  for (const m of src.matchAll(EMPTY_OPTION)) {
    const at = m.index ?? 0;
    const select = src.lastIndexOf('<Select', at);
    const textField = src.lastIndexOf('<TextField', at);
    const opening = src.slice(Math.max(select, textField, 0), at);
    if (!/\bdisplayEmpty\b/.test(opening)) {
      lines.push(src.slice(0, at).split('\n').length);
    }
  }
  return lines;
}

describe('Select mit beschrifteter Leer-Option', () => {
  it('erkennt die fehlerhafte Form (Selbsttest)', () => {
    const broken = '<Select value={x}>\n  <MenuItem value="">Alle</MenuItem>\n</Select>';
    const fixed = '<Select displayEmpty notched value={x}>\n  <MenuItem value="">Alle</MenuItem>\n</Select>';
    const textField = '<TextField select SelectProps={{ displayEmpty: true }}>\n  <MenuItem value="">Keine</MenuItem>';
    const reorderedAttrs = '<Select value={x}>\n  <MenuItem key="all" value="">Alle</MenuItem>\n</Select>';
    const singleQuotes = "<Select value={x}>\n  <MenuItem value=''>Alle</MenuItem>\n</Select>";
    const jsxExpression = "<Select value={x}>\n  <MenuItem value={''}>Alle</MenuItem>\n</Select>";
    const multiline = '<Select\n  value={x}\n>\n  <MenuItem\n    value=""\n  >Alle</MenuItem>\n</Select>';
    const commentedOut = '// <MenuItem value="">Alle</MenuItem>\n<Select displayEmpty value={x}></Select>';
    expect(missingDisplayEmpty(broken)).toEqual([2]);
    expect(missingDisplayEmpty(fixed)).toEqual([]);
    expect(missingDisplayEmpty(textField)).toEqual([]);
    expect(missingDisplayEmpty(reorderedAttrs)).toEqual([2]);
    expect(missingDisplayEmpty(singleQuotes)).toEqual([2]);
    expect(missingDisplayEmpty(jsxExpression)).toEqual([2]);
    expect(missingDisplayEmpty(multiline)).toEqual([4]);
    expect(missingDisplayEmpty(commentedOut)).toEqual([]);
  });

  // Without this, a broken walk() (wrong/missing root) would silently make
  // the guard vacuously green instead of pointing at a broken scan — same
  // failure mode the sibling i18n-hardcoded-strings.test.ts guards against.
  const SANITY_ROOTS: Array<{ label: string; dir: string; min: number }> = [
    { label: 'core/frontend/src', dir: SCAN_ROOTS[0].dir, min: 50 },
    { label: 'premium/frontend/src', dir: SCAN_ROOTS[1].dir, min: 15 },
    { label: 'enterprise/frontend/src', dir: SCAN_ROOTS[2].dir, min: 0 },
  ];

  for (const { label, dir, min } of SANITY_ROOTS) {
    // Skip (not fail) when the tier root is absent: the public mirror ships
    // core/ only, so a missing premium/ or enterprise/ root is a Core-only
    // checkout, not a broken scan.
    (fs.existsSync(dir) ? it : it.skip)(`scannt überhaupt Dateien (sanity check): ${label}`, () => {
      const count = walk(dir).length;
      if (count <= min) {
        throw new Error(
          `walk() fand nur ${count} Datei(en) unter ${label} (erwartet: > ${min}). ` +
          `Das deutet auf einen falschen/fehlenden Pfad oder einen kaputten Scan hin.`,
        );
      }
    });
  }

  it('zeigt die Leer-Option überall an (displayEmpty gesetzt)', () => {
    const offenders: string[] = [];
    for (const { dir, prefix } of SCAN_ROOTS) {
      // Core-only mirror checkout: premium/enterprise roots are absent by design.
      if (!fs.existsSync(dir)) continue;
      for (const file of walk(dir)) {
        if (!file.endsWith('.tsx')) continue;
        const rel = `${prefix}/${path.relative(dir, file).split(path.sep).join('/')}`;
        for (const line of missingDisplayEmpty(fs.readFileSync(file, 'utf8'))) {
          offenders.push(`${rel}:${line}`);
        }
      }
    }
    if (offenders.length > 0) {
      throw new Error(
        `${offenders.length} Select(s) mit <MenuItem value=""> ohne displayEmpty — ` +
          `die Leer-Option («Alle», «Keine» …) bleibt im geschlossenen Feld unsichtbar. ` +
          `displayEmpty + notched am Select, shrink am InputLabel setzen:\n  ${offenders.join('\n  ')}`,
      );
    }
  });
});
