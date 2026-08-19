// TF-626-Review: Ambient-Deklaration fuer die Tier-Pakete, die
// `utils/componentLoader.tsx` ausschliesslich per dynamischem `import()`
// laedt. Zur LAUFZEIT loest CRACO (`craco.config.js`) `@examcraft/premium` /
// `@examcraft/enterprise` per Webpack-Alias auf `../../premium/frontend/src`
// bzw. `../../enterprise/frontend/src` auf — das bleibt unveraendert.
//
// Zur TYPECHECK-Zeit (`tsconfig.typecheck.json`, `bun run typecheck`) ist die
// Alias-Aufloesung bewusst NICHT Teil des `paths`-Mappings mehr: `exclude`
// verhindert nur, dass ein Ordner als Einstiegspunkt gescannt wird, nicht
// aber, dass ein ueber `paths` real aufgeloester Import transitiv mitgezogen
// wird. Mit den vollen `@examcraft/premium`-Pfaden aus `tsconfig.json` zog
// `tsc` bislang den kompletten premium/frontend-Baum in den core-Typecheck —
// dessen Importe (react-i18next, @mui/material, ...) sind von core/frontend
// aus nicht aufloesbar (kein gemeinsamer node_modules-Vorfahre), Ergebnis:
// dutzende `TS2307`, die nichts mit core zu tun haben.
//
// Die Shorthand-Deklaration unten (kein Body) macht beide Spezifizierer fuer
// den Typechecker zu `any` — genau richtig fuer `componentLoader.tsx`, das
// ohnehin nur locker auf Objekt-Properties zugreift
// (`module.RAGExamCreator`, `module.PromptLibraryWithUpload`, ...) und keine
// statische Typinfo aus dem jeweils anderen Tier braucht.
declare module '@examcraft/premium';
declare module '@examcraft/enterprise';
