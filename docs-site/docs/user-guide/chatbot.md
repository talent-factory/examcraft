# Dokument ChatBot

Der ChatBot ermöglicht interaktive Gespräche mit Ihren hochgeladenen Dokumenten.

## Dokument auswählen

1. Klicken Sie auf **Dokument ChatBot** in der Navigation
2. Wählen Sie ein Dokument aus dem Dropdown-Menü
3. Der ChatBot lädt den Kontext (2–5 Sekunden)

## Chat starten

Stellen Sie Fragen zu Ihrem Dokument:

- "Erkläre mir den Heapsort Algorithmus"
- "Was sind die Unterschiede zwischen Quicksort und Mergesort?"
- "Fasse Kapitel 3 zusammen"

!!! tip "Tipps für gute Fragen"
    - Spezifisch und klar formuliert
    - Bezug auf Dokumentinhalt
    - Folge-Fragen nutzen für tieferes Verständnis

## Antworten verstehen

Jede Antwort enthält:

- **Haupttext** – KI-generierte Antwort
- **Quellen** – Relevante Textabschnitte aus dem Dokument
- **Confidence** – Zuverlässigkeit (0–1)

| Confidence | Bedeutung |
|------|------|
| > 0.8 | Sehr zuverlässig |
| 0.6–0.8 | Zuverlässig |
| < 0.6 | Mit Vorsicht verwenden |

## Chat-Historie

- Alle Nachrichten werden innerhalb der Session gespeichert
- Kontext bleibt erhalten (Multi-Turn)
- Wählen Sie ein anderes Dokument, um eine neue Konversation zu starten
