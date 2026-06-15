import { reflowMoodleAnswer } from '../moodleAnswerReflow';

/**
 * TF-430 — Moodle plattet Zeilenumbrüche in Freitextantworten beim Export.
 * Übrig bleibt Residual-Struktur (NBSP, 3+-Space-Runs, Tabs) an den alten
 * Bruchstellen. reflowMoodleAnswer() rekonstruiert daraus Markdown-taugliche
 * Umbrüche, OHNE den Original-Text in der DB zu verändern (Render-Zeit).
 *
 * Wichtig: Der MarkdownRenderer nutzt nur remark-gfm (kein remark-breaks) —
 * einzelne \n kollabieren zu Leerzeichen. Brüche MÜSSEN als Leerzeilen
 * (\n\n) erzeugt werden, sonst sind sie im Render unsichtbar.
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
    // wort<NBSP>wort (innersatzlich, im Demo-Korpus mehrfach belegt) — darf
    // den Satz nicht zerreissen
    const result = reflowMoodleAnswer(`sehr${NBSP}gut gemacht`);
    expect(result).toBe('sehr gut gemacht');
  });

  it('erzeugt Leerzeilen (\\n\\n), niemals nackte einzelne \\n', () => {
    const result = reflowMoodleAnswer('a)   b)   c)');
    expect(result).toContain('\n\n');
    // keine einsamen \n (jedes \n ist Teil eines \n\n-Paares)
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
    // Signaturen aus dem echten Demo-Korpus (BWZ Modul B, Jennifer Meyer):
    // NBSP+Spaces vor dem ersten Marker, danach 6-Space-Runs vor weiteren
    // Markern, Pfeile, run-on-Blob.
    const real =
      `a)${NBSP}      1.) Kommunikation mit dem Kunden      ` +
      `-> Die Fachsprache ist zu komplex      2.) Zu wenig Klarheit (Monteur)      ` +
      `-> unpräzise Formulierungen`;
    const result = reflowMoodleAnswer(real);
    const segments = result.split('\n\n');
    expect(segments.length).toBeGreaterThanOrEqual(5);
    // kein Segment trägt noch einen Bruch-Lauf in sich (NBSP / Tab / 3+ Spaces)
    for (const seg of segments) {
      expect(seg).not.toMatch(/\u00a0|\t| {3,}/);
      expect(seg.trim()).not.toBe('');
    }
    // Inhalt bleibt vollständig erhalten (nur Whitespace neu gesetzt)
    expect(result.replace(/\s+/g, ' ').trim()).toBe(
      real.replace(/\s+/g, ' ').trim()
    );
  });

  it('normalisiert bereits vorhandene Zeilenumbrüche (\\n, \\r\\n) zu sichtbaren Leerzeilen', () => {
    // Vertrag: niemals ein nacktes einzelnes \n im Output — der MarkdownRenderer
    // würde es zu einem Leerzeichen kollabieren und der Bruch wäre unsichtbar.
    // Schützt die Funktion als alleinigen Hüter der Invariante, falls je eine
    // Quelle doch Newlines liefert (anderer Export, manuell editierte Antwort).
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
    // Charakterisierung: nach dem Reflow rendert der MarkdownRenderer `*`/`-`-
    // Zeilen als Liste — lesbarer als inline im Blob. Bewusst NICHT escaped.
    expect(reflowMoodleAnswer('Antwort:\t- erster Punkt')).toBe(
      'Antwort:\n\n- erster Punkt'
    );
    expect(reflowMoodleAnswer('Punkte:      * Höflichkeit')).toBe(
      'Punkte:\n\n* Höflichkeit'
    );
  });
});
