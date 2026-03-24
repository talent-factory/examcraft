# ExamCraft AI - Proof of Concept Files

**Zweck:** Diese Dateien dienen als Proof-of-Concept für die Migration zu NPM Workspace (Option 5).

## 📁 Dateien

### 1. `root-package.json`
**Verwendung:** Root-Level package.json für NPM Workspace
**Kopieren nach:** `package.json` (Repository Root)

**Features:**
- Definiert Workspaces für alle Packages
- Gemeinsame Scripts für Build/Test/Lint
- Shared DevDependencies

**Installation:**
```bash
cp docs/architecture/poc/root-package.json package.json
npm install
```

---

### 2. `core-package.json`
**Verwendung:** Core Package Konfiguration
**Kopieren nach:** `packages/core/frontend/package.json`

**Features:**
- NPM Package Exports für types, services, components
- Build-Scripts für Library-Output
- Publishable zu NPM Registry

**Installation:**
```bash
cp docs/architecture/poc/core-package.json packages/core/frontend/package.json
cd packages/core/frontend
npm install
```

---

### 3. `premium-package.json`
**Verwendung:** Premium Package Konfiguration
**Kopieren nach:** `packages/premium/frontend/package.json`

**Features:**
- Dependency auf `@examcraft/core` (workspace)
- Private Package (nicht publishable)

**Installation:**
```bash
cp docs/architecture/poc/premium-package.json packages/premium/frontend/package.json
cd packages/premium/frontend
npm install
```

---

### 4. `enterprise-package.json`
**Verwendung:** Enterprise Package Konfiguration
**Kopieren nach:** `packages/enterprise/frontend/package.json`

**Features:**
- Dependencies auf `@examcraft/core` und `@examcraft/premium`
- Private Package (nicht publishable)

**Installation:**
```bash
cp docs/architecture/poc/enterprise-package.json packages/enterprise/frontend/package.json
cd packages/enterprise/frontend
npm install
```

---

### 5. `tsconfig.core.json`
**Verwendung:** TypeScript Konfiguration für Core Library
**Kopieren nach:** `packages/core/frontend/tsconfig.json`

**Features:**
- Declaration Files generieren (.d.ts)
- Source Maps für Debugging
- Strict Type Checking

**Installation:**
```bash
cp docs/architecture/poc/tsconfig.core.json packages/core/frontend/tsconfig.json
```

---

### 6. `rollup.config.js`
**Verwendung:** Build-System für Core Library
**Kopieren nach:** `packages/core/frontend/rollup.config.js`

**Features:**
- Multi-Entry Build (types, services, components)
- CommonJS + ESM Output
- External Dependencies (React, etc.)

**Installation:**
```bash
cp docs/architecture/poc/rollup.config.js packages/core/frontend/rollup.config.js
cd packages/core/frontend
npm install --save-dev rollup @rollup/plugin-typescript @rollup/plugin-node-resolve @rollup/plugin-commonjs
```

---

### 7. `migrate-imports.sh`
**Verwendung:** Automatische Import-Migration
**Ausführen:** `./docs/architecture/poc/migrate-imports.sh <directory>`

**Features:**
- Migriert `../core/types/X` → `@examcraft/core/types/X`
- Migriert `../core/services/X` → `@examcraft/core/services/X`
- Migriert `../core/components/X` → `@examcraft/core/components/X`
- Erstellt Backups vor Änderungen

**Verwendung:**
```bash
# Premium migrieren
./docs/architecture/poc/migrate-imports.sh packages/premium/frontend/src

# Enterprise migrieren
./docs/architecture/poc/migrate-imports.sh packages/enterprise/frontend/src
```

---

### 8. `core-index.ts`
**Verwendung:** Entry Point für Core Package
**Kopieren nach:** `packages/core/frontend/src/index.ts`

**Features:**
- Exportiert alle Public APIs
- Strukturierte Exports (types, services, components)
- Dokumentation für jede Export-Kategorie

**Installation:**
```bash
cp docs/architecture/poc/core-index.ts packages/core/frontend/src/index.ts
```

---

## 🚀 Quick Start

### Schritt 1: NPM Workspace Setup
```bash
# Root package.json kopieren
cp docs/architecture/poc/root-package.json package.json

# Dependencies installieren
npm install
```

### Schritt 2: Core Package konfigurieren
```bash
# Core package.json kopieren
cp docs/architecture/poc/core-package.json packages/core/frontend/package.json

# TypeScript Config kopieren
cp docs/architecture/poc/tsconfig.core.json packages/core/frontend/tsconfig.json

# Rollup Config kopieren
cp docs/architecture/poc/rollup.config.js packages/core/frontend/rollup.config.js

# Entry Point kopieren
cp docs/architecture/poc/core-index.ts packages/core/frontend/src/index.ts

# Core Dependencies installieren
cd packages/core/frontend
npm install
```

### Schritt 3: Premium Package migrieren
```bash
# Premium package.json kopieren
cp docs/architecture/poc/premium-package.json packages/premium/frontend/package.json

# Imports migrieren
./docs/architecture/poc/migrate-imports.sh packages/premium/frontend/src

# core/ Verzeichnis entfernen
rm -rf packages/premium/frontend/src/core

# Premium Dependencies installieren
cd packages/premium/frontend
npm install
```

### Schritt 4: Enterprise Package migrieren
```bash
# Enterprise package.json kopieren
cp docs/architecture/poc/enterprise-package.json packages/enterprise/frontend/package.json

# Imports migrieren
./docs/architecture/poc/migrate-imports.sh packages/enterprise/frontend/src

# core/ Verzeichnis entfernen
rm -rf packages/enterprise/frontend/src/core

# Enterprise Dependencies installieren
cd packages/enterprise/frontend
npm install
```

### Schritt 5: Build & Test
```bash
# Im Repository Root
npm run build:all
npm run test:all
```

## ✅ Verification

Nach der Migration sollten folgende Checks erfolgreich sein:

```bash
# TypeScript Compilation
npm run build:all

# Tests
npm run test:all

# Linting
npm run lint

# Import Validation
./scripts/validate-imports.sh
```

## 🔗 Referenzen

- **Migrations-Plan**: `docs/architecture/MIGRATION_PLAN_OPTION5.md`
- **Architektur-Analyse**: `docs/architecture/ARCHITECTURE_ANALYSIS_2025.md`
- **OpenSource-Empfehlung**: `docs/architecture/OPENSOURCE_ARCHITECTURE_RECOMMENDATION.md`
