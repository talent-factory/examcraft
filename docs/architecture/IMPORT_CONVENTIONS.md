# ExamCraft AI - Import-Konventionen

**Zuletzt aktualisiert:** 16. Januar 2025

## 📋 Übersicht

Dieses Dokument definiert die **verbindlichen Import-Konventionen** für das ExamCraft AI Projekt.

## 🎯 Grundregeln

### 1. Verwende IMMER relative Pfade innerhalb des gleichen Packages

```typescript
// ✅ RICHTIG - Innerhalb von Core
// Datei: packages/core/frontend/src/components/Dashboard.tsx
import { User } from '../types/auth';
import { AuthService } from '../services/AuthService';

// ✅ RICHTIG - Innerhalb von Premium
// Datei: packages/premium/frontend/src/components/RAGExamCreator.tsx
import { RAGExamDisplay } from './RAGExamDisplay';
```

### 2. Premium/Enterprise → Core Types/Services

```typescript
// ✅ RICHTIG - Premium importiert von eigenem core/
// Datei: packages/premium/frontend/src/components/RAGExamCreator.tsx
import { RAGExamResponse } from '../core/types/document';
import { DocumentService } from '../core/services/DocumentService';

// ❌ FALSCH - Verzeichnis existiert nicht!
import { RAGExamResponse } from '../../types/document';
```

### 3. Premium/Enterprise → Core Components (via @core)

```typescript
// ✅ RICHTIG - Verwende @core Alias
// Datei: packages/premium/frontend/src/components/prompts/PromptLibraryWithUpload.tsx
import { PromptLibrary } from '@core/components/admin/PromptLibrary';

// ❌ FALSCH - Verletzt CRA-Regeln!
import { PromptLibrary } from '../../../../core/frontend/src/components/admin/PromptLibrary';
```

## 📁 Verzeichnisstruktur

### Core Package
```
packages/core/frontend/src/
├── components/          → import { X } from '../components/Y'
├── types/              → import { X } from '../types/Y'
├── services/           → import { X } from '../services/Y'
├── contexts/           → import { X } from '../contexts/Y'
└── utils/              → import { X } from '../utils/Y'
```

### Premium Package
```
packages/premium/frontend/src/
├── components/          → import { X } from './Y'
├── core/               → import { X } from '../core/types/Y'
│   ├── types/          (Kopie von Core)
│   ├── services/       (Kopie von Core)
│   └── contexts/       (Kopie von Core)
├── api/                → import { X } from '../core/types/Y'
└── services/           → import { X } from '../core/types/Y'
```

### Enterprise Package
```
packages/enterprise/frontend/src/
├── components/          → import { X } from './Y'
└── core/               → import { X } from '../core/types/Y'
    ├── types/          (Kopie von Core)
    └── services/       (Kopie von Core)
```

## ✅ Korrekte Import-Beispiele

### Core → Core
```typescript
// Datei: packages/core/frontend/src/components/Dashboard.tsx
import { User, Role } from '../types/auth';
import { AuthService } from '../services/AuthService';
import { useAuth } from '../contexts/AuthContext';
import { formatDate } from '../utils/dateUtils';
```

### Premium → Premium Core
```typescript
// Datei: packages/premium/frontend/src/components/RAGExamCreator.tsx
import { RAGExamResponse, Document } from '../core/types/document';
import { RAGService } from '../core/services/RAGService';
import { PromptSelection } from '../core/types/prompt';
```

### Premium → Core Components (via @core)
```typescript
// Datei: packages/premium/frontend/src/components/prompts/PromptLibraryWithUpload.tsx
import { PromptLibrary } from '@core/components/admin/PromptLibrary';
import { PromptEditor } from '@core/components/admin/PromptEditor';
```

### Premium → Premium Components
```typescript
// Datei: packages/premium/frontend/src/components/RAGExamCreator.tsx
import RAGExamDisplay from './RAGExamDisplay';
import { PromptTemplateSelector } from './prompts';
```

## ❌ Häufige Fehler

### Fehler 1: Nicht-existierendes Verzeichnis
```typescript
// ❌ FALSCH - packages/premium/frontend/src/types/ existiert NICHT!
import { RAGExamResponse } from '../../types/document';

// ✅ RICHTIG
import { RAGExamResponse } from '../core/types/document';
```

### Fehler 2: Direkte Core-Imports
```typescript
// ❌ FALSCH - Verletzt CRA-Regeln!
import { PromptLibrary } from '../../../../core/frontend/src/components/admin/PromptLibrary';

// ✅ RICHTIG - Verwende @core Alias
import { PromptLibrary } from '@core/components/admin/PromptLibrary';
```

### Fehler 3: Falsche relative Pfade
```typescript
// ❌ FALSCH - Zu viele ../
import { User } from '../../../types/auth';

// ✅ RICHTIG - Prüfe die Verzeichnisstruktur
import { User } from '../core/types/auth';
```

## 🛠️ Validierung

### Automatische Prüfung
```bash
# Prüfe alle Import-Pfade
./scripts/validate-imports.sh
```

### Pre-Commit Hook (Empfohlen)
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: validate-imports
      name: Validate Import Paths
      entry: scripts/validate-imports.sh
      language: script
      pass_filenames: false
```

## 🔍 Troubleshooting

### Problem: "Cannot find module '../../types/document'"

**Ursache:** Falscher Import-Pfad in Premium/Enterprise Package

**Lösung:**
```typescript
// Ändere:
import { X } from '../../types/Y';

// Zu:
import { X } from '../core/types/Y';
```

### Problem: "Module not found outside src/"

**Ursache:** Direkter Import von Core Package (verletzt CRA-Regeln)

**Lösung:**
```typescript
// Ändere:
import { X } from '../../../../core/frontend/src/Y';

// Zu:
import { X } from '@core/Y';
```

## 📚 Weitere Ressourcen

- **Architektur-Analyse**: `docs/architecture/ARCHITECTURE_ANALYSIS_2025.md`
- **CRA Import Fix**: `CRA_IMPORT_FIX_SUMMARY.md`
- **Validierungs-Script**: `scripts/validate-imports.sh`
