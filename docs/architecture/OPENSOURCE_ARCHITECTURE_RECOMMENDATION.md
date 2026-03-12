# ExamCraft AI - OpenSource-Architektur Empfehlung

**Datum:** 16. Januar 2025
**Fokus:** OpenSource + Commercial Mix

## 🎯 Ihre Anforderung

> "Wichtig ist einfach zu berücksichtigen, dass 'core' in der OpenSource erscheint und 'premium' und 'enterprise' nicht."

## ✅ Empfohlene Lösung: Option 5 - NPM Workspace mit Core als Shared Base

### Konzept

**Core Package = OpenSource Base**
- Enthält ALLE gemeinsamen Types, Services, Components
- Wird als NPM Package veröffentlicht
- Premium/Enterprise importieren von Core

**Premium/Enterprise = Private Plugins**
- Nur eigene Components
- Importieren von `@examcraft/core`
- Bleiben privat im Repository

### Architektur-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│                     OpenSource Release                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  @examcraft/core (NPM Package)                         │ │
│  │  ├── types/        (User, Role, Document, etc.)        │ │
│  │  ├── services/     (AuthService, DocumentService)      │ │
│  │  ├── components/   (Button, Card, Layout)              │ │
│  │  ├── contexts/     (AuthContext)                       │ │
│  │  └── utils/        (formatDate, etc.)                  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Private Repository                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  @examcraft/premium (Private)                          │ │
│  │  ├── components/   (RAGExamCreator, DocumentChat)      │ │
│  │  └── dependencies: "@examcraft/core": "workspace:*"    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  @examcraft/enterprise (Private)                       │ │
│  │  ├── components/   (SSOConfig, CustomBranding)         │ │
│  │  └── dependencies:                                     │ │
│  │      "@examcraft/core": "workspace:*"                  │ │
│  │      "@examcraft/premium": "workspace:*"               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Verzeichnisstruktur

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
├── premium/                     ❌ Closed Source (Privat)
│   ├── frontend/
│   │   ├── src/
│   │   │   └── components/      ← NUR Premium Components
│   │   └── package.json
│   │       dependencies:
│   │         "@examcraft/core": "workspace:*"
│   └── backend/
│
└── enterprise/                  ❌ Closed Source (Privat)
    ├── frontend/
    │   ├── src/
    │   │   └── components/      ← NUR Enterprise Components
    │   └── package.json
    │       dependencies:
    │         "@examcraft/core": "workspace:*"
    │         "@examcraft/premium": "workspace:*"
    └── backend/
```

### Import-Beispiele

**Core (OpenSource):**
```typescript
// Datei: packages/core/frontend/src/components/Dashboard.tsx
import { User } from '../types/auth';
import { AuthService } from '../services/AuthService';
```

**Premium (Private):**
```typescript
// Datei: packages/premium/frontend/src/components/RAGExamCreator.tsx
import { User, Document } from '@examcraft/core/types';
import { DocumentService } from '@examcraft/core/services';
import { Button, Card } from '@examcraft/core/components';

// Premium eigene Components
import RAGExamDisplay from './RAGExamDisplay';
```

**Enterprise (Private):**
```typescript
// Datei: packages/enterprise/frontend/src/components/SSOConfig.tsx
import { User } from '@examcraft/core/types';
import { AuthService } from '@examcraft/core/services';
import { RAGExamCreator } from '@examcraft/premium/components';

// Enterprise eigene Components
import { SSOProvider } from './SSOProvider';
```

### OpenSource-Release Workflow

**1. Core Package veröffentlichen:**
```bash
cd packages/core/frontend
npm publish --access public
```

**2. GitHub Repository:**
```
examcraft-core/          ← Public Repository
├── packages/core/       ← Nur Core Package
├── README.md
├── LICENSE (MIT)
└── CONTRIBUTING.md

examcraft-full/          ← Private Repository
├── packages/
│   ├── core/            ← Git Submodule → examcraft-core
│   ├── premium/
│   └── enterprise/
```

**3. Docker Images:**
```bash
# OpenSource Image (nur Core)
docker build -f packages/core/frontend/Dockerfile -t examcraft/core:latest

# Full Image (Core + Premium + Enterprise)
docker build -f docker/Dockerfile.full -t examcraft/full:latest
```

### Vorteile für OpenSource

✅ **Perfekte Code-Trennung**
- Core = 100% OpenSource
- Premium/Enterprise = 100% Privat
- Keine gemischten Dateien

✅ **Keine Code-Duplizierung**
- Premium/Enterprise haben KEIN eigenes `core/` Verzeichnis mehr
- Importieren direkt von `@examcraft/core`

✅ **Klare Import-Pfade**
- `@examcraft/core/types` statt `../core/types`
- Keine Verwirrung mehr

✅ **Core als NPM Package nutzbar**
- Andere Projekte können Core verwenden
- Community kann eigene Plugins bauen

✅ **Einfaches Deployment**
- OpenSource: Nur Core deployen
- Full: Alle Packages deployen
- RBAC steuert Feature-Zugriff

### Migration (5-7 Tage)

**Woche 1:**
- Core als NPM Package konfigurieren
- Build-System für Library-Output
- NPM Workspace Setup

**Woche 2:**
- Premium/Enterprise migrieren
- Imports auf `@examcraft/core` umstellen
- Duplizierte `core/` Verzeichnisse entfernen

**Woche 3:**
- Tests anpassen
- Docker-Images aktualisieren
- OpenSource-Release vorbereiten

## 🆚 Vergleich mit anderen Optionen

| Kriterium | Aktuell | Option 5 |
|-----------|---------|----------|
| OpenSource-Trennung | ❌ Komplex | ✅ Perfekt |
| Code-Duplizierung | ❌ Ja (`core/` in Premium/Enterprise) | ✅ Keine |
| Import-Pfade | ❌ Verwirrend (3 Muster) | ✅ Klar (`@examcraft/core`) |
| Premium-Code privat | ✅ Ja | ✅ Ja |
| Wartbarkeit | ❌ Schwierig | ✅ Einfach |

## ✅ Fazit

**Option 5 ist die beste Lösung für Ihre Anforderung:**
- ✅ Core erscheint in OpenSource
- ✅ Premium/Enterprise erscheinen NICHT in OpenSource
- ✅ Keine Code-Duplizierung
- ✅ Klare Architektur
- ✅ Zukunftssicher
