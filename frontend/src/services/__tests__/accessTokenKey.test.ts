import * as fs from 'fs';
import * as path from 'path';
import { ACCESS_TOKEN_KEY } from '../../api/tokenRefreshLock';
import { GradeExportService } from '../gradeExportService';
import { GradingSchemesService } from '../gradingSchemesService';
import { MoodleFeedbackPushService } from '../moodleFeedbackPushService';
import { StatisticsService } from '../statisticsService';

/**
 * These four services read the bearer token from `localStorage['access_token']`
 * until TF-773 Teil D — a key nothing ever writes; the app stores it under
 * `examcraft_access_token`. Every call therefore went out without a token,
 * came back 401, and only succeeded because the global fetch interceptor
 * refreshed and retried. The Moodle push polls every 2 s, so each poll cost
 * three requests (401, refresh, retry): about 90 a minute against a limit of
 * 60. A push running longer than ~40 s ended in a 429 and the generic «Die
 * Übertragung konnte nicht gestartet werden».
 */

const calls: Array<() => Promise<unknown>> = [
  () => GradeExportService.download(1, 'csv' as never),
  () => GradingSchemesService.list(),
  () => MoodleFeedbackPushService.start(1),
  () => StatisticsService.getOverview(1),
];

describe('Services senden den Token aus examcraft_access_token', () => {
  const fetchMock = jest.fn();

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem(ACCESS_TOKEN_KEY, 'tok-123');
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
      blob: async () => new Blob(),
      headers: new Headers(),
    });
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  it.each(calls.map((call, i) => [i, call] as const))(
    'Aufruf %i trägt den Authorization-Header',
    async (_i, call) => {
      await call().catch(() => undefined);
      expect(fetchMock).toHaveBeenCalled();
      const init = fetchMock.mock.calls[0][1] as RequestInit | undefined;
      expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer tok-123');
    },
  );
});

it('kein Service in core/premium/enterprise liest den Token mehr unter dem Schlüssel access_token', () => {
  // TF-773 Teil D: der ursprüngliche Bug sass in core/frontend, aber
  // RAGService.ts (premium/frontend) duplizierte denselben Tokenwert bis
  // dahin als Literal statt ACCESS_TOKEN_KEY zu importieren — ein künftiges
  // Auseinanderdriften wäre in premium/enterprise unbemerkt geblieben, wenn
  // der Wächter nur core scannt.
  //
  // Aufwärts suchen statt zählen (wie _frontend_root() in
  // test_core_router_error_codes.py): der öffentliche core/-Mirror entsteht
  // per `git subtree split --prefix=core` und hat weder premium/ noch
  // enterprise/ noch ein core/-Verzeichnis darüber — ein fester
  // Ebenen-Zähler zu einem "Repo-Root" würde dort daneben- oder aus dem
  // Checkout hinauszeigen (core/frontend/src hat hier eine Ebene mehr über
  // sich als <mirror>/frontend/src).
  const frontendSrc = path.resolve(__dirname, '../..');
  const findTierRoot = (start: string): string | null => {
    let dir = start;
    for (let i = 0; i < 5; i++) {
      if (fs.existsSync(path.join(dir, 'premium/frontend/src'))) return dir;
      const parent = path.dirname(dir);
      if (parent === dir) return null;
      dir = parent;
    }
    return null;
  };
  const tierRoot = findTierRoot(frontendSrc);
  const scanRoots = [
    frontendSrc,
    ...(tierRoot
      ? [path.join(tierRoot, 'premium/frontend/src'), path.join(tierRoot, 'enterprise/frontend/src')]
      : []),
  ].filter((p) => fs.existsSync(p));
  const offenders: string[] = [];
  const walk = (dir: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name !== 'node_modules' && entry.name !== '__tests__') walk(full);
      } else if (/\.(ts|tsx)$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)) {
        if (/localStorage\.getItem\(\s*['"]access_token['"]\s*\)/.test(fs.readFileSync(full, 'utf8'))) {
          offenders.push(path.relative(tierRoot ?? frontendSrc, full));
        }
      }
    }
  };
  scanRoots.forEach(walk);
  expect(offenders).toEqual([]);
});
