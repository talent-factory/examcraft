/**
 * The tour's texts live in translation.json, its structure in
 * help-onboarding-steps.json, and an `i18n_key` per step joins the two. Nothing
 * in the type system holds that join together: a renamed step or a dropped
 * translation key surfaces only as a raw key string in the popover.
 *
 * That is exactly how the old shape failed — `title_de`/`title_en` field pairs
 * made every non-English language fall back to German, and no test noticed
 * because none of them asserted on the rendered text (TF-670).
 *
 * This file is the join's only guard: every key referenced by the steps file
 * must resolve in every shipped locale that claims to have the tour.
 */
import * as fs from 'fs';
import * as path from 'path';

const STEPS_PATH = path.join(__dirname, '../../../../public/help-onboarding-steps.json');

type Step = { step: number; i18n_key: string };
type Track = { id: string; i18n_key: string; steps: Step[] };
type Role = { core: Step[]; tracks: Track[] };

const steps: Record<string, Role> = JSON.parse(fs.readFileSync(STEPS_PATH, 'utf-8'));

/** Every i18n key prefix the tour references, with a label for failure output. */
const referencedKeys = (): Array<[string, string]> => {
  const out: Array<[string, string]> = [];
  for (const [role, blocks] of Object.entries(steps)) {
    blocks.core.forEach((s) => out.push([`${role}/core step ${s.step}`, s.i18n_key]));
    blocks.tracks.forEach((tr) => {
      out.push([`${role}/track ${tr.id}`, tr.i18n_key]);
      tr.steps.forEach((s) => out.push([`${role}/track ${tr.id} step ${s.step}`, s.i18n_key]));
    });
  }
  return out;
};

const resolve = (bundle: Record<string, unknown>, dotted: string): unknown =>
  dotted.split('.').reduce<unknown>(
    (node, part) =>
      node && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined,
    bundle,
  );

/**
 * Locales the tour is expected to be complete in — all four, since this
 * branch ships fr/it for its own keys the way every other feature ticket
 * does. Keeping the list here rather than deriving it is deliberate: adding a
 * language must be a decision, and until then a partially translated locale
 * should fall back rather than fail the build.
 *
 * Note this is stricter than the repo-wide `i18n-keys.test.ts`, which still
 * excludes fr/it because a broader, pre-existing translation gap remains
 * there (unrelated to this feature — see that file's own comment for the
 * current scope). The tour is simply already complete, so it can be held to
 * the higher bar now.
 */
const LOCALES_WITH_TOUR = ['de', 'en', 'fr', 'it'];

describe('Onboarding-Tour: Schlüssel und Übersetzungen passen zusammen', () => {
  it('vergibt für jeden Schritt und jede Vertiefung einen i18n_key', () => {
    const missing = referencedKeys().filter(([, key]) => !key);
    expect(missing).toEqual([]);
    expect(referencedKeys().length).toBeGreaterThan(0);
  });

  it('verwendet jeden i18n_key nur einmal', () => {
    const keys = referencedKeys().map(([, key]) => key);
    const duplicates = keys.filter((k, i) => keys.indexOf(k) !== i);
    expect(duplicates).toEqual([]);
  });

  it.each(LOCALES_WITH_TOUR)('löst in %s jeden Titel und Text auf', (locale) => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const bundle = require(`../../../locales/${locale}/translation.json`);
    const unresolved: string[] = [];

    for (const [label, key] of referencedKeys()) {
      for (const field of ['title', 'description']) {
        const value = resolve(bundle, `${key}.${field}`);
        if (typeof value !== 'string' || value.trim() === '') {
          unresolved.push(`${label} -> ${key}.${field}`);
        }
      }
    }

    expect(unresolved).toEqual([]);
  });

  /**
   * The whole `help.*` namespace, not a hand-picked list of controls.
   *
   * The first version of this test enumerated five control keys by hand and
   * passed while «Tour beenden?» — `help.onboarding.confirmEndTitle` — was
   * still German in fr/it, because it was not on the list. A user found it.
   * Deriving the set from the German bundle removes the possibility: anything
   * the help surface can show has to exist in every locale the tour claims.
   */
  it.each(LOCALES_WITH_TOUR)('übersetzt in %s den ganzen help-Namensraum', (locale) => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const de = require('../../../locales/de/translation.json');
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const bundle = require(`../../../locales/${locale}/translation.json`);

    const helpKeys: string[] = [];
    const walk = (node: unknown, prefix: string) => {
      if (node && typeof node === 'object') {
        for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
          walk(v, prefix ? `${prefix}.${k}` : k);
        }
      } else if (typeof node === 'string' && prefix.startsWith('help.')) {
        helpKeys.push(prefix);
      }
    };
    walk(de, '');

    expect(helpKeys.length).toBeGreaterThan(100);
    const missing = helpKeys.filter((k) => typeof resolve(bundle, k) !== 'string');
    expect(missing).toEqual([]);
  });
});
