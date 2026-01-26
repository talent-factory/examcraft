# PRD: Automatische JSON-Konvertierung für Prompt-Templates

**Status**: Draft
**Erstellt**: 2026-01-15
**Autor**: Claude (Session mit Daniel)
**Priorität**: High

---

## Executive Summary

Anwender sollen Prompt-Templates in natürlichem Markdown-Format erstellen können, ohne sich um technische JSON-Formatierungsanforderungen kümmern zu müssen. Das System muss automatisch sicherstellen, dass Claude API-Antworten im korrekten JSON-Format zurückgegeben werden, indem es Templates vor dem API-Call mit JSON-Instruktionen umhüllt. Dies ermöglicht eine benutzerfreundliche Template-Erstellung bei gleichzeitiger technischer Kompatibilität.

---

## Problemstellung

### Aktueller Zustand

- Anwender erstellen Prompt-Templates wie `question_generator_academic.md` in natürlichem Markdown
- Das Template beschreibt die gewünschte Fragenstruktur (Kontext, Aufgabenstellung, Code-Grundgerüst, Musterlösung)
- Der RAG-Service injiziert `{{ context }}` mit Dokumentinhalten aus Qdrant
- Claude generiert Fragen basierend auf dem Template

### Problem

1. **Claude ignoriert implizite Formatierung**: Ohne explizite JSON-Anweisungen gibt Claude Markdown-formatierte Antworten zurück
2. **Parser erwartet JSON**: Der `_parse_claude_response()` Parser kann nur strukturiertes JSON verarbeiten
3. **Benutzerfreundlichkeit vs. Technik**: Anwender müssten komplexe JSON-Instruktionen in Templates einbauen, was:
   - Die Template-Erstellung verkompliziert
   - Fehleranfällig ist
   - Die Lesbarkeit der Templates verschlechtert
   - Technisches Wissen voraussetzt

### Auswirkungen

- **Session 2026-01-15**: Korrekt generierte Fragen (inhaltlich perfekt) wurden verworfen, weil sie als Markdown statt JSON formatiert waren
- Beispiel aus Logs:
  ```
  ERROR: No valid JSON found in Claude response. Content preview:
  # Aufgabe 1 | QuickSort Rekursionseliminierung | 18 Punkte
  ## Kontext
  QuickSort kann durch die Eliminierung der Rekursion optimiert werden...
  ```
- Die Frage war **inhaltlich korrekt und relevant**, wurde aber vom Parser abgelehnt

### Evidenz

| Metrik | Wert |
|--------|------|
| Erfolgreiche Claude API Calls | 100% |
| Korrekt formatierte Antworten | 0% (ohne JSON-Instruktionen) |
| Verworfene, inhaltlich korrekte Fragen | 100% |

---

## Ziele & Erfolgsmetriken

### Produktziele

1. **Benutzerfreundlichkeit**: Anwender schreiben Templates in natürlichem Markdown ohne JSON-Kenntnisse
2. **Technische Kompatibilität**: System stellt JSON-Output automatisch sicher
3. **Flexibilität**: Bestehende Templates funktionieren ohne Änderung

### Business-Ziele

1. Reduzierte Supportanfragen zu Template-Fehlern
2. Erhöhte Adoption der Prompt Library durch vereinfachte Template-Erstellung
3. Verbesserte User Experience für Dozenten ohne technischen Hintergrund

### Erfolgsmetriken

| Metrik | Baseline | Target |
|--------|----------|--------|
| Template-Erstellungszeit | 30+ min (mit JSON) | < 10 min (ohne JSON) |
| Parser-Erfolgsrate | 0% (Markdown-Templates) | > 95% |
| Template-Fehlerrate | Hoch (JSON-Syntaxfehler) | < 5% |
| Benutzer-Zufriedenheit | Niedrig | > 4/5 Sterne |

---

## User Stories & Personas

### Persona: Dozent (Prof. Dr. Müller)

- **Rolle**: Informatik-Dozent an Fachhochschule
- **Technisches Niveau**: Fachexperte, aber kein Entwickler
- **Ziel**: Prüfungsfragen aus Vorlesungsmaterial generieren
- **Frustration**: "Ich will nur beschreiben, WIE die Fragen aussehen sollen, nicht mich mit JSON herumschlagen"

### User Stories

#### US-1: Template in natürlicher Sprache erstellen

**Als** Dozent
**möchte ich** ein Prompt-Template in natürlichem Markdown schreiben
**damit** ich mich auf den Inhalt konzentrieren kann, nicht auf technische Formatierung

**Akzeptanzkriterien**:
- [ ] Template enthält keine JSON-Instruktionen
- [ ] Template beschreibt gewünschte Fragenstruktur in Markdown
- [ ] Template verwendet `{{ context }}`, `{{ topic }}`, `{{ difficulty }}` Variablen
- [ ] System generiert trotzdem korrekt formatierte JSON-Antworten

**Beispiel-Template** (aus `/demo/example_prompts/question_generator_academic.md`):
```markdown
# Prüfungsfragen-Generator für BSc Informatik

Du bist ein Experte für die Erstellung akademischer Prüfungsfragen.

## Aufgabe
Erstelle qualitativ hochwertige Prüfungsfragen basierend auf:
- **Thema**: {{ topic }}
- **Schwierigkeitsgrad**: {{ difficulty }}

## Akademisches Material
{{ context }}

## Ausgabeformat
Für jede Frage:
- Kontext und Hintergrund
- Aufgabenstellung
- Code-Grundgerüst (falls relevant)
- Bewertungskriterien
```

#### US-2: Fehlerfreie Prüfungsgenerierung

**Als** Dozent
**möchte ich** dass meine Prüfungsfragen ohne technische Fehler generiert werden
**damit** ich mich auf die inhaltliche Qualität konzentrieren kann

**Akzeptanzkriterien**:
- [ ] Keine "Fallback-Fragen" aufgrund von Parsing-Fehlern
- [ ] Klare Fehlermeldung wenn Claude API tatsächlich fehlschlägt
- [ ] Inhaltlich korrekte Fragen werden nicht verworfen

---

## Funktionale Anforderungen

### Must-Have (MVP)

#### FR-1: Automatischer JSON-Wrapper

**Beschreibung**: Das System fügt automatisch JSON-Output-Instruktionen zum Benutzer-Template hinzu, bevor es an Claude gesendet wird.

**Implementierung** (in `rag_service.py`):
```python
def _wrap_template_with_json_instructions(self, user_prompt: str) -> str:
    """
    Wraps user's natural language template with JSON output instructions.
    User templates remain clean Markdown without JSON requirements.
    """
    json_wrapper = '''
## SYSTEM INSTRUCTION (Auto-generated)

You MUST respond ONLY with valid JSON in this exact format:
```json
{
  "questions": [
    {
      "id": "q1",
      "type": "open_ended",
      "question": "Complete question text including context and code if relevant",
      "correct_answer": "Model answer or solution approach",
      "explanation": "Grading criteria and point distribution",
      "difficulty": "[from template]",
      "topic": "[from template]"
    }
  ]
}
```

START YOUR RESPONSE WITH ```json - NO other text before or after.

---

## USER TEMPLATE

'''
    return json_wrapper + user_prompt
```

**Akzeptanzkriterien**:
- [ ] Wrapper wird transparent hinzugefügt (Benutzer sieht ihn nicht)
- [ ] Original-Template bleibt unverändert in der Datenbank
- [ ] JSON-Instruktionen sind klar und unmissverständlich

#### FR-2: Template-Validierung beim Upload

**Beschreibung**: Beim Upload eines Templates wird geprüft, ob `{{ context }}` vorhanden ist.

**Implementierung**:
```python
def validate_template(self, content: str) -> List[str]:
    """Validate template for required variables."""
    errors = []

    if '{{ context }}' not in content and '{{context}}' not in content:
        errors.append(
            "Template muss '{{ context }}' enthalten, damit Dokumentinhalte "
            "eingefügt werden können. Fügen Sie diese Variable an der Stelle ein, "
            "wo das akademische Material erscheinen soll."
        )

    return errors
```

**Akzeptanzkriterien**:
- [ ] Warnung wird angezeigt wenn `{{ context }}` fehlt
- [ ] Upload wird nicht blockiert (nur Warnung)
- [ ] Klare Fehlermeldung mit Lösungsvorschlag

### Should-Have

#### FR-3: Verbesserte Parser-Robustheit

**Beschreibung**: Parser akzeptiert auch Markdown-formatierte Antworten als Fallback.

**Rationale**: Falls Claude trotz JSON-Instruktionen Markdown ausgibt, sollte der Parser versuchen, die Struktur zu extrahieren.

#### FR-4: Template-Preview mit JSON-Wrapper

**Beschreibung**: Live-Preview zeigt das vollständige Prompt inklusive JSON-Wrapper.

### Could-Have

#### FR-5: Konfigurierbarer Output-Modus

**Beschreibung**: Fortgeschrittene Benutzer können JSON-Output deaktivieren, wenn sie eigene Parser verwenden.

---

## Nicht-funktionale Anforderungen

### Performance

- JSON-Wrapper-Hinzufügung: < 1ms
- Template-Validierung: < 10ms
- Keine Auswirkung auf Claude API Latenz

### Usability

- Template-Erstellung ohne JSON-Kenntnisse möglich
- Klare Dokumentation der verfügbaren Variablen
- Beispiel-Templates in der UI

### Reliability

- 95%+ Parser-Erfolgsrate bei korrekten Claude-Antworten
- Graceful Degradation bei unerwarteten Antwortformaten

---

## Abgrenzung (Out of Scope)

| Feature | Rationale | Future |
|---------|-----------|--------|
| Automatische Markdown-zu-JSON-Konvertierung | Komplexität, Edge Cases | v2.0 |
| Benutzerdefinierte JSON-Schemas | Überkompliziert für MVP | Backlog |
| Multi-Format-Output (JSON + Markdown) | Scope Creep | Backlog |

---

## Technische Erkenntnisse aus Session 2026-01-15

### Gelöste Probleme

1. **Import-Problem in `rag_exams.py`**: Direkte Imports verhinderten dynamische Service-Ersetzung
   - Fix: Module-Import statt direkter Import

2. **Doppelte Parser-Methode**: Zwei `_parse_claude_response()` Funktionen überschrieben sich
   - Fix: Duplikat entfernt, Parser verbessert

3. **Timeout zu kurz**: 30s reichte nicht für große Prompts mit Kontext
   - Fix: Auf 120s erhöht, konfigurierbar via `CLAUDE_REQUEST_TIMEOUT`

4. **Fehlende `{{ context }}` Variable**: Template hatte keinen Platzhalter für Dokumentinhalt
   - Fix: In Datenbank hinzugefügt

### Offenes Problem (dieses PRD)

5. **Markdown vs. JSON Output**: Claude gibt Markdown aus wenn nicht explizit JSON angefordert
   - Lösung: Automatischer JSON-Wrapper (dieses PRD)

---

## Risikobewertung

| Risiko | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| Claude ignoriert JSON-Instruktionen | Hoch | Mittel | Mehrfache, klare Instruktionen; Fallback-Parser |
| Wrapper beeinflusst Fragenqualität | Mittel | Niedrig | A/B Testing; Wrapper minimieren |
| Breaking Change für bestehende Templates | Hoch | Niedrig | Wrapper ist additiv, ändert nichts am Original |

---

## Timeline & Meilensteine

| Phase | Dauer | Deliverables |
|-------|-------|--------------|
| **Phase 1: JSON-Wrapper** | 1-2 Tage | `_wrap_template_with_json_instructions()` in RAG Service |
| **Phase 2: Template-Validierung** | 1 Tag | Upload-Validierung für `{{ context }}` |
| **Phase 3: Testing** | 1 Tag | E2E Tests mit bestehenden Templates |
| **Phase 4: Dokumentation** | 0.5 Tage | Template-Erstellungsguide aktualisieren |

**Gesamtdauer**: ~4-5 Tage

---

## Anhang: Referenz-Template

Das ursprüngliche Template des Benutzers (`/demo/example_prompts/question_generator_academic.md`) soll **ohne Änderungen** funktionieren:

```markdown
---
name: question_generator_academic
category: system_prompt
description: Generiert qualitativ hochwertige Prüfungsfragen für BSc Informatik
use_case: question_generation_open_ended
tags: [exam, academic, programming, bsc-informatik]
language: de
difficulty_level: medium
---

# Prüfungsfragen-Generator für BSc Informatik

Du bist ein Experte für die Erstellung akademischer Prüfungsfragen.

## Aufgabe

Erstelle qualitativ hochwertige Prüfungsfragen für BSc Informatik Studierende
basierend auf den bereitgestellten akademischen Materialien.

## Kontext

**Themenbereich**: {{ topic }}
**Schwierigkeitsgrad**: {{ difficulty }}

### Akademisches Material:

{{ context }}

## Anforderungen

1. Material-Analyse: Identifiziere relevante Konzepte
2. Fragen-Entwicklung: Code-Vervollständigung oder Verständnisfragen
3. Qualitätssicherung: Akademisches Niveau

## Ausgabeformat

Für jede Frage:
- Kontext und theoretischer Hintergrund
- Aufgabenstellung
- Code-Grundgerüst (falls relevant)
- Bewertungskriterien und Punkteverteilung
```

Dieses Template enthält **kein JSON** - das System muss es automatisch hinzufügen.

---

## Approval

- [ ] Product Owner
- [ ] Tech Lead
- [ ] QA Lead
