# Lint-Checks VOR Pull Requests

## 🎯 Ziel

Stelle sicher, dass **alle** Lint-Fehler behoben sind, **bevor** du einen Pull Request erstellst.

## 🚀 Schnellstart

### 1. Automatische Checks bei jedem Commit (Empfohlen)

Pre-Commit-Hooks sind bereits konfiguriert und laufen automatisch:

```bash
# Einmalig: Pre-Commit-Hooks installieren
pre-commit install

# Jetzt laufen Checks automatisch bei jedem `git commit`
git commit -m "feat: Add new feature"
```

**Was wird geprüft:**
- ✅ Ruff Linter (Python)
- ✅ Ruff Formatter (Python)
- ✅ YAML/JSON/TOML Validation
- ✅ End-of-File Fixer
- ✅ Trailing Whitespace
- ✅ Secret Detection

### 2. Manuelle Checks vor PR

Führe diese Befehle aus, **bevor** du `/create-pr` aufrufst:

```bash
# Backend: Ruff Linter + Auto-Fix
cd packages/core/backend
ruff check . --fix
ruff format .

# Frontend: ESLint + Auto-Fix
cd packages/core/frontend
bun run lint:fix

# Alle Pre-Commit-Hooks manuell ausführen
pre-commit run --all-files
```

### 3. Integration in `/commit` Command

Der `/commit` Command führt bereits Pre-Commit-Hooks aus:

```bash
# Pre-Commit-Hooks laufen automatisch
/commit

# Falls Fehler auftreten, werden sie automatisch gefixt
# Du musst nur erneut committen
```

## 🔧 Häufige Ruff-Fehler beheben

### F401: Unused Import

**Fehler:**
```python
from fastapi import Depends  # F401: imported but unused
```

**Fix:**
```bash
ruff check . --fix  # Entfernt automatisch
```

### F541: f-string ohne Platzhalter

**Fehler:**
```python
print(f"Hello World")  # F541: f-string without placeholders
```

**Fix:**
```python
print("Hello World")  # Entferne f-Präfix
```

### F841: Ungenutzte Variable

**Fehler:**
```python
result = some_function()  # F841: assigned but never used
```

**Fix:**
```python
some_function()  # Entferne Zuweisung
# ODER
_ = some_function()  # Explizit ignorieren
```

## 📋 Workflow-Integration

### Option 1: Pre-Commit-Hooks (Automatisch)

```bash
# Einmalig installieren
pre-commit install

# Jetzt bei jedem Commit:
git add .
git commit -m "feat: Add feature"
# → Pre-Commit-Hooks laufen automatisch
# → Fehler werden gefixt
# → Du musst erneut stagen und committen
```

### Option 2: Manuell vor jedem PR

```bash
# 1. Alle Änderungen committen
/commit

# 2. Lint-Checks ausführen
cd packages/core/backend && ruff check . --fix && ruff format .
cd packages/core/frontend && bun run lint:fix

# 3. Fixes committen
git add -A
git commit -m "style: Fix lint errors"

# 4. PR erstellen
/create-pr
```

### Option 3: GitHub Actions (Automatisch bei Push)

GitHub Actions führt Lint-Checks automatisch aus:

```yaml
# .github/workflows/ci-cd.yml (bereits konfiguriert)
- name: Lint Backend with Ruff
  run: |
    ruff check .
    ruff format --check .
```

**Vorteil:** Fehler werden im PR angezeigt
**Nachteil:** Erst nach Push sichtbar

## 🎯 Best Practices

### 1. Pre-Commit-Hooks aktivieren

```bash
# Einmalig pro Repository
pre-commit install

# Testen
pre-commit run --all-files
```

### 2. Vor jedem PR: Manuelle Checks

```bash
# Backend
cd packages/core/backend
ruff check . --fix
ruff format .

# Frontend
cd packages/core/frontend
bun run lint:fix

# Alle Checks
pre-commit run --all-files
```

### 3. CI/CD-Pipeline beobachten

Nach dem Push:
1. Gehe zu GitHub Actions
2. Prüfe "ExamCraft CI/CD Pipeline"
3. Behebe Fehler falls vorhanden

## 🔍 Troubleshooting

### Pre-Commit-Hooks laufen nicht

```bash
# Neu installieren
pre-commit uninstall
pre-commit install

# Cache löschen
pre-commit clean
pre-commit run --all-files
```

### Ruff findet keine Fehler lokal, aber in CI

```bash
# Gleiche Ruff-Version wie CI verwenden
pip install ruff==0.14.3

# Alle Dateien prüfen (nicht nur staged)
ruff check packages/core/backend --fix
```

### ESLint-Fehler im Frontend

```bash
cd packages/core/frontend

# Auto-Fix
bun run lint:fix

# Nur prüfen
bun run lint
```

## 📚 Weitere Ressourcen

- [Pre-Commit Documentation](https://pre-commit.com/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [ESLint Documentation](https://eslint.org/)
