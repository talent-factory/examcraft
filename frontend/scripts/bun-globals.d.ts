/**
 * check-i18n-keys.ts uses `import.meta.dir` and `import.meta.main`, which
 * Bun adds to `ImportMeta` but the DOM/node lib types don't know about.
 *
 * A full `@types/bun` devDependency was tried and reverted: TypeScript
 * applies every `@types/*` package under a reachable `node_modules`
 * ambiently, project-wide — not just to the files that need it. `@types/bun`
 * redeclares the global `fetch` (adding `preconnect`, among others), which
 * broke premium/frontend's and enterprise/frontend's typecheck: both share
 * this package's node_modules (see their tsconfig.json `typeRoots`), and
 * their fetch mocks (e.g. ChatService.test.ts) aren't shaped to satisfy it.
 *
 * This file only adds the two properties actually used here, so it can't
 * leak into unrelated code the way the full package did.
 */
export {};

declare global {
  interface ImportMeta {
    readonly dir: string;
    readonly main: boolean;
  }
}
