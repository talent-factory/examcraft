# Best Practices

## Dokumenten-Upload

### Optimale Vorbereitung

1. Strukturieren Sie Dokumente mit klaren Überschriften
2. Verwenden Sie konsistente Formatierung
3. Fügen Sie Metadaten hinzu (Titel, Autor, Datum)
4. Vermeiden Sie Wasserzeichen und Hintergrundbilder

### Batch-Upload

Laden Sie zusammengehörige Dokumente gemeinsam hoch (z.B. alle Kapitel eines Lehrbuchs). Das erleichtert spätere RAG-Prüfungen.

## Fragenerstellung

### Themenformulierung

- Spezifisch statt allgemein
- Kontext angeben
- Bloom-Level im Hinterkopf behalten

!!! example "Beispiele"
    **Gut:**

    - "Python Listen – Methoden append(), extend(), insert()"
    - "Algorithmen – Zeitkomplexität von Sortierverfahren"

    **Schlecht:**

    - "Python" (zu breit)
    - "Programmierung" (zu allgemein)

### Qualitätskontrolle

- Überprüfen Sie generierte Fragen immer
- Achten Sie auf Confidence Scores
- Passen Sie den Schwierigkeitsgrad an
- Nutzen Sie Quellenangaben zur Verifikation

## RAG-Prüfungen

- Wählen Sie 3–5 relevante Dokumente (optimal)
- Geben Sie einen spezifischen Fokus an
- Zu viele Dokumente führen zu niedrigerer Qualität

## ChatBot-Nutzung

Beginnen Sie mit Überblicksfragen und vertiefen Sie schrittweise:

```text
Benutzer: "Was ist Heapsort?"
Bot: [Erklärt Heapsort]

Benutzer: "Wie unterscheidet sich das von Quicksort?"
Bot: [Vergleicht beide Algorithmen]

Benutzer: "Welcher ist effizienter für grosse Datenmengen?"
Bot: [Analysiert Komplexität]
```
