# PDF-zu-Markdown Extraktion

Ein robustes Python-Script zur Extraktion von Text aus PDF-Dateien und Konvertierung zu Markdown-Format.

## Features

- **Batch-Verarbeitung**: Verarbeitet alle PDF-Dateien in einem Verzeichnis automatisch
- **Dual-Engine-Support**: Nutzt `docling` für erweiterte Features, fällt auf `pypdf` zurück
- **Metadaten-Extraktion**: Extrahiert Titel, Autor, Seitenanzahl und andere Metadaten
- **Flexible Ausgabe**: Unterstützt separate Ein- und Ausgabeverzeichnisse
- **Umfassendes Logging**: Detaillierte Protokollierung mit konfigurierbaren Log-Levels
- **Kommandozeilen-Interface**: Vollständig konfigurierbar über Kommandozeilenargumente
- **Fortschrittsanzeige**: Zeigt Verarbeitungsfortschritt bei mehreren Dateien
- **Robuste Fehlerbehandlung**: Graceful Fallbacks und aussagekräftige Fehlermeldungen

## Installation

Das Script nutzt die folgenden Dependencies, die bereits im Projekt konfiguriert sind:

```bash
uv add docling pypdf
```text

## Verwendung

### Grundlegende Verwendung

```bash
# Verarbeitet alle PDFs im demo/ Verzeichnis
uv run python utils/extraction.py

# Mit spezifischen Verzeichnissen
uv run python utils/extraction.py -i pdfs/ -o markdown/

# Erzwingt pypdf statt docling
uv run python utils/extraction.py --force-pypdf

# Mit detaillierter Ausgabe
uv run python utils/extraction.py --verbose
```text

### Kommandozeilenoptionen

| Option | Beschreibung |
|--------|-------------|
| `-i, --input-dir` | Eingabeverzeichnis mit PDF-Dateien (Standard: demo) |
| `-o, --output-dir` | Ausgabeverzeichnis für Markdown-Dateien (Standard: gleiches wie Eingabe) |
| `--force-pypdf` | Erzwingt die Verwendung von pypdf statt docling |
| `-v, --verbose` | Aktiviert detaillierte Logging-Ausgabe |
| `--log-file` | Pfad zur Log-Datei (Standard: automatisch generiert) |
| `-h, --help` | Zeigt Hilfe an |

### Beispiele

```bash
# Einfache Verarbeitung mit Standardeinstellungen
uv run python utils/extraction.py

# Spezifische Verzeichnisse mit Logging
uv run python utils/extraction.py -i documents/pdfs -o documents/markdown --verbose

# Nur pypdf verwenden mit eigener Log-Datei
uv run python utils/extraction.py --force-pypdf --log-file extraction.log

# Hilfe anzeigen
uv run python utils/extraction.py --help
```text

## Ausgabeformat

Das Script erstellt Markdown-Dateien mit folgender Struktur:

```markdown
# Dokument-Metadaten

**Titel:** [Dokumenttitel]
**Autor:** [Autor]
**Erstellt mit:** [Creator-Software]
**Anzahl Seiten:** [Seitenanzahl]

---

## Seite 1

[Seiteninhalt...]

## Seite 2

[Seiteninhalt...]
```text

## Verarbeitungsmethoden

### Docling (Primär)

- Erweiterte PDF-Verarbeitung mit KI-Features
- Bessere Texterkennung und Strukturierung
- Automatischer Fallback bei Fehlern

### PyPDF (Fallback)

- Zuverlässige lokale PDF-Verarbeitung
- Keine externen API-Abhängigkeiten
- Metadaten-Extraktion inklusive

## Logging

Das Script erstellt automatisch Log-Dateien mit Zeitstempel:

- Format: `pdf_extraction_YYYYMMDD_HHMMSS.log`
- Konfigurierbare Log-Level (INFO, DEBUG)
- Sowohl Konsolen- als auch Datei-Ausgabe

## Fehlerbehandlung

- Automatischer Fallback von docling zu pypdf
- Detaillierte Fehlermeldungen
- Fortsetzung der Verarbeitung bei einzelnen Fehlern
- Zusammenfassung am Ende der Verarbeitung

## Entwicklung

### Funktionsstruktur

```python
# Hauptfunktionen
setup_logging()           # Logging-Konfiguration
extract_text_with_pypdf() # PyPDF-basierte Extraktion
process_pdf_files()       # Batch-Verarbeitung
main()                    # CLI-Interface
```text

### Erweiterungsmöglichkeiten

- Unterstützung für weitere Dateiformate
- OCR-Integration für gescannte PDFs
- Erweiterte Metadaten-Extraktion
- Parallelverarbeitung für große Dateien

## Lizenz

Dieses Script ist Teil des ExamCraft-Projekts und steht unter der MIT-Lizenz.
