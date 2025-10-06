# ExamCraft AI - Testing & Quality Assurance

## 🎯 Übersicht

Dieses Dokument beschreibt das Testing-Setup für ExamCraft AI, das **Import-Fehler und ähnliche Probleme vor Commits verhindert**.

## 🛡️ Automatische Qualitätssicherung

### 1. Pre-Commit Hooks (Lokal)

**Installation:**

```bash
# Pre-commit installieren
pip install pre-commit

# Hooks aktivieren
pre-commit install

# Optional: Hooks für pre-push
pre-commit install --hook-type pre-push
```

**Was wird geprüft:**

- ✅ **Python Imports** - Alle Imports funktionieren
- ✅ **Requirements Validation** - Keine fehlenden Dependencies
- ✅ **Code Formatting** - Black, isort, ruff
- ✅ **Security** - Bandit Security Scan
- ✅ **YAML/JSON Syntax** - Konfigurationsdateien
- ✅ **Backend Tests** - Pytest Suite
- ✅ **TypeScript Linting** - ESLint

**Manuell ausführen:**

```bash
# Alle Checks
pre-commit run --all-files

# Nur Import-Check
python scripts/check_imports.py

# Nur Requirements-Check
python scripts/validate_requirements.py

# Nur Tests
cd backend && pytest tests/ -v
```

### 2. GitLab CI/CD Pipeline

**Automatisch bei jedem Push:**

```yaml
Stages:
  1. Validate  → Import-Check, Requirements, YAML
  2. Test      → Backend Tests, Frontend Tests
  3. Build     → Docker Images
  4. Deploy    → Render.com (manuell)
```

**Pipeline-Status:**

```
https://gitlab.com/talent-factory/software/examcraft/-/pipelines
```

## 📝 Test-Kategorien

### Import Tests

**Datei:** `backend/tests/test_imports.py`

**Prüft:**
- ✅ Kritische Dependencies (numpy, fastapi, pydantic)
- ✅ Service-Module (vector_service, qdrant_vector_service)
- ✅ API-Module (documents, vector_search, rag_exams)
- ✅ Haupt-Application (main.py)
- ✅ Numpy-Verfügbarkeit in Vector Services

**Ausführen:**

```bash
cd backend
pytest tests/test_imports.py -v
```

### Unit Tests

**Dateien:** `backend/tests/test_*.py`

**Ausführen:**

```bash
cd backend

# Alle Tests
pytest tests/ -v

# Mit Coverage
pytest tests/ -v --cov=. --cov-report=html

# Nur bestimmte Tests
pytest tests/test_api_documents.py -v
```

### Integration Tests

**Erfordert:**
- PostgreSQL
- Redis
- Qdrant (oder Mock)

**Ausführen:**

```bash
# Mit Docker Compose
docker-compose up -d postgres redis qdrant

# Tests ausführen
cd backend
pytest tests/ -v --integration
```

## 🔍 Import-Check Details

### Was wird geprüft?

**Script:** `scripts/check_imports.py`

1. **Findet alle Python-Dateien** in `backend/` und `utils/`
2. **Versucht jede Datei zu importieren**
3. **Erkennt Fehler:**
   - `ImportError` - Fehlende Dependencies
   - `NameError` - Undefinierte Variablen (wie `np`)
   - Andere Syntax-Fehler

**Beispiel-Output:**

```
🔍 Checking Python Imports...

Found 45 Python files to check

✓ backend/main.py
✓ backend/api/documents.py
✗ backend/services/qdrant_vector_service.py
  • NameError in backend/services/qdrant_vector_service.py: name 'np' is not defined

❌ Import Check FAILED
Failed files: 1/45

💡 Fix these import errors before committing!
```

## 📦 Requirements Validation

### Was wird geprüft?

**Script:** `scripts/validate_requirements.py`

1. **Parse requirements.txt**
2. **Findet alle Imports im Code**
3. **Vergleicht:**
   - Fehlende Dependencies (im Code, aber nicht in requirements.txt)
   - Ungenutzte Dependencies (in requirements.txt, aber nicht im Code)

**Beispiel-Output:**

```
🔍 Validating requirements.txt...

📦 Found 35 packages in requirements.txt
📥 Found 28 third-party imports in code

❌ Missing Dependencies:
  • Import 'numpy' → Add 'numpy' to requirements.txt

⚠️  Potentially Unused Dependencies:
  • chromadb
  • sentence-transformers

💡 Consider removing unused packages to reduce build time
```

## 🚀 Best Practices

### Vor jedem Commit

```bash
# 1. Imports prüfen
python scripts/check_imports.py

# 2. Requirements validieren
python scripts/validate_requirements.py

# 3. Tests ausführen
cd backend && pytest tests/ -v

# 4. Pre-commit hooks (automatisch)
git commit -m "Your message"
```

### Neue Dependency hinzufügen

```bash
# 1. Zu requirements.txt hinzufügen
echo "new-package==1.0.0" >> backend/requirements.txt

# 2. Installieren
pip install -r backend/requirements.txt

# 3. Validieren
python scripts/validate_requirements.py

# 4. Import-Test
python scripts/check_imports.py

# 5. Commit
git add backend/requirements.txt
git commit -m "feat: Add new-package dependency"
```

### Dependency entfernen

```bash
# 1. Aus requirements.txt entfernen
# (Zeile löschen oder auskommentieren)

# 2. Prüfen, ob noch verwendet
python scripts/validate_requirements.py

# 3. Import-Check
python scripts/check_imports.py

# 4. Tests ausführen
cd backend && pytest tests/ -v

# 5. Commit
git commit -m "refactor: Remove unused dependency"
```

## 🐛 Häufige Probleme

### Problem: "NameError: name 'np' is not defined"

**Ursache:** numpy wird nur in try-block importiert

**Lösung:**

```python
# ❌ FALSCH:
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError:
    pass

# ✅ RICHTIG:
import numpy as np  # Immer importieren

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    pass
```

### Problem: "ModuleNotFoundError: No module named 'xyz'"

**Ursache:** Dependency fehlt in requirements.txt

**Lösung:**

```bash
# 1. Package hinzufügen
echo "xyz==1.0.0" >> backend/requirements.txt

# 2. Installieren
pip install xyz==1.0.0

# 3. Validieren
python scripts/validate_requirements.py
```

### Problem: Pre-commit Hook schlägt fehl

**Ursache:** Code-Qualitätsprobleme

**Lösung:**

```bash
# 1. Fehler anzeigen
pre-commit run --all-files

# 2. Auto-Fix (wenn möglich)
pre-commit run --all-files --hook-stage manual

# 3. Manuell beheben
# (Fehler in Output anschauen)

# 4. Erneut versuchen
git commit -m "Your message"
```

## 📊 CI/CD Pipeline

### Pipeline-Stages

**1. Validate (schnell, ~1 Min)**
- Import-Check
- Requirements-Validation
- YAML-Syntax

**2. Test (~3-5 Min)**
- Backend Unit Tests
- Frontend Tests
- Coverage Reports

**3. Build (~5-10 Min)**
- Docker Images
- Push zu Registry

**4. Deploy (manuell)**
- Staging: develop Branch
- Production: main Branch

### Pipeline-Konfiguration

**Datei:** `.gitlab-ci.yml`

**Wichtige Variablen:**

```yaml
variables:
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "18"
  RENDER_SERVICE_ID: "srv-xxx"  # In GitLab CI/CD Settings
  RENDER_API_KEY: "rnd_xxx"     # In GitLab CI/CD Settings
```

### Pipeline-Status prüfen

```bash
# In GitLab UI:
https://gitlab.com/talent-factory/software/examcraft/-/pipelines

# Oder via CLI:
glab ci status
glab ci view
```

## 🎓 Zusammenfassung

### Was verhindert Fehler?

1. **Pre-Commit Hooks** → Lokale Prüfung vor Commit
2. **Import Tests** → Erkennt NameError, ImportError
3. **Requirements Validation** → Erkennt fehlende Dependencies
4. **CI/CD Pipeline** → Automatische Tests bei Push
5. **Unit Tests** → Funktionale Korrektheit

### Workflow

```
Code ändern
    ↓
Pre-commit Hook (lokal)
    ↓
Git Commit
    ↓
Git Push
    ↓
GitLab CI/CD Pipeline
    ↓
Deployment (manuell)
```

### Vorteile

- ✅ **Frühe Fehlererkennung** - Vor Commit, nicht erst im Deployment
- ✅ **Schnelles Feedback** - Lokale Checks in Sekunden
- ✅ **Automatisierung** - Keine manuellen Checks nötig
- ✅ **Konsistenz** - Gleiche Checks für alle Entwickler
- ✅ **Dokumentation** - Klare Fehlermeldungen

---

**Status**: ✅ Vollständig implementiert
**Letzte Aktualisierung**: 2025-10-06
**Verantwortlich**: TF-108 - Production Deployment

