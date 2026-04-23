# Prüfungen exportieren

Der Export von Prüfungen ermöglicht es Ihnen, generierte und überprüfte Fragen in verschiedenen Formaten zu verwenden oder in externe Systeme zu importieren.

## Aktuelle Export-Optionen

### Manuelle Kopie (aktuell verfügbar)

Generierte Fragen können direkt aus der Review Queue oder dem Prüfungskomponisten kopiert werden:

1. **Aus der Review Queue**:
   - Wählen Sie genehmigte Fragen aus
   - Klicken Sie auf „Kopieren"
   - Einfügen in Word, Google Docs, oder Texteditor

2. **Aus dem Prüfungskomponisten**:
   - Klicken Sie auf die fertige Prüfung
   - Nutzen Sie die Browserfunktion „Seite speichern" (Ctrl+S / Cmd+S)
   - Speichern als HTML-Datei für weitere Bearbeitung

### Browser-Druckfunktion

Die beste aktuelle Option für PDF-Export:

1. Öffnen Sie die Prüfung im Prüfungskomponisten
2. Drücken Sie `Ctrl+P` (Windows) oder `Cmd+P` (Mac)
3. Wählen Sie „In PDF speichern"
4. Konfigurieren Sie Seitenlayout, Ränder und andere Optionen
5. Speichern Sie die PDF-Datei

Diese Methode ist kostenlos und funktioniert in allen Browsern.

## Geplante Export-Formate (Roadmap)

Folgende Export-Funktionen sind für zukünftige Releases geplant:

### PDF-Export (Q2/Q3 2026)

**Automatischer PDF-Export mit Formatierung**

- Druckfertige Prüfung mit professionellem Layout
- Automatisches Deckblatt mit Metadaten (Kurs, Datum, Lehrer)
- Konfigurierbares Seitenlayout (A4/Letter)
- Optional: Lösungsblatt mit Antwortschlüssel und Erklärungen
- Seitennummern und Kopfzeilen
- Professionelle Schrift und Formatierung

**Nutzungsbeispiel:**
```
Prüfung: Sortieralgorithmen
Kurs: Informatik 2 (Wintersemester 2025)
Datum: 15.01.2026
Lehrperson: Dr. Müller
```

### JSON-Export (Q2/Q3 2026)

**Maschinenlesbares Format für Integration**

```json
{
  "exam": {
    "title": "Sortieralgorithmen",
    "created": "2026-01-15",
    "questions": [
      {
        "id": "q1",
        "text": "Was ist die Zeitkomplexität von...",
        "type": "multiple_choice",
        "options": ["A) O(n)", "B) O(n log n)", "C) O(n²)"],
        "correct_answer": "B",
        "explanation": "Quicksort hat...",
        "difficulty": 3,
        "bloom_level": "Apply",
        "source_documents": ["Skript_Kapitel_5.pdf"]
      }
    ]
  }
}
```

**Anwendungsfälle:**
- Integration in Custom-Prüfungssysteme
- Bulk-Upload in andere LMS-Plattformen
- Automatisierte Datenverarbeitung
- API-basierte Workflows

### Moodle XML-Export (Q3/Q4 2026)

**Direkter Import in Moodle LMS**

- Kompatibel mit Moodle 4.0+
- Automatische Konvertierung zu Moodle-Frage-Format
- Unterstützung für Multiple Choice, Short Answer, Essay
- Kategorisierung und Verschlagwortung
- Schwierigkeitsgrad und Punkte übernehmen

**Workflow:**
```
ExamCraft → Moodle XML Export → Moodle Question Bank → Prüfung
```

### Microsoft Word-Export (Q3 2026)

**Exportformat für Word-basierte Bearbeitung**

- `.docx` Format mit professionellem Template
- Editierbare Formatierung
- Optionale Antworttabelle und Bearbeitungsfeld
- Kompatibel mit MS Office und LibreOffice

### Google Forms-Export (Q4 2026)

**Automatischer Import in Google Forms**

- Erstellt neue Form mit allen Fragen
- Automatische Antwortverifikation
- Sharing und Kollabaration möglich
- Integrierte Auswertung und Statistiken

## Export-Optionen vergleichen

| Format | Verfügbar | Auswahl | Formatierung | Integration | Bearbeitung |
|--------|-----------|---------|-------------|-------------|------------|
| Manuelle Kopie | ✅ Jetzt | Einzeln | Minimal | Nein | Einfach |
| Browser-PDF | ✅ Jetzt | Alle | Gut | Nein | Nein |
| **PDF-Export** | Q2/Q3 2026 | Alle | Professionell | Nein | Nein |
| **JSON** | Q2/Q3 2026 | Alle | Keine | Ja | Ja |
| **Moodle XML** | Q3/Q4 2026 | Alle | Automatisch | Ja (Moodle) | Ja |
| **Word** | Q3 2026 | Alle | Editierbar | Teilweise | Ja |
| **Google Forms** | Q4 2026 | Alle | Automatisch | Ja (Google) | Ja |

## Best Practices beim Export

1. **Vor dem Export prüfen**: Stellen Sie sicher, dass alle Fragen in der Review Queue genehmigt sind
2. **Metadaten notieren**: Dokumentieren Sie Kurs, Datum und Lehrperson
3. **Backup erstellen**: Behalten Sie eine Kopie in ExamCraft, falls Sie später anpassen möchten
4. **Format auswählen**: Nutzen Sie das Format, das am besten zu Ihrem Workflow passt
5. **Testen vor Verwendung**: Überprüfen Sie die exportierte Prüfung vor Ausgabe an Lernende

## Häufige Fragen zum Export

**Kann ich eine teilweise Prüfung exportieren?**

Mit der manuellen Kopie oder Browser-PDF können Sie Fragen einzeln auswählen. Die geplanten Formate werden auch Auswahl-Optionen unterstützen.

**Werden Quellenangaben mitexportiert?**

Ja! Die Quelldokumente (Seitenzahlen) werden in Moodle XML, JSON und PDF mit exportiert.

**Ist mein exportierter Inhalt geschützt?**

Der Export ist eine Kopie. Nach dem Export können andere die Datei frei bearbeiten und weitergeben. Nutzen Sie Datenschutz auf Betriebssystemebene, falls nötig (z.B. PDF-Kennwort).

**Kann ich bereits exportierte Prüfungen aktualisieren?**

Nein, aber Sie können die Fragen im Prüfungskomponisten erneut generieren und exportieren. Die alte Version wird durch die neue ersetzt.
