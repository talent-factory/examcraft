# Dokumente hochladen und verwalten

## Unterstuetzte Dateiformate

| Format | Erweiterung | Max. Groesse | Besonderheiten |
|--------|-------------|------------|----------------|
| PDF | `.pdf` | 50 MB | Tabellen, Formeln, Bilder |
| Word | `.doc`, `.docx` | 25 MB | Formatierung erhalten |
| Markdown | `.md` | 10 MB | Code-Bloecke, LaTeX |
| Text | `.txt` | 5 MB | Plain Text |

## Dokumente hochladen

### 1. Tab "Dokumente hochladen" oeffnen

Klicken Sie auf den Tab **Dokumente hochladen** in der Navigation.

### 2. Dateien auswaehlen

Sie haben zwei Moeglichkeiten:

- **Drag & Drop**: Ziehen Sie Dateien in den Upload-Bereich
- **Datei-Browser**: Klicken Sie auf **Dateien auswaehlen**

### 3. Upload-Fortschritt ueberwachen

Waehrend des Uploads sehen Sie:

- Dateiname und Groesse
- Fortschrittsbalken (0--100%)
- Status: "Wird verarbeitet..." dann "Verarbeitet"

### 4. Verarbeitung abwarten

Nach dem Upload werden die Dokumente automatisch:

1. Text extrahiert
2. In semantische Chunks aufgeteilt
3. In der Vektordatenbank indexiert
4. Fuer RAG-Suche vorbereitet

| Dokumenttyp | Typische Verarbeitungszeit |
|------------|---------------------------|
| PDF (10 Seiten) | ~30 Sekunden |
| Word (20 Seiten) | ~45 Sekunden |
| Markdown (5 Seiten) | ~15 Sekunden |

!!! tip "Best Practices fuer Uploads"
    - Verwenden Sie klare Dateinamen (z.B. `Algorithmen_Kapitel_3.pdf`)
    - Strukturierte Dokumente mit Ueberschriften liefern bessere Ergebnisse
    - Laden Sie zusammengehoerige Dokumente im Batch hoch

!!! warning "Vermeiden"
    - Gescannte PDFs ohne OCR
    - Passwortgeschuetzte Dateien
    - Dateien groesser als 50 MB
    - Duplikate

## Dokumentenbibliothek

Die Dokumentenbibliothek zeigt alle hochgeladenen Dokumente in einer uebersichtlichen Liste mit Dateiname, Upload-Datum, Dateigroesse, Seitenanzahl und Verarbeitungsstatus.

### Dokumente durchsuchen

Geben Sie Suchbegriffe in das Suchfeld ein. Ergebnisse werden in Echtzeit gefiltert (Dateiname, Tags, Inhalt).

**Filter:**

- Alle Formate
- Nur PDF
- Nur Word
- Nur Markdown

### Dokumente fuer Pruefungen auswaehlen

1. Aktivieren Sie die Checkboxen neben den gewuenschten Dokumenten
2. Klicken Sie auf **Pruefung aus Auswahl erstellen**
3. Sie werden zum RAG-Pruefungs-Creator weitergeleitet

### Dokumente loeschen

1. Klicken Sie auf das Loeschen-Symbol
2. Bestaetigen Sie die Sicherheitsabfrage
3. Dokument wird aus Bibliothek und Vektordatenbank entfernt

!!! warning "Achtung"
    Geloeschte Dokumente koennen nicht wiederhergestellt werden.
