# Prompt Management

Das Prompt Management System ermoeglicht die zentrale Verwaltung aller AI-Prompts ohne Code-Aenderungen.

## Uebersicht

- **Versionierung** -- Alle Aenderungen werden getrackt
- **Rollback** -- Zurueck zu frueheren Versionen
- **Semantic Search** -- Finde Prompts nach Bedeutung
- **Analytics** -- Ueberwache Performance und Kosten
- **Template System** -- Wiederverwendbare Prompts mit Variablen
- **Web-Interface** -- Keine Code-Aenderungen noetig

## Prompt Library

### Ansicht

Die Prompt Library zeigt alle verfuegbaren Prompts in einem Grid-Layout mit:

- Prompt-Name und Beschreibung
- Kategorie (System / User / Template)
- Use Case, Version, Status
- Tags und Verwendungszaehler

### Aktionen

- **Bearbeiten** -- Prompt im Editor oeffnen
- **Versionen** -- Version History anzeigen
- **Loeschen** -- Prompt entfernen

## Prompt Editor

### Neuen Prompt erstellen

1. Klicken Sie **Neuer Prompt**
2. Fuellen Sie die folgenden Felder aus:

| Feld | Beschreibung |
|------|-------------|
| Name | Eindeutiger Identifier (z.B. `system_prompt_question_generation`) |
| Beschreibung | Kurze Erklaerung |
| Kategorie | System Prompt / User Prompt / Few-Shot Example / Template |
| Use Case | Verwendungszweck (z.B. `question_generation`) |
| Content | Prompt-Text (Markdown unterstuetzt) |
| Tags | Schlagwoerter fuer Suche |
| Aktiv | Sofort aktivieren? |

### Template-Variablen

Syntax: `{variable_name}`

Beispiel: `Generiere {count} Fragen zum Thema {topic}`

Variablen werden zur Laufzeit ersetzt. Bei RAG-Pruefungen stehen folgende Variablen automatisch zur Verfuegung: `topic`, `difficulty`, `language`, `context`.

## Version Control

- Automatische Versionsnummern (v1, v2, v3...)
- Nur eine Version kann gleichzeitig aktiv sein
- Alte Versionen bleiben erhalten

### Rollback

1. Oeffnen Sie die Version History
2. Waehlen Sie die gewuenschte Version
3. Klicken Sie **Aktivieren**
4. Bestaetigen Sie

## Usage Analytics

| Metrik | Beschreibung |
|--------|-------------|
| Verwendungen | Anzahl Aufrufe |
| Erfolgsrate | % erfolgreiche Generierungen |
| Durchschn. Latenz | Durchschnittliche Antwortzeit |
| Tokens Total | Gesamtverbrauch |

## Semantic Search

1. Wechseln Sie zum Tab **Semantic Search**
2. Geben Sie eine Suchanfrage ein
3. Filtern Sie nach Kategorie, Use Case oder Similarity Threshold
4. Ergebnisse werden nach Relevanz sortiert
