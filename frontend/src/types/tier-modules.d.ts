// TF-626-Review: ambient declaration for the tier packages that
// `utils/componentLoader.tsx` loads exclusively via dynamic `import()`.
// At RUNTIME, CRACO (`craco.config.js`) resolves `@examcraft/premium` /
// `@examcraft/enterprise` via a Webpack alias to `../../premium/frontend/src`
// resp. `../../enterprise/frontend/src` — that stays unchanged.
//
// At TYPECHECK time (`tsconfig.typecheck.json`, `bun run typecheck`), the
// alias resolution is deliberately NOT part of the `paths` mapping anymore:
// `exclude` only prevents a folder from being scanned as an entry point, not
// an import actually resolved via `paths` from being pulled in transitively.
// With the full `@examcraft/premium` paths from `tsconfig.json`, `tsc` used
// to pull the entire premium/frontend tree into the core typecheck — its
// imports (react-i18next, @mui/material, ...) can't be resolved from
// core/frontend (no shared node_modules ancestor), resulting in dozens of
// `TS2307` errors that have nothing to do with core.
//
// The shorthand declaration below (no body) makes both specifiers resolve
// to `any` for the typechecker — exactly right for `componentLoader.tsx`,
// which only ever loosely accesses object properties anyway
// (`module.RAGExamCreator`, `module.PromptLibraryWithUpload`, ...) and
// needs no static type info from either tier.
declare module '@examcraft/premium';
declare module '@examcraft/enterprise';
