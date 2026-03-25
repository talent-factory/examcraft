# Dokumente hochladen und verwalten

## Unterstützte Dateiformate

| Format | Erweiterung | Max. Grösse | Besonderheiten |
|----|-------|------|--------|
| PDF | `.pdf` | 50 MB | Tabellen, Formeln, Bilder |
| Word | `.doc`, `.docx` | 25 MB | Formatierung erhalten |
| Markdown | `.md` | 10 MB | Code-Blöcke, LaTeX |
| Text | `.txt` | 5 MB | Plain Text |

## Dokumente hochladen

### 1. Tab "Dokumente hochladen" öffnen

Klicken Sie auf den Tab **Dokumente hochladen** in der Navigation.

### 2. Dateien auswählen

Sie haben zwei Möglichkeiten:

- **Drag & Drop**: Ziehen Sie Dateien in den Upload-Bereich
- **Datei-Browser**: Klicken Sie auf **Dateien auswählen**

### 3. Upload-Fortschritt überwachen

Während des Uploads sehen Sie:

- Dateiname und Grösse
- Fortschrittsbalken (0–100%)
- Status: "Wird verarbeitet..." dann "Verarbeitet"

### 4. Verarbeitung abwarten

Nach dem Upload werden die Dokumente automatisch:

1. Text extrahiert
2. In semantische Chunks aufgeteilt
3. In der Vektordatenbank indexiert
4. Für RAG-Suche vorbereitet

| Dokumenttyp | Typische Verarbeitungszeit |
|------|--------------|
| PDF (10 Seiten) | ~30 Sekunden |
| Word (20 Seiten) | ~45 Sekunden |
| Markdown (5 Seiten) | ~15 Sekunden |

!!! tip "Best Practices für Uploads"
    - Verwenden Sie klare Dateinamen (z.B. `Algorithmen_Kapitel_3.pdf`)
    - Strukturierte Dokumente mit Überschriften liefern bessere Ergebnisse
    - Laden Sie zusammengehörige Dokumente im Batch hoch

!!! warning "Vermeiden"
    - Gescannte PDFs ohne OCR
    - Passwortgeschützte Dateien
    - Dateien grösser als 50 MB
    - Duplikate

## Dokumentenbibliothek

Die Dokumentenbibliothek zeigt alle hochgeladenen Dokumente in einer übersichtlichen Liste mit Dateiname, Upload-Datum, Dateigrösse, Seitenanzahl und Verarbeitungsstatus.

### Dokumente durchsuchen

Geben Sie Suchbegriffe in das Suchfeld ein. Ergebnisse werden in Echtzeit gefiltert (Dateiname, Tags, Inhalt).

**Filter:**

- Alle Formate
- Nur PDF
- Nur Word
- Nur Markdown

### Dokumente für Prüfungen auswählen

1. Aktivieren Sie die Checkboxen neben den gewünschten Dokumenten
2. Klicken Sie auf **Prüfung aus Auswahl erstellen**
3. Sie werden zum RAG-Prüfungs-Creator weitergeleitet

### Dokumente löschen

1. Klicken Sie auf das Löschen-Symbol
2. Bestätigen Sie die Sicherheitsabfrage
3. Dokument wird aus Bibliothek und Vektordatenbank entfernt

!!! warning "Achtung"
    Gelöschte Dokumente können nicht wiederhergestellt werden.
