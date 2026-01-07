# Handoff-Dokumentation für Context Reset

Erstelle eine umfassende Handoff-Dokumentation vor einem `/compact`, damit ein neuer Agent mit frischem Kontext nahtlos weiterarbeiten kann.

## 🎯 Zweck

Dieser Befehl wird **vor einem `/compact`** verwendet, um den aktuellen Arbeitsstand zu dokumentieren. Nach dem Compact kann ein neuer Agent diese Dokumentation laden und ohne Vorkenntnisse weiterarbeiten.

## 📋 Aufgabe

Du sollst eine vollständige Handoff-Dokumentation erstellen, die:

1. **Aufgabenkontext erfasst**:
   - Was ist die ursprüngliche Aufgabenstellung?
   - Welches Problem soll gelöst werden?
   - Warum ist diese Aufgabe wichtig?
   - Gibt es einen zugehörigen Linear Issue? (ID und Link)

2. **Bereits Erledigtes dokumentiert**:
   - Welche Schritte wurden bereits unternommen?
   - Welche Dateien wurden erstellt oder modifiziert?
   - Was hat funktioniert und warum?
   - Welche Lösungsansätze waren erfolgreich?

3. **Gescheiterte Versuche festhalten**:
   - Was wurde versucht, hat aber nicht funktioniert?
   - Welche Fehlermeldungen sind aufgetreten?
   - Warum wurden bestimmte Ansätze verworfen?
   - Was sollte vermieden werden?

4. **Aktuellen Zustand beschreiben**:
   - Git Status (Branch, uncommitted changes)
   - Laufende Services oder Prozesse
   - Wichtige Environment-Variablen
   - Abhängigkeiten oder externe Faktoren

5. **Nächste Schritte definieren**:
   - Was muss als Nächstes getan werden? (priorisierte Liste)
   - Welche Dateien müssen bearbeitet werden?
   - Welche Befehle müssen ausgeführt werden?
   - Welche Blocker gibt es?

6. **Wichtige Referenzen sammeln**:
   - Relevante Dateipfade mit Zeilennummern
   - Links zu Dokumentation
   - Ähnliche gelöste Probleme
   - Wichtige Code-Patterns im Projekt

## 🔧 Workflow

### Schritt 1: Informationen sammeln

```bash
# Git Status erfassen
git status
git diff --stat
git log -5 --oneline

# Aktuelle Branch
git branch --show-current

# Geänderte Dateien
git diff --name-only

# Laufende Prozesse
docker compose ps

# TODO/FIXME im Code finden
grep -r "TODO\|FIXME" --include="*.py" --include="*.ts" --include="*.tsx" .
```

### Schritt 2: Dokumentation strukturieren

Die Dokumentation sollte folgende Abschnitte enthalten:

```markdown
# Handoff: [Aufgaben-Titel]

**Datum**: [YYYY-MM-DD HH:MM]
**Branch**: [branch-name]
**Linear Issue**: [TF-XXX] - [Issue-Titel]

## 🎯 Original-Aufgabe

[Beschreibung der ursprünglichen Anforderung]

## ✅ Bereits erledigt

### Änderungen
- [Datei 1]: [Was wurde geändert]
- [Datei 2]: [Was wurde geändert]

### Erfolgreiche Ansätze
1. [Ansatz 1 mit Begründung]
2. [Ansatz 2 mit Begründung]

## ❌ Gescheiterte Versuche

### Versuch 1: [Beschreibung]
**Problem**: [Was ist schiefgelaufen]
**Fehlermeldung**:
```
[Relevante Fehlermeldung]
```
**Warum gescheitert**: [Analyse]

## 📍 Aktueller Zustand

### Git Status
```bash
[Output von git status]
```

### Modified Files
- `path/to/file1.py` - [Beschreibung der Änderungen]
- `path/to/file2.tsx` - [Beschreibung der Änderungen]

### Environment
- Services: [Welche laufen/nicht laufen]
- Database: [Status]
- Dependencies: [Relevante Pakete]

## 🚀 Nächste Schritte

### Priorität 1: [Titel]
**Was**: [Detaillierte Beschreibung]
**Wo**: `path/to/file.py:123`
**Wie**: [Konkrete Anleitung]

### Priorität 2: [Titel]
**Was**: [Detaillierte Beschreibung]
**Wo**: `path/to/file.tsx:45`
**Wie**: [Konkrete Anleitung]

## 🔍 Wichtige Referenzen

### Relevante Dateien
- `packages/core/backend/main.py:712` - [Warum relevant]
- `.env.example` - [Was beachten]

### Dokumentation
- [Link zu relevanter Doku]
- [Link zu ähnlichem gelöstem Problem]

### Code-Patterns
```python
# Beispiel eines wichtigen Patterns im Projekt
```

## ⚠️ Wichtige Hinweise

- [Warnung 1]
- [Warnung 2]
- [Besonderheit 3]

## 📝 Für den nächsten Agent

[Zusammenfassung in 2-3 Sätzen: Was muss der nächste Agent wissen, um sofort loszulegen?]
```

### Schritt 3: Dokumentation speichern

```bash
# Standard-Verzeichnis erstellen falls nicht vorhanden
mkdir -p .claude/handoffs

# Dateiname mit Timestamp
# Format: .claude/handoffs/YYYY-MM-DD_task-name.md
```

## 📁 Ausgabe-Verzeichnis

**Standard**: `.claude/handoffs/`

**Dateiname-Konvention**: `YYYY-MM-DD_[task-slug].md`

Beispiele:
- `.claude/handoffs/2026-01-07_system-prompt-extraction.md`
- `.claude/handoffs/2026-01-07_rbac-regression-fix.md`
- `.claude/handoffs/2026-01-07_deployment-setup.md`

## 🚀 Verwendung

### Basic Usage

```bash
# Mit automatischem Task-Namen (aus Git Branch)
/document-handoff

# Mit spezifischem Task-Namen
/document-handoff "System Prompt Extraction"

# Mit benutzerdefiniertem Ausgabeverzeichnis
/document-handoff --output "docs/handoffs"
```

### Workflow mit Compact

```bash
# 1. Handoff-Dokumentation erstellen
/document-handoff "Feature Implementation"

# 2. Context komprimieren
/compact

# 3. Neue Session: Dokumentation laden
# "Lies bitte .claude/handoffs/2026-01-07_feature-implementation.md
#  und arbeite an den nächsten Schritten weiter."
```

## 📋 Parameter

| Parameter | Beschreibung | Standard |
|-----------|-------------|----------|
| `task-name` | Name der Aufgabe (wird für Dateinamen verwendet) | Automatisch aus Git Branch |
| `--output` | Ausgabeverzeichnis | `.claude/handoffs/` |
| `--include-git-diff` | Git Diff in Dokumentation einbetten | `false` |
| `--scan-todos` | TODO/FIXME Kommentare scannen | `true` |
| `--linear-issue` | Linear Issue ID (z.B. TF-177) | Automatisch erkennen |

## 💡 Best Practices

### Vor dem Compact

- ✅ Alle wichtigen Änderungen committen oder dokumentieren
- ✅ Services-Status festhalten
- ✅ Offene Fragen explizit notieren
- ✅ Fehler-Logs beifügen
- ✅ Konkrete nächste Schritte definieren

### In der Dokumentation

- ✅ **Spezifisch sein**: "Zeile 123 in file.py ändern" statt "Code anpassen"
- ✅ **Kontext erklären**: Warum wurde etwas gemacht?
- ✅ **Fehler dokumentieren**: Was hat nicht funktioniert und warum?
- ✅ **Referenzen angeben**: Dateipfade mit Zeilennummern
- ✅ **Priorisieren**: Wichtigste nächste Schritte zuerst

### Für den nächsten Agent

- ✅ **Selbsterklärend**: Keine Vorkenntnisse erforderlich
- ✅ **Actionable**: Klare Handlungsanweisungen
- ✅ **Vollständig**: Alle relevanten Informationen
- ✅ **Strukturiert**: Einfach zu navigieren

## ⚠️ Wichtige Hinweise

1. **Vor Compact ausführen**: Diese Dokumentation ist nutzlos nach dem Compact, wenn sie nicht erstellt wurde!

2. **Git Branch**: Der Branch-Name wird für die automatische Task-Erkennung verwendet (z.B. `feature/TF-177-description` → Task: "TF-177-description")

3. **Keine Secrets**: Niemals API Keys, Passwörter oder Tokens in die Handoff-Dokumentation schreiben!

4. **Versionskontrolle**: Handoff-Dokumente können in Git committed werden (z.B. für Team-Übergaben)

5. **Aufräumen**: Alte Handoff-Dokumente regelmäßig archivieren oder löschen

## 📊 Beispiel-Output

### Minimale Dokumentation

```markdown
# Handoff: RBAC Regression Fix

**Datum**: 2026-01-07 15:30
**Branch**: feature/TF-177-rbac-regression-exam-creation
**Linear Issue**: TF-177

## 🎯 Original-Aufgabe
RAG Exam Creator zeigt "Premium Feature" Upgrade-Prompt trotz Full deployment.

## ✅ Bereits erledigt
- `.env.example` angepasst (DEPLOYMENT_MODE Variablen)
- `packages/core/backend/main.py` untersucht

## ❌ Gescheiterte Versuche
Versuch, über Environment Variables zu steuern → zu komplex

## 📍 Aktueller Zustand
Modified: .env.example, packages/core/backend/main.py (uncommitted)

## 🚀 Nächste Schritte
1. RBAC-Logik in `main.py:712` überprüfen
2. Frontend Premium Component Loading testen

## 📝 Für den nächsten Agent
Backend scheint korrekt konfiguriert. Problem liegt wahrscheinlich im Frontend Component Loading. Prüfe `packages/core/frontend/src/pages/Exams.tsx` auf Premium-Import-Logik.
```

## 🎓 Wann diesen Befehl verwenden?

### ✅ Verwenden wenn:
- Context wird zu groß und `/compact` ist nötig
- Übergabe an anderen Developer/Agent
- Komplexe Aufgabe muss unterbrochen werden
- Viele gescheiterte Versuche dokumentiert werden müssen
- Am Ende eines Arbeitstages für morgen

### ❌ Nicht verwenden wenn:
- Aufgabe ist in 5 Minuten fertig
- Keine relevanten Änderungen gemacht
- Nur Recherche, keine Implementierung
- Triviale Task ohne wichtigen Kontext

---

**Verwende diesen Befehl IMMER vor `/compact`, wenn du später nahtlos weiterarbeiten möchtest!**
