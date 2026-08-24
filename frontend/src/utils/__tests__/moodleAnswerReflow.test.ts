import { reflowMoodleAnswer } from '../moodleAnswerReflow';

/**
 * TF-430 — Moodle flattens line breaks in free-text answers on export.
 * What remains is residual structure (NBSP, 3+-space runs, tabs) at the
 * old break points. reflowMoodleAnswer() reconstructs Markdown-friendly
 * breaks from that, WITHOUT changing the original text in the DB (render time).
 *
 * Important: the MarkdownRenderer only uses remark-gfm (no remark-breaks) —
 * single \n collapse to a space. Breaks MUST be produced as blank lines
 * (\n\n), otherwise they're invisible in the render.
 */
const NBSP = '\u00a0';

describe('reflowMoodleAnswer (TF-430)', () => {
  it('macht aus einem Tab einen Markdown-Absatzumbruch', () => {
    const result = reflowMoodleAnswer('1.) Erster Punkt\t2.) Zweiter Punkt');
    expect(result).toBe('1.) Erster Punkt\n\n2.) Zweiter Punkt');
  });

  it('macht aus einem Lauf von 3+ Leerzeichen einen Absatzumbruch', () => {
    const result = reflowMoodleAnswer('a)      1.) Kommunikation mit dem Kunden');
    expect(result).toBe('a)\n\n1.) Kommunikation mit dem Kunden');
  });

  it('bricht an NBSP+Space-Läufen (Moodle-Residual NSSSSSS)', () => {
    const result = reflowMoodleAnswer(`Kunden${NBSP}      -> Formulierungen`);
    expect(result).toBe('Kunden\n\n-> Formulierungen');
  });

  it('bricht NICHT bei einzelnem NBSP mitten im Satz (kein Über-Segmentieren)', () => {
    // word<NBSP>word (mid-sentence, occurs repeatedly in the demo corpus) —
    // must not tear the sentence apart
    const result = reflowMoodleAnswer(`sehr${NBSP}gut gemacht`);
    expect(result).toBe('sehr gut gemacht');
  });

  it('erzeugt Leerzeilen (\\n\\n), niemals nackte einzelne \\n', () => {
    const result = reflowMoodleAnswer('a)   b)   c)');
    expect(result).toContain('\n\n');
    // no lone \n (every \n is part of a \n\n pair)
    expect(/[^\n]\n[^\n]/.test(result)).toBe(false);
  });

  it('lässt eine bereits saubere Choice-Antwort unverändert', () => {
    const clean = 'Option B: Ich höre beiden aktiv zu und vermittle.';
    expect(reflowMoodleAnswer(clean)).toBe(clean);
  });

  it('liefert leeren String für null/undefined/leer (Fallback "—" bleibt erhalten)', () => {
    expect(reflowMoodleAnswer(null)).toBe('');
    expect(reflowMoodleAnswer(undefined)).toBe('');
    expect(reflowMoodleAnswer('')).toBe('');
    expect(reflowMoodleAnswer('   ')).toBe('');
  });

  it('ist idempotent (Reflow eines Reflows ändert nichts)', () => {
    const raw = `a)${NBSP}      1.) Punkt\t-> Folge      2.) Anderer`;
    const once = reflowMoodleAnswer(raw);
    expect(reflowMoodleAnswer(once)).toBe(once);
  });

  it('reflowt einen realen, run-on-Antwortausschnitt in mehrere Segmente', () => {
    // Signatures from the real demo corpus (BWZ Modul B, Jennifer Meyer):
    // NBSP+spaces before the first marker, then 6-space runs before further
    // markers, arrows, run-on blob.
    const real =
      `a)${NBSP}      1.) Kommunikation mit dem Kunden      ` +
      `-> Die Fachsprache ist zu komplex      2.) Zu wenig Klarheit (Monteur)      ` +
      `-> unpräzise Formulierungen`;
    const result = reflowMoodleAnswer(real);
    const segments = result.split('\n\n');
    expect(segments.length).toBeGreaterThanOrEqual(5);
    // no segment still carries a break-run within it (NBSP / Tab / 3+ spaces)
    for (const seg of segments) {
      expect(seg).not.toMatch(/\u00a0|\t| {3,}/);
      expect(seg.trim()).not.toBe('');
    }
    // content stays fully intact (only whitespace is re-set)
    expect(result.replace(/\s+/g, ' ').trim()).toBe(
      real.replace(/\s+/g, ' ').trim()
    );
  });

  it('normalisiert bereits vorhandene Zeilenumbrüche (\\n, \\r\\n) zu sichtbaren Leerzeilen', () => {
    // Contract: never a lone single \n in the output — the MarkdownRenderer
    // would collapse it to a space and the break would be invisible.
    // Protects the function as the sole guardian of the invariant, in case
    // some source ever does deliver newlines (a different export, a manually
    // edited answer).
    const result = reflowMoodleAnswer('Zeile 1\nZeile 2\r\nZeile 3');
    expect(result).toBe('Zeile 1\n\nZeile 2\n\nZeile 3');
    expect(/[^\n]\n[^\n]/.test(result)).toBe(false);
  });

  it('bricht bei genau 2 Leerzeichen NICHT, bei 3 schon (Schwellenwert-Grenze)', () => {
    expect(reflowMoodleAnswer('foo  bar')).toBe('foo bar');
    expect(reflowMoodleAnswer('foo   bar')).toBe('foo\n\nbar');
  });

  it('führende/abschliessende Bruchsignale erzeugen keine leeren Absätze', () => {
    expect(reflowMoodleAnswer('\tHallo Welt   ')).toBe('Hallo Welt');
    expect(reflowMoodleAnswer('   Hallo Welt')).toBe('Hallo Welt');
  });

  it('Spiegelstrich-/Stern-Marker landen am Zeilenanfang (→ Markdown-Liste, gewollt)', () => {
    // Characterization: after the reflow, the MarkdownRenderer renders `*`/`-`
    // lines as a list — more readable than inline in the blob. Deliberately NOT escaped.
    expect(reflowMoodleAnswer('Antwort:\t- erster Punkt')).toBe(
      'Antwort:\n\n- erster Punkt'
    );
    expect(reflowMoodleAnswer('Punkte:      * Höflichkeit')).toBe(
      'Punkte:\n\n* Höflichkeit'
    );
  });
});
