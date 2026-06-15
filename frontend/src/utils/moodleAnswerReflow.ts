/**
 * Rekonstruiert lesbare Zeilenstruktur in Moodle-Freitextantworten (TF-430).
 *
 * Moodle plattet Zeilenumbrüche bereits beim Export — in keiner Quelldatei
 * (JSON oder CSV) sind sie noch vorhanden. Übrig bleibt Residual-Struktur an
 * den alten Bruchstellen: NBSP (U+00A0), Läufe von 3+ Leerzeichen und Tabs.
 * Diese Funktion verwandelt diese Signale zur Render-Zeit in Markdown-taugliche
 * Absatzumbrüche, OHNE den in der DB gespeicherten Originaltext zu verändern.
 *
 * Bewusst konservativ (Guard gegen Über-Segmentierung):
 * - Ein Tab oder ein Lauf von 3+ Whitespace (Spaces und/oder NBSP) bricht.
 * - Ein einzelnes NBSP (oder 1–2-Zeichen-Lauf) wird zu einem normalen
 *   Leerzeichen — so zerreissen innersatzliche `wort<NBSP>wort`-Fälle (im
 *   Demo-Korpus mehrfach belegt) den Satz nicht.
 *
 * Der MarkdownRenderer nutzt nur `remark-gfm` (kein `remark-breaks`); einzelne
 * `\n` kollabieren dort zu Leerzeichen. Brüche werden deshalb als Leerzeilen
 * (`\n\n`) ausgegeben, damit sie im Render sichtbar bleiben.
 *
 * Gibt `''` für null/undefined/leer/whitespace-only zurück, damit Aufrufer
 * ihren `|| '—'`-Fallback behalten.
 */

// Interne Bruchmarke: U+0000 kommt in Moodle-Antworten nie vor und dient nur
// als Sentinel vor split(). Bewusst als Escape (nicht als unsichtbares Byte)
// notiert — NICHT durch ein Leerzeichen ersetzen.
const BREAK = '\u0000';

export function reflowMoodleAnswer(text: string | null | undefined): string {
  if (!text) return '';

  const withBreaks = text
    // bereits vorhandene Zeilenumbrüche (CR/LF) sind echte Brüche — nie als
    // nacktes einzelnes \n durchreichen (würde im Render unsichtbar kollabieren)
    .replace(/[\r\n]+/g, BREAK)
    // Tab = Einrückungs-/Umbruch-Residue → Bruch
    .replace(/\t/g, BREAK)
    // Lauf von 3+ Whitespace (Space und/oder NBSP) → Bruch
    .replace(/[ \u00a0]{3,}/g, BREAK)
    // verbleibende NBSP (solo / 1–2er-Lauf) → normales Leerzeichen
    .replace(/\u00a0/g, ' ');

  return withBreaks
    .split(BREAK)
    .map((segment) => segment.replace(/ {2,}/g, ' ').trim())
    .filter((segment) => segment.length > 0)
    .join('\n\n');
}

export default reflowMoodleAnswer;
