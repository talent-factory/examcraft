# 🎛️ Admin Guide: Prompt Knowledge Base Management

> **Vollständige Anleitung für Administratoren zur Verwaltung der**
> **AI-Prompts in ExamCraft AI**

**Version**: 1.0.0
**Stand**: Oktober 2025
**Zielgruppe**: System-Administratoren, Prompt Engineers

---

## 📖 Inhaltsverzeichnis

1. [Übersicht](#-übersicht)
2. [Architektur](#️-architektur)
3. [Prompt Library](#-prompt-library)
4. [Prompt Editor](#️-prompt-editor)
5. [Template Variables](#-template-variables-neu)
6. [Version Control](#-version-control)
7. [Usage Analytics](#-usage-analytics)
8. [Semantic Search](#-semantic-search)
9. [Best Practices](#-best-practices)
10. [Troubleshooting](#-troubleshooting)

---

## 🎯 Übersicht

### Was ist das Prompt Management System?

Das Prompt Management System ermöglicht die **zentrale Verwaltung aller
AI-Prompts** ohne Code-Änderungen. Es bietet:

- ✅ **Versionierung** - Alle Änderungen werden getrackt
- ✅ **Rollback** - Zurück zu früheren Versionen
- ✅ **Semantic Search** - Finde Prompts nach Bedeutung
- ✅ **Analytics** - Überwache Performance und Kosten
- ✅ **Template System** - Wiederverwendbare Prompts mit Variablen
- ✅ **Web-Interface** - Keine Code-Änderungen nötig

### Warum Prompt Management?

**Vorteile:**

- 🚀 **Schnellere Iteration** - Teste neue Prompts ohne Deployment
- 📊 **Datengetrieben** - Entscheide basierend auf Metriken
- 🔄 **Sicherheit** - Rollback bei Problemen
- 👥 **Kollaboration** - Team kann gemeinsam optimieren
- 💰 **Kostenoptimierung** - Reduziere Token-Verbrauch

### Zugriff

**URL**: `http://localhost:3000` → Tab "Prompt Management"

**Berechtigungen**: Nur für Administratoren

---

## 🏗️ Architektur

### System-Komponenten

```text
┌─────────────────────────────────────────────────────┐
│  React Frontend (Material-UI)                       │
│  ├─ Prompt Library                                  │
│  ├─ Prompt Editor                                   │
│  ├─ Version History                                 │
│  ├─ Usage Analytics                                 │
│  └─ Semantic Search                                 │
├─────────────────────────────────────────────────────┤
│  API Layer (Axios)                                  │
│  └─ /api/v1/prompts/*                               │
├─────────────────────────────────────────────────────┤
│  Backend Services (FastAPI)                         │
│  ├─ PromptService (CRUD)                            │
│  ├─ PromptVectorService (Search)                    │
│  └─ PromptUsageLogger                               │
├─────────────────────────────────────────────────────┤
│  Datenbanken                                        │
│  ├─ PostgreSQL (Prompts, Versionen, Logs)          │
│  └─ Qdrant (Vector Search)                          │
└─────────────────────────────────────────────────────┘
```

### Datenmodell

**Tabelle: `prompts`**

```sql
- id (UUID, PK)
- name (VARCHAR, UNIQUE)
- content (TEXT)
- description (TEXT)
- category (ENUM: system_prompt, user_prompt, few_shot_example, template)
- tags (TEXT[])
- use_case (VARCHAR)
- version (INTEGER)
- is_active (BOOLEAN)
- parent_id (UUID, FK → prompts.id)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

**Tabelle: `prompt_usage_logs`**

```sql
- id (UUID, PK)
- prompt_id (UUID, FK)
- prompt_version (INTEGER)
- use_case (VARCHAR)
- tokens_used (INTEGER)
- latency_ms (INTEGER)
- success (BOOLEAN)
- timestamp (TIMESTAMP)
```

### API Endpoints

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/v1/prompts` | Liste aller Prompts |
| GET | `/api/v1/prompts/{id}` | Einzelner Prompt |
| POST | `/api/v1/prompts` | Neuer Prompt |
| PUT | `/api/v1/prompts/{id}` | Prompt aktualisieren |
| DELETE | `/api/v1/prompts/{id}` | Prompt löschen |
| POST | `/api/v1/prompts/{id}/versions` | Neue Version |
| GET | `/api/v1/prompts/versions/{name}` | Version History |
| POST | `/api/v1/prompts/search` | Semantic Search |
| GET | `/api/v1/prompts/{id}/usage` | Usage Logs |
| PATCH | `/api/v1/prompts/{id}/active` | Aktivieren/Deaktivieren |

---

## 📚 Prompt Library

### Übersicht

Die Prompt Library zeigt alle verfügbaren Prompts in einem Grid-Layout.

**Features:**

- 🔍 **Suche** - Durchsuche Name, Beschreibung, Tags
- 🏷️ **Filter** - Nach Kategorie filtern
- 📊 **Sortierung** - Nach Name, Datum, Verwendungen
- 🎨 **Farbcodierung** - Kategorien visuell unterscheiden

### Kategorien

**System Prompt** (Blau)

- Grundlegende Instruktionen für AI
- Definiert Verhalten und Rolle
- Beispiel: "Du bist ein Experte für Prüfungsfragen..."

**User Prompt** (Grün)

- Spezifische Aufgaben für AI
- Enthält konkrete Anweisungen
- Beispiel: "Generiere 5 Multiple Choice Fragen zu {topic}"

**Few-Shot Example** (Orange)

- Beispiele für gewünschtes Output-Format
- Hilft AI, Struktur zu verstehen
- Beispiel: Beispiel-Frage mit Antworten

**Template** (Lila)

- Wiederverwendbare Prompt-Vorlagen
- Enthält Variablen {variable}
- Beispiel: "Erstelle {count} Fragen zum Thema {topic}"

### Aktionen

**Bearbeiten** (✏️)

- Öffnet Prompt Editor
- Lädt aktuelle Version
- Ermöglicht Änderungen

**Versionen** (🕐)

- Zeigt Version History
- Ermöglicht Rollback
- Vergleicht Versionen

**Löschen** (🗑️)

- Entfernt Prompt permanent
- Sicherheitsabfrage erforderlich
- **Achtung**: Kann nicht rückgängig gemacht werden!

### Suche & Filter

**Suchfunktion:**

- Echtzeit-Filterung
- Durchsucht: Name, Beschreibung, Tags
- Case-insensitive

**Kategorie-Filter:**

- Alle Kategorien
- System Prompts
- User Prompts
- Few-Shot Examples
- Templates

---

## ✏️ Prompt Editor

### Neuen Prompt erstellen

#### Schritt 1: Grundinformationen

**Name:**

- Format: `snake_case`
- Eindeutig im System
- Beispiel: `system_prompt_question_generation`

**Beschreibung:**

- Kurze Erklärung (1-2 Sätze)
- Zweck und Verwendung
- Beispiel: "Generiert Multiple Choice Fragen aus Dokumenten"

#### Schritt 2: Kategorisierung

**Kategorie:**

- Wähle passende Kategorie
- Beeinflusst Verwendung im System

**Use Case:**

- Spezifischer Anwendungsfall
- Beispiele: `question_generation`, `chatbot`, `evaluation`

**Tags:**

- Schlagwörter für Suche
- Mehrere Tags möglich
- Beispiele: `education`, `multiple-choice`, `bloom-taxonomy`

#### Schritt 3: Content erstellen

**Editor-Tabs:**

- **Bearbeiten** - Markdown-Editor
- **Vorschau** - Gerenderte Ansicht

**Template-Variablen:**

Syntax: `{variable_name}`

Beispiel:

```markdown
Du bist ein Experte für {subject}.

Erstelle {count} Fragen zum Thema "{topic}" mit Schwierigkeitsgrad {difficulty}.

Anforderungen:
- Bloom-Level: {bloom_level}
- Fragetyp: {question_type}
- Sprache: {language}
```

**Verfügbare Variablen:**

- `{topic}` - Thema der Fragen
- `{count}` - Anzahl Fragen
- `{difficulty}` - Schwierigkeitsgrad
- `{question_type}` - Fragetyp
- `{language}` - Sprache
- `{context}` - RAG-Kontext
- `{bloom_level}` - Bloom-Taxonomie Level

#### Schritt 4: Aktivierung

**Aktiv-Toggle:**

- ☑️ **Aktiv** - Prompt wird sofort verwendet
- ☐ **Inaktiv** - Prompt ist gespeichert, aber nicht aktiv

**Empfehlung:**

- Teste neue Prompts zuerst inaktiv
- Aktiviere nach erfolgreichen Tests

### Bestehenden Prompt bearbeiten

**Änderungen vornehmen:**

1. Öffne Prompt in Editor
2. Nehme Änderungen vor
3. Speichere

**Versionierung:**

- Jede Speicherung erstellt neue Version
- Alte Versionen bleiben erhalten
- Nur neueste Version ist aktiv

**Best Practice:**

- Beschreibe Änderungen in Commit-Message
- Teste vor Aktivierung
- Überwache Usage Analytics nach Änderung

---

## 🔧 Template Variables (NEU)

### Übersicht

Das Template-Variablen-System ermöglicht **dynamische Prompt-Konfiguration** ohne Code-Änderungen. Benutzer können Variablen wie `topic`, `difficulty`, `language` direkt im UI anpassen.

**Features:**

- ✅ **Jinja2 Template-Rendering** - Unterstützt `{{variable}}` und `{variable}` Syntax
- ✅ **Variable Extraction API** - Automatische Erkennung von Template-Variablen
- ✅ **Live-Preview** - Echtzeit-Rendering während der Eingabe
- ✅ **Auto-Mapping** - Automatisches Befüllen aus Formular-Feldern
- ✅ **Type Detection** - Automatische Erkennung von Variablen-Typen

### Template-Syntax

**Jinja2 Syntax (empfohlen):**

```jinja2
Generate {{count}} questions about {{topic}} with difficulty {{difficulty}}.

Context:
{{context}}

Requirements:
- Bloom Level: {{bloom_level}}
- Language: {{language}}
- Include code examples: {{include_code}}
```

**Simple Syntax (Backward Compatibility):**

```text
Topic: {topic}
Difficulty: {difficulty}
Language: {language}
Context: {context}
```

**Beide Syntaxen werden unterstützt!**

### Variable Extraction

**Automatische Erkennung:**

Das System extrahiert automatisch alle Variablen aus dem Prompt-Content:

```python
# Backend: GET /api/v1/prompts/{prompt_id}/variables
{
  "prompt_id": "abc-123",
  "variables": ["topic", "difficulty", "language", "context"],
  "prompt_content_preview": "Generate questions about {{topic}}..."
}
```

**Unterstützte Variablen-Typen:**

- `string` - Text-Eingabe (Standard)
- `number` - Numerische Eingabe
- `boolean` - Checkbox
- `select` - Dropdown (wenn Optionen definiert)

### Live-Preview

**Echtzeit-Rendering:**

Während der Benutzer Variablen-Werte eingibt, wird der Prompt in Echtzeit gerendert:

```typescript
// Frontend: POST /api/v1/prompts/render-preview
{
  "prompt_id": "abc-123",
  "variables": {
    "topic": "Python Programming",
    "difficulty": "medium",
    "language": "de"
  }
}

// Response:
{
  "rendered_content": "Generate questions about Python Programming with difficulty medium...",
  "variables_used": ["topic", "difficulty", "language"]
}
```

**Debouncing:**

- API-Calls werden um 800ms verzögert
- Verhindert zu viele Requests während des Tippens
- Optimiert Performance und Kosten

### Auto-Mapping

**Automatisches Befüllen:**

Variablen, die bereits im Hauptformular existieren, werden automatisch befüllt:

| Variable | Quelle | Mapping |
|----------|--------|---------|
| `topic` | Topic-Feld | Direkt |
| `difficulty` | Schwierigkeit-Dropdown | easy/medium/hard |
| `language` | Sprache-Dropdown | de/en |
| `context` | Ausgewählte Dokumente | Backend |

**Redundanz-Eliminierung:**

- Auto-filled Variablen werden **nicht** im TemplateVariablesEditor angezeigt
- Nur **zusätzliche** Variablen werden angezeigt
- Editor versteckt sich komplett, wenn alle Variablen auto-filled sind

### Best Practices

**1. Verwende aussagekräftige Variablen-Namen:**

```jinja2
✅ GOOD: {{bloom_level}}, {{question_count}}, {{include_examples}}
❌ BAD: {{x}}, {{var1}}, {{temp}}
```

**2. Dokumentiere Variablen in Description:**

```text
Description: "Generates multiple choice questions.
Variables:
- topic: Subject area (e.g., 'Python Programming')
- difficulty: easy/medium/hard
- count: Number of questions (1-10)"
```

**3. Verwende Default-Werte:**

```jinja2
Generate {{count|default(5)}} questions about {{topic}}.
Difficulty: {{difficulty|default('medium')}}.
```

**4. Validiere Eingaben:**

```jinja2
{% if difficulty not in ['easy', 'medium', 'hard'] %}
  Error: Invalid difficulty level
{% endif %}
```

### Troubleshooting

**Problem: Variable wird nicht erkannt**

- ✅ Überprüfe Syntax: `{{variable}}` oder `{variable}`
- ✅ Keine Leerzeichen: `{{ variable }}` funktioniert nicht
- ✅ Nur alphanumerische Zeichen + Underscore

**Problem: Live-Preview zeigt Fehler**

- ✅ Überprüfe, ob alle Required Variables gesetzt sind
- ✅ Aktiviere Strict-Mode für detaillierte Fehler
- ✅ Überprüfe Jinja2-Syntax (z.B. geschlossene Tags)

**Problem: Auto-Mapping funktioniert nicht**

- ✅ Überprüfe Variablen-Namen (exakte Übereinstimmung)
- ✅ Überprüfe Formular-Werte (nicht leer)
- ✅ Überprüfe Browser-Console für Fehler

---

## 🔗 RAG Integration (NEU)

### Übersicht

Das RAG Service Integration Feature ermöglicht die **Verwendung von custom Prompts** direkt im Question Generation Workflow. Benutzer können Prompt-Templates aus der Knowledge Base auswählen und mit Template-Variablen konfigurieren.

**Features:**

- ✅ **Prompt-Auswahl im UI** - Dropdown für jeden Fragetyp
- ✅ **Template-Variablen-Editor** - Dynamische Konfiguration
- ✅ **Auto-Variable-Merging** - Automatisches Befüllen aus Formular
- ✅ **Live-Preview** - Echtzeit-Rendering des finalen Prompts
- ✅ **Fallback-Mechanismus** - Default Templates bei Fehlern
- ✅ **Usage Logging** - Tracking von custom Prompt-Verwendung

### Workflow

**1. Prompt-Auswahl:**

Benutzer wählt im RAG-Prüfung-Erstellen-Dialog einen Prompt-Template:

```text
┌─────────────────────────────────────────┐
│ Fragetyp: Multiple Choice               │
├─────────────────────────────────────────┤
│ Prompt-Template: [Dropdown]             │
│ ├─ Default Prompt                       │
│ ├─ Advanced MC Questions v2.1           │
│ └─ Bloom Level 4-6 MC Questions         │
└─────────────────────────────────────────┘
```

**2. Variable-Konfiguration:**

System befüllt automatisch:

| Variable | Quelle | Wert |
|----------|--------|------|
| `topic` | Thema-Feld | "Python Programming" |
| `difficulty` | Dropdown | "medium" |
| `language` | Dropdown | "de" |
| `context` | Dokumente | (Backend) |

Benutzer kann zusätzliche Variablen setzen:

```text
┌─────────────────────────────────────────┐
│ Zusätzliche Template-Variablen:         │
├─────────────────────────────────────────┤
│ bloom_level: [5]                        │
│ include_code: [✓]                       │
│ question_count: [10]                    │
└─────────────────────────────────────────┘
```

**3. Live-Preview:**

Zeigt gerenderten Prompt in Echtzeit:

```text
┌─────────────────────────────────────────┐
│ Prompt-Vorschau:                        │
├─────────────────────────────────────────┤
│ Generate 10 multiple choice questions   │
│ about Python Programming with           │
│ difficulty medium.                      │
│                                         │
│ Bloom Level: 5 (Evaluate)              │
│ Include code examples: Yes              │
│ Language: German                        │
└─────────────────────────────────────────┘
```

**4. Question Generation:**

Backend verwendet custom Prompt:

```python
# Backend: RAGService.generate_question()
async def generate_question(
    topic: str,
    context: RAGContext,
    question_type: str = "multiple_choice",
    difficulty: str = "medium",
    language: str = "de",
    # NEU: Custom Prompt
    prompt_id: Optional[str] = None,
    prompt_variables: Optional[Dict[str, Any]] = None
) -> RAGQuestion:
    if prompt_id:
        # Load custom prompt from Knowledge Base
        prompt = prompt_service.render_prompt_by_id(
            prompt_id=prompt_id,
            variables={
                "context": context_text,
                "topic": topic,
                "difficulty": difficulty,
                "language": language,
                **prompt_variables  # Merge custom variables
            }
        )
    else:
        # Fallback to default template
        prompt = self.question_templates[question_type]
```

### API Integration

**Request Format:**

```json
POST /api/v1/rag/generate-exam
{
  "topic": "Python Programming",
  "question_count": 5,
  "question_types": ["multiple_choice", "open_ended"],
  "difficulty": "medium",
  "language": "de",
  "prompt_config": {
    "multiple_choice": {
      "prompt_id": "abc-123-def-456",
      "variables": {
        "bloom_level": "5",
        "include_code": true
      }
    },
    "open_ended": {
      "prompt_id": "xyz-789-uvw-012",
      "variables": {
        "min_words": 200
      }
    }
  }
}
```

**Backward Compatibility:**

Alte Requests ohne `prompt_config` funktionieren weiterhin:

```json
POST /api/v1/rag/generate-exam
{
  "topic": "Python Programming",
  "question_count": 5,
  "question_types": ["multiple_choice"],
  "difficulty": "medium",
  "language": "de"
  // Kein prompt_config → Default Templates werden verwendet
}
```

### Usage Logging

**Automatisches Tracking:**

Jede Verwendung eines custom Prompts wird geloggt:

```python
# Backend: PromptUsageLogger
{
  "prompt_id": "abc-123",
  "use_case": "question_generation_multiple_choice",
  "timestamp": "2025-10-19T17:00:00Z",
  "variables_used": ["topic", "difficulty", "bloom_level"],
  "success": true
}
```

**Analytics Dashboard:**

- Zeigt Verwendungshäufigkeit pro Prompt
- Identifiziert beliebte Prompts
- Hilft bei Optimierung und Wartung

### Best Practices

**1. Teste custom Prompts vor Verwendung:**

- Verwende Live-Preview
- Generiere Test-Fragen
- Überprüfe Qualität

**2. Dokumentiere Template-Variablen:**

```text
Prompt Name: "Advanced MC Questions v2.1"
Description: "Generates Bloom Level 4-6 multiple choice questions with code examples.

Variables:
- topic: Subject area (required)
- difficulty: easy/medium/hard (required)
- bloom_level: 1-6 (default: 4)
- include_code: true/false (default: true)
- language: de/en (required)"
```

**3. Verwende Fallback-Mechanismus:**

- System fällt automatisch auf default Templates zurück
- Keine Fehler bei ungültigen Prompt-IDs
- Logging für Debugging

**4. Überwache Usage Analytics:**

- Identifiziere problematische Prompts
- Optimiere basierend auf Nutzung
- Deaktiviere ungenutzte Prompts

### Troubleshooting

**Problem: Custom Prompt wird nicht verwendet**

- ✅ Überprüfe Prompt-ID (UUID-Format)
- ✅ Überprüfe Prompt-Status (is_active = true)
- ✅ Überprüfe Backend-Logs für Fehler
- ✅ Teste mit default Prompt

**Problem: Variable-Merging funktioniert nicht**

- ✅ Überprüfe Variablen-Namen (case-sensitive)
- ✅ Überprüfe Jinja2-Syntax im Prompt
- ✅ Teste mit Live-Preview
- ✅ Überprüfe Browser-Console

**Problem: Fallback wird immer verwendet**

- ✅ Überprüfe Prompt-ID Validität
- ✅ Überprüfe Prompt-Content (keine Syntax-Fehler)
- ✅ Überprüfe Backend-Logs für Details
- ✅ Teste Prompt-Rendering separat

---

## 🕐 Version Control

### Version History anzeigen

**Zugriff:**

- Klicke "Versionen" in Prompt Library
- Oder: "Versionen anzeigen" in Editor

**Anzeige:**

- Tabelle mit allen Versionen
- Sortiert nach Version (neueste zuerst)
- Zeigt: Version, Status, Beschreibung, Datum

### Versionen vergleichen

**Vorschau:**

1. Klicke "Vorschau" bei gewünschter Version
2. Dialog zeigt:
   - Beschreibung
   - Content
   - Tags
   - Metadaten

**Vergleich:**

- Aktuell: Manueller Vergleich
- Geplant (v1.1): Diff-Ansicht

### Rollback durchführen

**Wann Rollback?**

- Neue Version funktioniert nicht
- Performance-Probleme
- Qualitätsverschlechterung
- Fehlerhafte Generierungen

**Vorgehensweise:**

1. Öffne Version History
2. Finde gewünschte Version
3. Klicke "Aktivieren"
4. Bestätige Sicherheitsabfrage
5. Alte Version wird aktiv

**Wichtig:**

- Nur eine Version kann aktiv sein
- Rollback erstellt keine neue Version
- Alte Version wird reaktiviert

### Versionsmanagement Best Practices

**Naming Convention:**

- v1.0 - Initial Release
- v1.1 - Minor Update
- v2.0 - Major Rewrite

**Beschreibungen:**

- Kurz und prägnant
- Was wurde geändert?
- Warum wurde geändert?

**Testing:**

- Teste neue Versionen vor Aktivierung
- Überwache Metriken nach Rollout
- Halte Rollback-Plan bereit

---

## 📊 Usage Analytics

### Metriken-Übersicht

**4 Haupt-Metriken:**

#### 1. Verwendungen

- Anzahl Aufrufe des Prompts
- Zeigt Popularität
- Hilft bei Priorisierung

#### 2. Erfolgsrate

- % erfolgreiche Generierungen
- Indikator für Qualität
- Ziel: >95%

#### 3. Ø Latenz

- Durchschnittliche Antwortzeit in ms
- Performance-Indikator
- Ziel: <2000ms

#### 4. Tokens Total

- Gesamtverbrauch an Tokens
- Kosten-Indikator
- Optimierungspotential

### Verwendungsverlauf

**Tabelle zeigt:**

- Timestamp
- Use Case
- Tokens verwendet
- Latenz
- Erfolg/Fehler

**Filterung:**

- Letzte 100 Verwendungen
- Sortiert nach Datum (neueste zuerst)

### Interpretation

**Erfolgsrate:**

- >95%: Sehr gut ✅
- 90-95%: Gut ✅
- 80-90%: Akzeptabel ⚠️
- <80%: Optimierung nötig ❌

**Latenz:**

- <1000ms: Sehr schnell ✅
- 1000-2000ms: Schnell ✅
- 2000-5000ms: Akzeptabel ⚠️
- >5000ms: Zu langsam ❌

**Token-Verbrauch:**

- Vergleiche mit ähnlichen Prompts
- Identifiziere Optimierungspotential
- Reduziere unnötige Tokens

### Optimierung basierend auf Analytics

**Niedrige Erfolgsrate:**

1. Überprüfe Prompt-Formulierung
2. Füge mehr Kontext hinzu
3. Verbessere Beispiele
4. Teste mit verschiedenen Inputs

**Hohe Latenz:**

1. Reduziere Prompt-Länge
2. Entferne unnötige Instruktionen
3. Optimiere Template-Variablen
4. Prüfe API-Performance

**Hoher Token-Verbrauch:**

1. Kürze Prompt-Text
2. Entferne Redundanzen
3. Nutze effizientere Formulierungen
4. Teste kürzere Varianten

---

## 🔍 Semantic Search

### Funktionsweise

Semantic Search findet Prompts basierend auf **Bedeutung**, nicht nur
Keywords.

**Technologie:**

- OpenAI Embeddings (text-embedding-3-small)
- Qdrant Vector Database
- Cosine Similarity

### Suchparameter

**Query:**

- Natürlichsprachige Suchanfrage
- Beispiel: "Generiere Multiple Choice Fragen für Informatik"

**Filter:**

- **Kategorie** - Einschränkung auf Kategorie
- **Use Case** - Spezifischer Anwendungsfall
- **Tags** - Schlagwörter

**Advanced:**

- **Limit** - Anzahl Ergebnisse (1-20)
- **Score Threshold** - Minimum Similarity (0-1)

### Ergebnisse interpretieren

**Similarity Score:**

- 0.9-1.0: Sehr relevant ✅
- 0.7-0.9: Relevant ✅
- 0.5-0.7: Teilweise relevant ⚠️
- <0.5: Wenig relevant ❌

**Farbcodierung:**

- Grün: >0.9
- Blau: 0.7-0.9
- Orange: 0.5-0.7
- Grau: <0.5

### Anwendungsfälle

#### 1. Ähnliche Prompts finden

- Suche: "Fragen zu Algorithmen"
- Finde alle relevanten Prompts
- Vergleiche Ansätze

#### 2. Duplikate identifizieren

- Suche nach Prompt-Namen
- Finde ähnliche Prompts
- Konsolidiere wenn nötig

#### 3. Best Practices entdecken

- Suche nach Use Case
- Finde erfolgreiche Prompts
- Lerne von Beispielen

---

## 💡 Best Practices

### Prompt-Erstellung

**Struktur:**

```markdown
# Rolle
Du bist ein [Experte/Assistent] für [Bereich].

# Aufgabe
[Klare Beschreibung der Aufgabe]

# Anforderungen
- [Anforderung 1]
- [Anforderung 2]
- [Anforderung 3]

# Format
[Gewünschtes Output-Format]

# Beispiel
[Optional: Beispiel-Output]
```

**Dos:**

- ✅ Klare, präzise Instruktionen
- ✅ Konkrete Beispiele
- ✅ Strukturierte Formatierung
- ✅ Template-Variablen nutzen
- ✅ Testen vor Aktivierung

**Don'ts:**

- ❌ Vage Formulierungen
- ❌ Zu lange Prompts (>2000 Tokens)
- ❌ Widersprüchliche Anweisungen
- ❌ Unnötige Wiederholungen
- ❌ Direkt in Production aktivieren

### Versionierung

**Semantic Versioning:**

- v1.0.0 - Major.Minor.Patch
- Major: Breaking Changes
- Minor: Neue Features
- Patch: Bugfixes

**Changelog:**

- Dokumentiere alle Änderungen
- Nutze Beschreibungsfeld
- Referenziere Issues/Tickets

### Testing

**Test-Prozess:**

1. Erstelle Prompt (inaktiv)
2. Teste mit verschiedenen Inputs
3. Überprüfe Outputs
4. Messe Performance
5. Aktiviere wenn erfolgreich

**Test-Szenarien:**

- Normale Inputs
- Edge Cases
- Fehlerhafte Inputs
- Verschiedene Sprachen
- Verschiedene Schwierigkeitsgrade

### Monitoring

**Regelmäßige Checks:**

- Wöchentlich: Usage Analytics
- Monatlich: Erfolgsraten
- Quartalsweise: Optimierungspotential

**Alerts:**

- Erfolgsrate <90%
- Latenz >3000ms
- Ungewöhnlich hoher Token-Verbrauch

---

## 🔧 Troubleshooting

### Häufige Probleme

#### Problem: Prompt wird nicht verwendet

Lösungen:

1. Prüfe ob Prompt aktiv ist
2. Prüfe Use Case Zuordnung
3. Prüfe ob neueste Version aktiv
4. Restart Backend-Service

#### Problem: Niedrige Erfolgsrate

Lösungen:

1. Überprüfe Prompt-Formulierung
2. Füge mehr Kontext hinzu
3. Teste mit verschiedenen Inputs
4. Vergleiche mit erfolgreichen Prompts

#### Problem: Hohe Latenz

Lösungen:

1. Reduziere Prompt-Länge
2. Optimiere Template-Variablen
3. Prüfe API-Performance
4. Kontaktiere Support

#### Problem: Semantic Search findet nichts

Lösungen:

1. Reduziere Score Threshold
2. Erweitere Suchanfrage
3. Entferne Filter
4. Prüfe ob Prompts indexiert sind

### Logs & Debugging

**Backend Logs:**

```bash
docker-compose logs -f backend | grep prompt
```

**Database Queries:**

```sql
-- Alle aktiven Prompts
SELECT * FROM prompts WHERE is_active = true;

-- Usage Statistics
SELECT 
  prompt_id,
  COUNT(*) as uses,
  AVG(latency_ms) as avg_latency,
  SUM(tokens_used) as total_tokens
FROM prompt_usage_logs
GROUP BY prompt_id;
```

**Vector Search Status:**

```bash
# Qdrant Collection Info
curl http://localhost:6333/collections/prompts_knowledge_base
```

---

## 📞 Support

**Technische Fragen:**

- Email: <admin@examcraft.ai>
- Slack: #prompt-management

**Dokumentation:**

- [API Docs](http://localhost:8000/docs)
- [GitHub Wiki](https://github.com/examcraft/wiki)

---

**Letzte Aktualisierung**: Oktober 2025
**Version**: 1.0.0
**Autor**: ExamCraft AI Team
