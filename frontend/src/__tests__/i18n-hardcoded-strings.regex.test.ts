/**
 * Regression test for the `literal-error` scan (TF-772 C1).
 *
 * The predecessor regex required the string literal to sit directly inside
 * `new Error(`, so it saw 15 of 95 throw sites in the service directories. The
 * misses were not exotic: 68 were `new Error(detail || 'text')` and 12 passed
 * the literal into a helper. Both shapes nest, which is why the scan reads a
 * balanced argument instead of matching a regex against it.
 *
 * Each form below gets its own example, so a future "simplification" back to a
 * flat regex fails here rather than silently halving the guard's reach — the
 * failure mode that made this ticket necessary in the first place.
 *
 * The negative cases matter just as much: a scan that reports everything is as
 * useless as one that reports nothing, and it would inflate the allowlist that
 * TF-772 measures progress by.
 */
import { scanSource, stripComments } from '../../scripts/i18n-hardcoded-strings-scan';

const SERVICE = 'core/frontend/src/services/ExampleService.ts';
const COMPONENT = 'core/frontend/src/components/Example.tsx';

/** The `literal-error` texts the scan reports for one snippet. */
function literals(source: string, file: string = SERVICE): string[] {
  return scanSource(stripComments(source), file)
    .filter((f) => f.kind === 'literal-error')
    .map((f) => f.text);
}

describe('literal-error: erfasste Formen', () => {
  it('A — nacktes Literal', () => {
    expect(literals(`throw new Error('Bare literal message');`)).toEqual([
      'Bare literal message',
    ]);
  });

  it('B — nacktes Template-Literal', () => {
    // The `${…}` is deliberately literal on both sides: the fixture must contain
    // the characters a template literal is made of, and the expectation is the
    // raw inner text the scan reports for it (as in the real dashboard.ts).
    /* eslint-disable no-template-curly-in-string */
    expect(literals('throw new Error(`Dashboard stats failed: ${resp.status}`);')).toEqual([
      'Dashboard stats failed: ${resp.status}',
    ]);
    /* eslint-enable no-template-curly-in-string */
  });

  it("C — x || 'literal' (die dominante Form, 68 Stellen)", () => {
    expect(literals(`throw new Error(errorData.detail || 'Failed to fetch review queue');`))
      .toEqual(['Failed to fetch review queue']);
  });

  it('D — Ternär mit Literal', () => {
    expect(literals(`throw new Error(e.detail ? e.detail : 'Unknown failure');`)).toEqual([
      'Unknown failure',
    ]);
  });

  it('E — Literal als Argument eines Hilfsaufrufs (12 Stellen)', () => {
    expect(literals(`throw new Error(extractApiError(error.detail, 'Login failed'));`)).toEqual([
      'Login failed',
    ]);
  });

  it('F — reject(new Error(…)) ohne throw (WS_ERRORS-Form)', () => {
    expect(literals(`reject(new Error('Die Verbindung wurde unterbrochen'));`)).toEqual([
      'Die Verbindung wurde unterbrochen',
    ]);
  });

  it('G — Klammer im Literal beendet das Argument nicht vorzeitig', () => {
    expect(literals(`throw new Error('Fehler (intern) aufgetreten');`)).toEqual([
      'Fehler (intern) aufgetreten',
    ]);
  });

  it('H — maskiertes Anführungszeichen beendet das Literal nicht', () => {
    expect(literals(`throw new Error('It\\'s broken');`)).toEqual(["It\\'s broken"]);
  });

  it('mehrere Literale in einem Wurf werden einzeln gemeldet', () => {
    expect(literals(`throw new Error(a || 'First fallback' || 'Second fallback');`)).toEqual([
      'First fallback',
      'Second fallback',
    ]);
  });

  it('meldet die Zeile des Wurfs, nicht die des Literals', () => {
    const source = ['const x = 1;', 'throw new Error(', "  detail || 'Wrapped fallback',", ');'].join(
      '\n',
    );
    const [finding] = scanSource(stripComments(source), SERVICE).filter(
      (f) => f.kind === 'literal-error',
    );
    expect(finding.line).toBe(2);
  });
});

describe('literal-error: bewusst nicht erfasst', () => {
  it('kein Literal im Argument', () => {
    expect(literals(`throw new Error(error.detail);`)).toEqual([]);
  });

  it('Literal kürzer als drei Zeichen', () => {
    expect(literals(`throw new Error('ok');`)).toEqual([]);
  });

  it('ausserhalb von services/ und api/ (Deliberate Gap 3)', () => {
    expect(literals(`throw new Error('Not authenticated');`, COMPONENT)).toEqual([]);
  });

  it('auskommentierter Code', () => {
    expect(literals(`// throw new Error('Commented out');`)).toEqual([]);
  });

  it('api/ wird wie services/ behandelt', () => {
    expect(literals(`throw new Error('Prompts API failed');`, 'core/frontend/src/api/promptsApi.ts'))
      .toEqual(['Prompts API failed']);
  });
});
