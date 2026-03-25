# Best Practices

## Dokumenten-Upload

### Optimale Vorbereitung

1. Strukturieren Sie Dokumente mit klaren Ueberschriften
2. Verwenden Sie konsistente Formatierung
3. Fuegen Sie Metadaten hinzu (Titel, Autor, Datum)
4. Vermeiden Sie Wasserzeichen und Hintergrundbilder

### Batch-Upload

Laden Sie zusammengehoerige Dokumente gemeinsam hoch (z.B. alle Kapitel eines Lehrbuchs). Das erleichtert spaetere RAG-Pruefungen.

## Fragenerstellung

### Themenformulierung

- Spezifisch statt allgemein
- Kontext angeben
- Bloom-Level im Hinterkopf behalten

!!! example "Beispiele"
    **Gut:**

    - "Python Listen -- Methoden append(), extend(), insert()"
    - "Algorithmen -- Zeitkomplexitaet von Sortierverfahren"

    **Schlecht:**

    - "Python" (zu breit)
    - "Programmierung" (zu allgemein)

### Qualitaetskontrolle

- Ueberpruefen Sie generierte Fragen immer
- Achten Sie auf Confidence Scores
- Passen Sie den Schwierigkeitsgrad an
- Nutzen Sie Quellenangaben zur Verifikation

## RAG-Pruefungen

- Waehlen Sie 3--5 relevante Dokumente (optimal)
- Geben Sie einen spezifischen Fokus an
- Zu viele Dokumente fuehren zu niedrigerer Qualitaet

## ChatBot-Nutzung

Beginnen Sie mit Ueberblicksfragen und vertiefen Sie schrittweise:

```text
Benutzer: "Was ist Heapsort?"
Bot: [Erklaert Heapsort]

Benutzer: "Wie unterscheidet sich das von Quicksort?"
Bot: [Vergleicht beide Algorithmen]

Benutzer: "Welcher ist effizienter fuer grosse Datenmengen?"
Bot: [Analysiert Komplexitaet]
```
