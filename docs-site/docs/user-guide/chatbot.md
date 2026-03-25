# Dokument ChatBot

Der ChatBot ermoeglicht interaktive Gespraeche mit Ihren hochgeladenen Dokumenten.

## Dokument auswaehlen

1. Klicken Sie auf **Dokument ChatBot** in der Navigation
2. Waehlen Sie ein Dokument aus dem Dropdown-Menue
3. Der ChatBot laedt den Kontext (2--5 Sekunden)

## Chat starten

Stellen Sie Fragen zu Ihrem Dokument:

- "Erklaere mir den Heapsort Algorithmus"
- "Was sind die Unterschiede zwischen Quicksort und Mergesort?"
- "Fasse Kapitel 3 zusammen"

!!! tip "Tipps fuer gute Fragen"
    - Spezifisch und klar formuliert
    - Bezug auf Dokumentinhalt
    - Folge-Fragen nutzen fuer tieferes Verstaendnis

## Antworten verstehen

Jede Antwort enthaelt:

- **Haupttext** -- KI-generierte Antwort
- **Quellen** -- Relevante Textabschnitte aus dem Dokument
- **Confidence** -- Zuverlaessigkeit (0--1)

| Confidence | Bedeutung |
|-----------|-----------|
| > 0.8 | Sehr zuverlaessig |
| 0.6--0.8 | Zuverlaessig |
| < 0.6 | Mit Vorsicht verwenden |

## Chat-Historie

- Alle Nachrichten werden innerhalb der Session gespeichert
- Kontext bleibt erhalten (Multi-Turn)
- Waehlen Sie ein anderes Dokument, um eine neue Konversation zu starten
