# RAG-basierte Pruefungen

## Was ist RAG?

**RAG** (Retrieval-Augmented Generation) kombiniert:

- **Retrieval**: Semantische Suche in Ihren Dokumenten
- **Generation**: KI-basierte Fragenerstellung

Der Vorteil: Fragen sind direkt aus Ihren Kursmaterialien abgeleitet und enthalten Quellenangaben.

## Voraussetzungen

- Mindestens 1 Dokument hochgeladen und verarbeitet
- Dokument in der Bibliothek ausgewaehlt

## Schritt-fuer-Schritt

### 1. Dokumente auswaehlen

In der Dokumentenbibliothek:

1. Waehlen Sie 1--10 Dokumente aus
2. Klicken Sie **Pruefung aus Auswahl erstellen**

!!! tip "Optimale Dokumentenanzahl"
    3--5 Dokumente liefern die beste Qualitaet. Zu viele Dokumente koennen die Ergebnisse verwaessern.

### 2. RAG-Konfiguration

- **Thema/Fokus**: Spezifischer Fokus (z.B. "Sortieralgorithmen Komplexitaet"). Leer lassen fuer allgemeine Fragen.
- **Anzahl Fragen**: 1--20, empfohlen 5--10
- **Fragetypen**: Multiple Choice, Offene Fragen, True/False
- **Schwierigkeitsgrad**: Einfach / Mittel / Schwer
- **Prompt-Vorlage**: Waehlen Sie ein Prompt-Template mit Live-Vorschau

### 3. Generierung starten

Klicken Sie **RAG-Pruefung generieren**. Wartezeit: 20--60 Sekunden.

### 4. Ergebnis pruefen

Jede Frage enthaelt:

- Fragentext und Antwortoptionen
- Korrekte Antwort mit Erklaerung
- **Quelldokumente** (mit Seitenzahl)
- **Confidence Score** (0--1)

## Qualitaetsindikatoren

| Confidence Score | Bewertung |
|-----------------|-----------|
| 0.9--1.0 | Sehr hohe Qualitaet |
| 0.7--0.9 | Gute Qualitaet |
| 0.5--0.7 | Akzeptabel -- Ueberpruefen |
| < 0.5 | Ueberarbeitung empfohlen |
