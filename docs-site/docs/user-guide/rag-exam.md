# RAG-basierte Prüfungen

## Was ist RAG?

**RAG** (Retrieval-Augmented Generation) kombiniert:

- **Retrieval**: Semantische Suche in Ihren Dokumenten
- **Generation**: KI-basierte Fragenerstellung

Der Vorteil: Fragen sind direkt aus Ihren Kursmaterialien abgeleitet und enthalten Quellenangaben.

## Voraussetzungen

- Mindestens 1 Dokument hochgeladen und verarbeitet
- Dokument in der Bibliothek ausgewählt

## Schritt-für-Schritt

### 1. Dokumente auswählen

In der Dokumentenbibliothek:

1. Wählen Sie 1–10 Dokumente aus
2. Klicken Sie **Prüfung aus Auswahl erstellen**

!!! tip "Optimale Dokumentenanzahl"
    3–5 Dokumente liefern die beste Qualität. Zu viele Dokumente können die Ergebnisse verwässern.

### 2. RAG-Konfiguration

- **Thema/Fokus**: Spezifischer Fokus (z.B. "Sortieralgorithmen Komplexität"). Leer lassen für allgemeine Fragen.
- **Anzahl Fragen**: 1–20, empfohlen 5–10
- **Fragetypen**: Multiple Choice, Offene Fragen, True/False
- **Schwierigkeitsgrad**: Einfach / Mittel / Schwer
- **Prompt-Vorlage**: Wählen Sie ein Prompt-Template mit Live-Vorschau

### 3. Generierung starten

Klicken Sie **RAG-Prüfung generieren**. Wartezeit: 20–60 Sekunden.

### 4. Ergebnis prüfen

Jede Frage enthält:

- Fragentext und Antwortoptionen
- Korrekte Antwort mit Erklärung
- **Quelldokumente** (mit Seitenzahl)
- **Confidence Score** (0–1)

## Qualitätsindikatoren

| Confidence Score | Bewertung |
|---------|------|
| 0.9–1.0 | Sehr hohe Qualität |
| 0.7–0.9 | Gute Qualität |
| 0.5–0.7 | Akzeptabel – Überprüfen |
| < 0.5 | Überarbeitung empfohlen |
