# Prompt Management

Das Prompt Management System ermöglicht die zentrale Verwaltung aller AI-Prompts ohne Code-Änderungen.

## Übersicht

- **Versionierung** – Alle Änderungen werden getrackt
- **Rollback** – Zurück zu früheren Versionen
- **Semantic Search** – Finde Prompts nach Bedeutung
- **Analytics** – Überwache Performance und Kosten
- **Template System** – Wiederverwendbare Prompts mit Variablen
- **Web-Interface** – Keine Code-Änderungen nötig

## Prompt Library

### Ansicht

Die Prompt Library zeigt alle verfügbaren Prompts in einem Grid-Layout mit:

- Prompt-Name und Beschreibung
- Kategorie (System / User / Template)
- Use Case, Version, Status
- Tags und Verwendungszähler

### Aktionen

- **Bearbeiten** – Prompt im Editor öffnen
- **Versionen** – Version History anzeigen
- **Löschen** – Prompt entfernen

## Prompt Editor

### Neuen Prompt erstellen

1. Klicken Sie **Neuer Prompt**
2. Füllen Sie die folgenden Felder aus:

| Feld | Beschreibung |
|---|-------|
| Name | Eindeutiger Identifier (z.B. `system_prompt_question_generation`) |
| Beschreibung | Kurze Erklärung |
| Kategorie | System Prompt / User Prompt / Few-Shot Example / Template |
| Use Case | Verwendungszweck (z.B. `question_generation`) |
| Content | Prompt-Text (Markdown unterstützt) |
| Tags | Schlagwörter für Suche |
| Aktiv | Sofort aktivieren? |

### Template-Variablen

Syntax: `{variable_name}`

Beispiel: `Generiere {count} Fragen zum Thema {topic}`

Variablen werden zur Laufzeit ersetzt. Bei RAG-Prüfungen stehen folgende Variablen automatisch zur Verfügung: `topic`, `difficulty`, `language`, `context`.

## Version Control

- Automatische Versionsnummern (v1, v2, v3...)
- Nur eine Version kann gleichzeitig aktiv sein
- Alte Versionen bleiben erhalten

### Rollback

1. Öffnen Sie die Version History
2. Wählen Sie die gewünschte Version
3. Klicken Sie **Aktivieren**
4. Bestätigen Sie

## Usage Analytics

| Metrik | Beschreibung |
|----|-------|
| Verwendungen | Anzahl Aufrufe |
| Erfolgsrate | % erfolgreiche Generierungen |
| Durchschn. Latenz | Durchschnittliche Antwortzeit |
| Tokens Total | Gesamtverbrauch |

## Semantic Search

1. Wechseln Sie zum Tab **Semantic Search**
2. Geben Sie eine Suchanfrage ein
3. Filtern Sie nach Kategorie, Use Case oder Similarity Threshold
4. Ergebnisse werden nach Relevanz sortiert
