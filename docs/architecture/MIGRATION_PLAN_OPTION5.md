# ExamCraft AI - Migrations-Plan Option 5

**Datum:** 16. Januar 2025
**Ziel:** Migration zu NPM Workspace mit Core als Shared Base
**Aufwand:** 5-7 Tage (1 Entwickler Vollzeit)
**Risiko:** MITTEL

## 📋 Übersicht

### Ziel-Architektur

```
packages/
├── core/                        ✅ OpenSource (NPM Package)
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── types/           ← ALLE Types hier!
│   │   │   ├── services/        ← ALLE Services hier!
│   │   │   ├── components/      ← Core Components
│   │   │   ├── contexts/
│   │   │   └── utils/
│   │   ├── package.json         ← Publishable
│   │   └── tsconfig.json
│   └── backend/
│
├── premium/                     ❌ Closed Source
│   ├── frontend/
│   │   ├── src/
│   │   │   └── components/      ← NUR Premium Components
│   │   └── package.json
│   │       dependencies:
│   │         "@examcraft/core": "workspace:*"
│   └── backend/
│
└── enterprise/                  ❌ Closed Source
    ├── frontend/
    │   ├── src/
    │   │   └── components/      ← NUR Enterprise Components
    │   └── package.json
    │       dependencies:
    │         "@examcraft/core": "workspace:*"
    │         "@examcraft/premium": "workspace:*"
    └── backend/
```

### Vorteile nach Migration

- ✅ Keine Code-Duplizierung (core/ Verzeichnisse entfernt)
- ✅ Klare Import-Pfade (`@examcraft/core/types`)
- ✅ Perfekte OpenSource-Trennung
- ✅ Core als NPM Package nutzbar
- ✅ Keine wiederkehrenden Import-Fehler

## 🗓️ Migrations-Plan (7 Tage)

### Phase 1: Vorbereitung (Tag 1-2)

#### Tag 1: NPM Workspace Setup

**1.1 Root package.json erstellen**
```bash
# Im Repository-Root
touch package.json
```

**1.2 NPM Workspace konfigurieren**
- Siehe: `docs/architecture/poc/root-package.json`
- Workspaces definieren: core, premium, enterprise

**1.3 Core Package konfigurieren**
- `packages/core/frontend/package.json` anpassen
- Name: `@examcraft/core`
- Exports definieren für types, services, components

**1.4 TypeScript Path Aliases entfernen**
- Alte `@core/*` Aliases aus tsconfig.json entfernen
- Werden durch NPM Workspace ersetzt

**Deliverables:**
- ✅ Root package.json mit Workspaces
- ✅ Core package.json mit Exports
- ✅ NPM Workspace funktioniert (`npm install` im Root)

---

#### Tag 2: Core als Library vorbereiten

**2.1 Core Build-System konfigurieren**
- TypeScript Compiler für Library-Output
- Rollup/Vite für Bundle-Erstellung
- Source Maps generieren

**2.2 Core Exports definieren**
```typescript
// packages/core/frontend/src/index.ts
export * from './types';
export * from './services';
export * from './components';
export * from './contexts';
export * from './utils';
```

**2.3 Test-Build durchführen**
```bash
cd packages/core/frontend
npm run build
# Prüfe dist/ Verzeichnis
```

**Deliverables:**
- ✅ Core Build-System funktioniert
- ✅ dist/ Verzeichnis mit kompilierten Files
- ✅ Type Definitions (.d.ts) generiert

---

### Phase 2: Premium Migration (Tag 3-4)

#### Tag 3: Premium Imports umstellen

**3.1 Dependency hinzufügen**
```json
// packages/premium/frontend/package.json
{
  "dependencies": {
    "@examcraft/core": "workspace:*"
  }
}
```

**3.2 Imports automatisch umstellen**
```bash
# Script ausführen (siehe poc/migrate-imports.sh)
./scripts/migrate-imports.sh packages/premium/frontend/src
```

**3.3 Manuelle Prüfung**
- Alle `../core/types/X` → `@examcraft/core/types/X`
- Alle `../core/services/X` → `@examcraft/core/services/X`
- Alle `../core/components/X` → `@examcraft/core/components/X`

**3.4 Dupliziertes core/ Verzeichnis entfernen**
```bash
rm -rf packages/premium/frontend/src/core
```

**Deliverables:**
- ✅ Alle Premium Imports auf @examcraft/core umgestellt
- ✅ core/ Verzeichnis entfernt
- ✅ TypeScript Compilation erfolgreich

---

#### Tag 4: Premium Tests & Fixes

**4.1 Tests ausführen**
```bash
cd packages/premium/frontend
npm test
```

**4.2 Fehler beheben**
- Import-Pfade korrigieren
- Type-Errors fixen
- Test-Mocks anpassen

**4.3 Build testen**
```bash
npm run build
```

**Deliverables:**
- ✅ Alle Tests grün
- ✅ Build erfolgreich
- ✅ Keine TypeScript-Fehler

---

### Phase 3: Enterprise Migration (Tag 5)

#### Tag 5: Enterprise Imports umstellen

**5.1 Dependencies hinzufügen**
```json
// packages/enterprise/frontend/package.json
{
  "dependencies": {
    "@examcraft/core": "workspace:*",
    "@examcraft/premium": "workspace:*"
  }
}
```

**5.2 Imports umstellen**
```bash
./scripts/migrate-imports.sh packages/enterprise/frontend/src
```

**5.3 core/ Verzeichnis entfernen**
```bash
rm -rf packages/enterprise/frontend/src/core
```

**5.4 Tests & Build**
```bash
cd packages/enterprise/frontend
npm test
npm run build
```

**Deliverables:**
- ✅ Enterprise Imports umgestellt
- ✅ Tests grün
- ✅ Build erfolgreich

---

### Phase 4: Integration & Deployment (Tag 6-7)

#### Tag 6: Docker & CI/CD

**6.1 Docker-Images anpassen**
- `docker/Dockerfile.core` für OpenSource
- `docker/Dockerfile.full` für Full-Deployment
- Multi-Stage Build mit NPM Workspace

**6.2 docker-compose.yml aktualisieren**
- Volume Mounts anpassen
- Build-Context für Workspaces

**6.3 CI/CD Pipeline**
- GitHub Actions für Core Package
- NPM Publish Workflow
- Docker Build & Push

**Deliverables:**
- ✅ Docker-Images bauen erfolgreich
- ✅ docker-compose up funktioniert
- ✅ CI/CD Pipeline konfiguriert

---

#### Tag 7: Testing & Dokumentation

**7.1 End-to-End Tests**
- Core-only Deployment testen
- Full Deployment testen
- RBAC Feature-Zugriff prüfen

**7.2 Dokumentation aktualisieren**
- README.md für Core Package
- CONTRIBUTING.md
- Import-Konventionen aktualisieren

**7.3 Cleanup**
- Alte Dateien entfernen
- Git History aufräumen
- Release Notes erstellen

**Deliverables:**
- ✅ Alle Tests grün
- ✅ Dokumentation aktualisiert
- ✅ Migration abgeschlossen

## 📦 Proof-of-Concept Files

Alle PoC-Dateien befinden sich in `docs/architecture/poc/`:

1. `root-package.json` - NPM Workspace Konfiguration
2. `core-package.json` - Core Package mit Exports
3. `premium-package.json` - Premium Package Dependencies
4. `migrate-imports.sh` - Import-Migration Script
5. `tsconfig.core.json` - TypeScript Config für Core Library
6. `rollup.config.js` - Build-System für Core

## ⚠️ Risiken & Mitigation

### Risiko 1: Breaking Changes in Core
**Problem:** Änderungen an Core brechen Premium/Enterprise
**Mitigation:**
- Semantic Versioning für Core Package
- Deprecation Warnings vor Breaking Changes
- Comprehensive Tests vor Core-Releases

### Risiko 2: Build-Komplexität
**Problem:** Multi-Package Build kann komplex werden
**Mitigation:**
- Turborepo für Build-Orchestrierung
- Caching für schnellere Builds
- Klare Build-Reihenfolge dokumentieren

### Risiko 3: Import-Fehler während Migration
**Problem:** Vergessene Imports führen zu Runtime-Errors
**Mitigation:**
- Automatisches Migration-Script
- Comprehensive TypeScript Checks
- Manuelle Review aller geänderten Files

### Risiko 4: Docker Build-Zeit
**Problem:** NPM Workspace kann Build-Zeit erhöhen
**Mitigation:**
- Multi-Stage Docker Builds
- Layer Caching optimieren
- Nur geänderte Packages rebuilden

## ✅ Success Criteria

Migration ist erfolgreich, wenn:

1. ✅ Alle Tests grün (Backend + Frontend)
2. ✅ Core-only Deployment funktioniert
3. ✅ Full Deployment funktioniert
4. ✅ Keine Import-Fehler mehr
5. ✅ Build-Zeit < 5 Minuten
6. ✅ Docker-Images < 500MB
7. ✅ Core Package auf NPM veröffentlicht
8. ✅ Dokumentation vollständig

## 📊 Rollback-Plan

Falls Migration fehlschlägt:

1. **Git Revert** auf letzten stabilen Commit
2. **Docker-Images** auf vorherige Version zurücksetzen
3. **NPM Workspace** deaktivieren (package.json entfernen)
4. **Alte Struktur** wiederherstellen (core/ Verzeichnisse)

**Rollback-Zeit:** < 1 Stunde

## 🔗 Referenzen

- **Architektur-Analyse**: `docs/architecture/ARCHITECTURE_ANALYSIS_2025.md`
- **OpenSource-Empfehlung**: `docs/architecture/OPENSOURCE_ARCHITECTURE_RECOMMENDATION.md`
- **Import-Konventionen**: `docs/architecture/IMPORT_CONVENTIONS.md`
- **PoC Files**: `docs/architecture/poc/`
