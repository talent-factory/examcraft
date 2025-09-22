---
description: Erstelle professionelle Git-Commits mit automatischen Checks für Java, Python und React Projekte
---

# Professional Git Commit Workflow

Dieser Workflow führt automatische Checks durch und erstellt professionelle Git-Commits nach den definierten Standards.

## Schritte

1. **Git Status prüfen**
```bash
git status
```

2. **Änderungen überprüfen**
```bash
git diff --cached
```

3. **Alle Änderungen hinzufügen (falls noch nicht geschehen)**
// turbo
```bash
git add .
```

4. **Commit mit strukturierter Message erstellen**

Format:
```
type: Kurze Beschreibung

Detaillierte Erklärung
- Änderung 1
- Änderung 2
- ...
- Änderung n
```

Verfügbare Types:
- `feat:` - Neue Features
- `fix:` - Bugfixes  
- `docs:` - Dokumentationsänderungen
- `chore:` - Wartungsarbeiten
- `refactor:` - Code-Refactoring
- `test:` - Test-bezogene Änderungen

5. **Commit durchführen**
```bash
git commit -m "commit_message"
```

6. **Optional: Push zu Remote**
```bash
git push
```
