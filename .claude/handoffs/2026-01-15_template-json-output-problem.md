# Handoff: Template JSON Output Problem

**Datum**: 2026-01-15
**Branch**: `feature/prompt-use-case-dropdown`
**Status**: Teilweise gelöst, PRD erstellt

---

## Original-Aufgabe

Der Benutzer berichtete, dass bei der Prüfungsgenerierung das falsche (oder kein) Template verwendet wird. Das ausgewählte Template `question_generator_academic` sollte verwendet werden, um Prüfungsfragen zum Thema "Quicksort vs MergeSort" zu generieren.

---

## Bereits erledigt

### 1. Import-Problem in `rag_exams.py` behoben

**Problem**: Der direkte Import `from services.rag_service import rag_service` band die Variable an den Core Placeholder, bevor der Premium-Service ersetzt werden konnte.

**Lösung**: Geändert zu Modul-Import:
```python
# VORHER (falsch)
from services.rag_service import rag_service

# NACHHER (korrekt)
import services.rag_service as rag_service_module
# Verwendung: rag_service_module.rag_service.generate_rag_exam(...)
```

**Datei**: `packages/core/backend/api/rag_exams.py` (Zeilen 12-16, 194, 271, 438, 459)

### 2. Doppelte Parser-Methode entfernt

**Problem**: Es gab zwei `_parse_claude_response()` Funktionen in `claude_service.py`, wobei die zweite die erste überschrieb und ein anderes JSON-Format erwartete.

**Lösung**: Duplikat entfernt, erste Methode mit Multi-Format-Support erweitert:
- JSON-Objekt mit `"questions"` Key
- JSON-Array direkt
- JSON in Markdown Code-Blöcken

**Datei**: `packages/core/backend/services/claude_service.py` (Zeilen 399-467)

### 3. API Timeout erhöht

**Problem**: 30 Sekunden Timeout reichte nicht für große Prompts mit Dokumentkontext.

**Lösung**:
```python
self.request_timeout = float(os.getenv("CLAUDE_REQUEST_TIMEOUT", "120.0"))
```

**Datei**: `packages/core/backend/services/claude_service.py` (Zeile 35)

### 4. `{{ context }}` Variable in Template hinzugefügt

**Problem**: Das Template in der Datenbank hatte keinen `{{ context }}` Platzhalter, daher wurde der Dokumentinhalt nie eingefügt.

**Lösung**: Via Python-Script in der Datenbank aktualisiert.

### 5. Besseres Error-Handling im RAG Service

**Änderungen in** `packages/premium/backend/services/rag_service.py`:
- Prüfung auf `error` Feld in Claude Response
- Erkennung von Demo/Fallback-Fragen
- Exception wird propagiert statt Fallback-Fragen zu generieren

### 6. Verbessertes Error-Logging

**Änderungen in** `packages/core/backend/services/claude_service.py`:
- Exception-Typ wird geloggt
- Full Traceback bei Fehlern
- API-Key-Status beim Start (maskiert)

---

## Gescheiterte Versuche

### 1. Template mit JSON-Instruktionen am Ende

**Versuch**: JSON-Output-Anweisung am Ende des Templates hinzugefügt.

**Ergebnis**: Claude ignorierte die Anweisung und gab weiterhin Markdown aus.

**Log-Beispiel**:
```
ERROR: No valid JSON found in Claude response. Content preview:
# Aufgabe 1 | QuickSort Rekursionseliminierung | 18 Punkte
## Kontext
QuickSort kann durch die Eliminierung der Rekursion optimiert werden...
```

**Erkenntnis**: Die Frage war **inhaltlich korrekt**, nur das Format war falsch.

### 2. Template komplett auf JSON umgestellt

**Versuch**: Template gekürzt und mit starker JSON-Betonung am Anfang umgeschrieben.

**Ergebnis**: Funktioniert teilweise - Claude gibt jetzt manchmal JSON aus, aber nicht zuverlässig.

**Problem**: Anwender sollten Templates in natürlichem Markdown schreiben können, ohne JSON-Kenntnisse.

---

## Aktueller Zustand

### Git Status

```
Branch: feature/prompt-use-case-dropdown

Modified (uncommitted):
- packages/core/backend/services/claude_service.py (Timeout, Logging)
- packages/premium (Submodule - rag_service.py Änderungen)

New Files:
- demo/BWZ/ (Benutzer-Testdaten)
- docs/PRD-Template-JSON-Wrapper.md
```

### Datenbank-Zustand

Das Template `question_generator_academic` wurde in der Datenbank mehrfach modifiziert:
- `{{ context }}` Platzhalter hinzugefügt
- JSON-Output-Instruktionen hinzugefügt
- Stark gekürzte Version

**ACHTUNG**: Die Datenbank-Version weicht von der Datei `/demo/example_prompts/question_generator_academic.md` ab!

### Docker Services

```bash
docker compose --env-file .env -f docker-compose.full.yml ps
# Backend läuft mit:
# - Timeout: 120s
# - Premium RAG Service geladen
```

---

## Nächste Schritte (Priorisiert)

### 1. HIGH: Automatischen JSON-Wrapper implementieren

**Beschreibung**: Das System soll automatisch JSON-Output-Instruktionen zum Benutzer-Template hinzufügen.

**Datei**: `packages/premium/backend/services/rag_service.py`

**Implementierung**:
```python
def _wrap_template_with_json_instructions(self, user_prompt: str) -> str:
    json_wrapper = '''
## SYSTEM INSTRUCTION
You MUST respond ONLY with valid JSON:
{"questions": [{"id": "q1", "type": "...", "question": "...", ...}]}
START YOUR RESPONSE WITH ```json
---
'''
    return json_wrapper + user_prompt
```

**Aufruf in** `generate_question()` (ca. Zeile 448):
```python
# Nach dem Rendern des User-Templates
prompt = self._wrap_template_with_json_instructions(prompt)
```

### 2. MEDIUM: Template-Validierung beim Upload

**Beschreibung**: Warnung anzeigen wenn `{{ context }}` fehlt.

**Datei**: `packages/premium/backend/api/prompts.py` oder `packages/premium/backend/services/prompt_service.py`

### 3. MEDIUM: Datenbank-Template zurücksetzen

Das Template in der Datenbank sollte wieder dem Original entsprechen (ohne JSON-Instruktionen), da der JSON-Wrapper systemseitig erfolgen soll.

```bash
# Template aus Datei in DB laden
docker compose exec backend python -c "
from database import SessionLocal
from premium.models.prompt import Prompt

db = SessionLocal()
prompt = db.query(Prompt).filter(Prompt.name == 'question_generator_academic').first()

with open('/app/demo/example_prompts/question_generator_academic.md', 'r') as f:
    content = f.read()
    # YAML Frontmatter entfernen
    if content.startswith('---'):
        parts = content.split('---', 2)
        prompt.content = parts[2].strip() if len(parts) > 2 else content

db.commit()
"
```

### 4. LOW: Änderungen committen

```bash
git add packages/core/backend/services/claude_service.py
git add docs/PRD-Template-JSON-Wrapper.md
git commit -m "fix(claude): Improve error handling and increase timeout

- Increase API timeout from 30s to 120s (configurable)
- Add detailed error logging with exception type
- Fix duplicate parser method
- Add PRD for automatic JSON wrapper feature"

cd packages/premium
git add backend/services/rag_service.py
git commit -m "fix(rag): Better error handling for Claude API responses

- Check for error field in response
- Detect demo/fallback questions
- Propagate errors instead of silent fallback"
```

---

## Wichtige Referenzen

### Dateien

| Datei | Beschreibung |
|-------|--------------|
| `packages/core/backend/services/claude_service.py` | Claude API Client mit Parser |
| `packages/premium/backend/services/rag_service.py` | RAG Service mit Prompt-Rendering |
| `packages/core/backend/api/rag_exams.py` | API Endpoint für Prüfungsgenerierung |
| `demo/example_prompts/question_generator_academic.md` | Referenz-Template (Benutzer-Format) |
| `docs/PRD-Template-JSON-Wrapper.md` | PRD für JSON-Wrapper Feature |

### Code-Patterns

**Modul-Import für dynamische Service-Ersetzung**:
```python
import services.rag_service as rag_service_module
# Verwendung: rag_service_module.rag_service.method()
```

**Template-Rendering mit Jinja2**:
```python
prompt = self.prompt_service.render_prompt_by_id(
    prompt_id=prompt_id,
    variables={"context": context_text, "topic": topic, ...},
    strict=False
)
```

---

## Für den nächsten Agent

**Zusammenfassung**: Die Prüfungsgenerierung funktioniert jetzt teilweise - Claude generiert korrekte Fragen, aber das Ausgabeformat (Markdown vs. JSON) ist noch nicht zuverlässig. Das Kernproblem ist, dass Anwender Templates in natürlichem Markdown schreiben sollen, aber das System JSON-Output braucht. **Lösung: Automatischer JSON-Wrapper im Backend** (siehe PRD).

**Starte mit**:
1. PRD lesen: `docs/PRD-Template-JSON-Wrapper.md`
2. `_wrap_template_with_json_instructions()` in `rag_service.py` implementieren
3. Template in Datenbank auf Original zurücksetzen

**Wichtig**: Die Änderungen in `claude_service.py` und `rag_service.py` sind noch nicht committet!
