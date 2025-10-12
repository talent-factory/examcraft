# 📸 Screenshot-Erstellungs-Checkliste

> **Schritt-für-Schritt Anleitung zur Erstellung aller 19 Screenshots**

**Browser**: Chrome/Firefox  
**Auflösung**: 1920x1080  
**Zoom**: 100%  
**URL**: <http://localhost:3000>

---

## ✅ Vorbereitung

### 1. Browser-Setup

```bash
# Öffne Browser im Inkognito-Modus
# Chrome: Cmd+Shift+N (macOS) / Ctrl+Shift+N (Windows)
# Firefox: Cmd+Shift+P (macOS) / Ctrl+Shift+P (Windows)
```

- [ ] Browser im Inkognito-Modus geöffnet
- [ ] Fenster auf 1920x1080 skaliert
- [ ] Zoom auf 100% gesetzt
- [ ] Browser-Erweiterungen deaktiviert

### 2. Daten vorbereiten

```bash
# Seed-Daten laden
docker-compose exec backend python scripts/seed_prompts.py

# Beispiel-Dokumente hochladen (falls noch nicht vorhanden)
# Nutze PDFs aus demo/ Verzeichnis
```

- [ ] Seed-Prompts geladen
- [ ] 3-5 Beispiel-PDFs hochgeladen
- [ ] 1-2 Beispiel-Prüfungen generiert
- [ ] 1-2 ChatBot-Konversationen erstellt

---

## 📸 Screenshot-Erstellung

### Screenshot 01: Hauptnavigation ✅

**Datei**: `docs/screenshots/01_main_navigation.png`

**Schritte:**

1. Öffne <http://localhost:3000>
2. Warte bis Seite vollständig geladen (alle Tabs sichtbar)
3. Screenshot des gesamten Browser-Fensters
4. **macOS**: `Cmd+Shift+4` → `Space` → Klick auf Browser-Fenster
5. **Windows**: `Win+Shift+S` → Fenster auswählen

**Erwartetes Ergebnis:**

- Header mit "ExamCraft AI" Logo
- 6 Tabs sichtbar: KI-Prüfung, Dokumente, Bibliothek, RAG, ChatBot, Prompt Management
- Aktueller Tab: "KI-Prüfung erstellen" (Standard)
- System Status Footer

**Checkliste:**

- [ ] Alle 6 Tabs sichtbar
- [ ] Header vollständig
- [ ] Footer sichtbar
- [ ] Keine Browser-UI (Adressleiste, etc.)
- [ ] Datei gespeichert als `01_main_navigation.png`

---

### Screenshot 02: KI-Prüfung Konfiguration ✅

**Datei**: `docs/screenshots/02_ai_exam_config.png`

**Schritte:**

1. Klicke auf Tab "KI-Prüfung erstellen" (falls nicht bereits aktiv)
2. Fülle Formular mit Beispieldaten:
   - **Thema**: "Python Programmierung - Listen und Dictionaries"
   - **Schwierigkeitsgrad**: Mittel
   - **Anzahl Fragen**: 5
   - **Fragetypen**: Beide Checkboxen aktiviert
   - **Sprache**: Deutsch
3. Screenshot **vor** Klick auf "Prüfung generieren"
4. **macOS**: `Cmd+Shift+4` → Bereich auswählen
5. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Formular vollständig ausgefüllt
- Alle Eingabefelder sichtbar
- "Prüfung generieren" Button sichtbar (noch nicht geklickt)

**Checkliste:**

- [ ] Thema eingegeben
- [ ] Schwierigkeitsgrad ausgewählt
- [ ] Anzahl Fragen gesetzt (5)
- [ ] Beide Fragetypen aktiviert
- [ ] Sprache Deutsch ausgewählt
- [ ] Button sichtbar
- [ ] Datei gespeichert als `02_ai_exam_config.png`

---

### Screenshot 03: KI-Prüfung Ergebnis ✅

**Datei**: `docs/screenshots/03_ai_exam_result.png`

**Schritte:**

1. Klicke "Prüfung generieren" (mit Daten aus Screenshot 02)
2. Warte 10-30 Sekunden bis Generierung abgeschlossen
3. Scrolle zu den ersten 2-3 Fragen
4. Screenshot der Ergebnisanzeige
5. **macOS**: `Cmd+Shift+4` → Bereich auswählen
6. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Prüfungsübersicht (Thema, Anzahl, Schwierigkeit)
- Mindestens 2 vollständige Fragen sichtbar
- Jede Frage zeigt:
  - Fragenummer
  - Fragetext
  - Antwortoptionen (bei Multiple Choice)
  - Korrekte Antwort (grün markiert)
  - Erklärung
  - Bloom-Level Badge
  - Schwierigkeitsgrad (Sterne)

**Checkliste:**

- [ ] Prüfungsübersicht sichtbar
- [ ] Mindestens 2 Fragen vollständig sichtbar
- [ ] Korrekte Antwort grün markiert
- [ ] Bloom-Level Badge sichtbar
- [ ] "Neue Prüfung erstellen" Button sichtbar
- [ ] Datei gespeichert als `03_ai_exam_result.png`

---

### Screenshot 04: Dokument Upload (leer) ✅

**Datei**: `docs/screenshots/04_document_upload_empty.png`

**Schritte:**

1. Klicke auf Tab "Dokumente hochladen"
2. Screenshot des leeren Upload-Bereichs
3. **macOS**: `Cmd+Shift+4` → Bereich auswählen
4. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Upload-Box mit Drag & Drop Zone
- "Dateien auswählen" Button
- Hinweis auf unterstützte Formate
- Hinweis auf max. Dateigröße

**Checkliste:**

- [ ] Upload-Box sichtbar
- [ ] "Dateien auswählen" Button sichtbar
- [ ] Format-Hinweis sichtbar
- [ ] Größen-Hinweis sichtbar
- [ ] Datei gespeichert als `04_document_upload_empty.png`

---

### Screenshot 05: Dokument Upload (in Progress) ✅

**Datei**: `docs/screenshots/05_document_upload_progress.png`

**Schritte:**

1. Wähle eine PDF-Datei aus (z.B. aus `demo/` Verzeichnis)
2. **Schnell**: Screenshot während Upload/Verarbeitung (ca. 50%)
3. **Timing ist wichtig!** Bereite Screenshot-Tool vor
4. **macOS**: `Cmd+Shift+4` bereithalten
5. **Windows**: `Win+Shift+S` bereithalten

**Erwartetes Ergebnis:**

- Dateiname und Größe angezeigt
- Fortschrittsbalken bei ca. 50%
- Status: "Wird verarbeitet..."
- Spinner-Animation (optional)

**Checkliste:**

- [ ] Dateiname sichtbar
- [ ] Fortschrittsbalken sichtbar (nicht 0% oder 100%)
- [ ] Status "Wird verarbeitet..." sichtbar
- [ ] Datei gespeichert als `05_document_upload_progress.png`

**Tipp**: Falls zu schnell, nutze größere PDF oder wiederhole Upload

---

### Screenshot 06: Dokument Upload (Erfolg) ✅

**Datei**: `docs/screenshots/06_document_upload_success.png`

**Schritte:**

1. Warte bis Upload vollständig abgeschlossen
2. Screenshot der Erfolgsanzeige
3. **macOS**: `Cmd+Shift+4` → Bereich auswählen
4. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Grünes Häkchen ✅
- Status: "Verarbeitet"
- Anzahl extrahierte Seiten
- "Weiteres Dokument hochladen" Button (optional)

**Checkliste:**

- [ ] Grünes Häkchen sichtbar
- [ ] Status "Verarbeitet" sichtbar
- [ ] Seitenanzahl angezeigt
- [ ] Datei gespeichert als `06_document_upload_success.png`

---

### Screenshot 07: Dokumentenbibliothek ✅

**Datei**: `docs/screenshots/07_document_library.png`

**Schritte:**

1. Klicke auf Tab "Dokumentenbibliothek"
2. Stelle sicher, dass 3-5 Dokumente vorhanden sind
3. Screenshot der gesamten Bibliothek
4. **macOS**: `Cmd+Shift+4` → Bereich auswählen
5. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Suchfeld oben
- Format-Filter Dropdown
- Liste mit 3-5 Dokumenten
- Jedes Dokument zeigt:
  - Dateiname
  - Upload-Datum
  - Dateigröße
  - Anzahl Seiten
  - Checkbox
  - Löschen-Button

**Checkliste:**

- [ ] Suchfeld sichtbar
- [ ] Filter sichtbar
- [ ] Mindestens 3 Dokumente sichtbar
- [ ] Alle Spalten sichtbar
- [ ] "Prüfung aus Auswahl erstellen" Button sichtbar
- [ ] Datei gespeichert als `07_document_library.png`

---

### Screenshot 08: Dokumentenauswahl ✅

**Datei**: `docs/screenshots/08_document_selection.png`

**Schritte:**

1. In Dokumentenbibliothek: Wähle 2-3 Dokumente aus (Checkboxen aktivieren)
2. Screenshot mit aktivierten Checkboxen
3. **macOS**: `Cmd+Shift+4` → Bereich auswählen
4. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- 2-3 aktivierte Checkboxen
- Ausgewählte Zeilen hervorgehoben (optional)
- "Prüfung aus Auswahl erstellen" Button aktiv

**Checkliste:**

- [ ] 2-3 Checkboxen aktiviert
- [ ] Zeilen hervorgehoben
- [ ] Button aktiv/hervorgehoben
- [ ] Datei gespeichert als `08_document_selection.png`

---

### Screenshot 09: RAG-Prüfung Konfiguration ✅

**Datei**: `docs/screenshots/09_rag_exam_config.png`

**Schritte:**

1. Klicke "Prüfung aus Auswahl erstellen" (oder Tab "RAG-Prüfung erstellen")
2. Fülle Formular mit Beispieldaten:
   - **Fokus**: "Sortieralgorithmen Komplexität"
   - **Anzahl Fragen**: 5
   - **Fragetypen**: Multiple Choice
   - **Schwierigkeit**: Mittel
3. Screenshot **vor** Klick auf "RAG-Prüfung generieren"
4. **macOS**: `Cmd+Shift+4` → Bereich auswählen
5. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Ausgewählte Dokumente angezeigt
- Formular ausgefüllt
- "RAG-Prüfung generieren" Button sichtbar

**Checkliste:**

- [ ] Ausgewählte Dokumente sichtbar
- [ ] Fokus eingegeben
- [ ] Anzahl Fragen gesetzt
- [ ] Fragetyp ausgewählt
- [ ] Schwierigkeit ausgewählt
- [ ] Button sichtbar
- [ ] Datei gespeichert als `09_rag_exam_config.png`

---

### Screenshot 10: RAG-Prüfung Ergebnis ✅

**Datei**: `docs/screenshots/10_rag_exam_result.png`

**Schritte:**

1. Klicke "RAG-Prüfung generieren"
2. Warte 20-60 Sekunden bis abgeschlossen
3. Screenshot einer Frage **mit Quellenangaben**
4. **macOS**: `Cmd+Shift+4` → Bereich auswählen
5. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Frage mit Antwortoptionen
- Korrekte Antwort (grün)
- Erklärung
- **Quelldokumente** mit Seitenzahl
- **Confidence Score** (0-1)
- Bloom-Level Badge

**Checkliste:**

- [ ] Frage vollständig sichtbar
- [ ] Quellenangaben sichtbar
- [ ] Confidence Score sichtbar
- [ ] Bloom-Level Badge sichtbar
- [ ] Datei gespeichert als `10_rag_exam_result.png`

---

### Screenshot 11: ChatBot Übersicht ✅

**Datei**: `docs/screenshots/11_chatbot_overview.png`

**Schritte:**

1. Klicke auf Tab "Dokument ChatBot"
2. Wähle ein Dokument aus Dropdown
3. Screenshot der leeren Chat-Oberfläche
4. **macOS**: `Cmd+Shift+4` → Bereich auswählen
5. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Dokument-Auswahl Dropdown (mit ausgewähltem Dokument)
- Leerer Chat-Bereich
- Eingabefeld für Fragen
- "Senden" Button
- "Chat exportieren" Button (optional)

**Checkliste:**

- [ ] Dropdown mit Dokument sichtbar
- [ ] Chat-Bereich leer
- [ ] Eingabefeld sichtbar
- [ ] Senden-Button sichtbar
- [ ] Datei gespeichert als `11_chatbot_overview.png`

---

### Screenshot 12: ChatBot Konversation ✅

**Datei**: `docs/screenshots/12_chatbot_conversation.png`

**Schritte:**

1. Stelle Frage: "Erkläre mir den Heapsort Algorithmus"
2. Warte auf Antwort (10-30 Sekunden)
3. Screenshot der Konversation
4. **macOS**: `Cmd+Shift+4` → Bereich auswählen
5. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- User-Nachricht (rechts, blau)
- Bot-Antwort (links, grau)
- Quellenangaben unter Antwort
- Confidence Score
- Timestamp (optional)

**Checkliste:**

- [ ] User-Nachricht sichtbar
- [ ] Bot-Antwort sichtbar
- [ ] Quellenangaben sichtbar
- [ ] Confidence Score sichtbar
- [ ] Datei gespeichert als `12_chatbot_conversation.png`

---

### Screenshot 13: Chat Export ✅

**Datei**: `docs/screenshots/13_chatbot_export.png`

**Schritte:**

1. Klicke "Chat exportieren" Button
2. Screenshot des Export-Dialogs
3. **macOS**: `Cmd+Shift+4` → Bereich auswählen
4. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Export-Dialog geöffnet
- Format-Auswahl (Markdown/PDF)
- Dateiname-Eingabe
- "Exportieren" Button

**Checkliste:**

- [ ] Dialog geöffnet
- [ ] Format-Auswahl sichtbar
- [ ] Dateiname-Feld sichtbar
- [ ] Exportieren-Button sichtbar
- [ ] Datei gespeichert als `13_chatbot_export.png`

**Hinweis**: Falls Export-Feature noch nicht implementiert, Screenshot überspringen

---

### Screenshot 14: Prompt Library ✅

**Datei**: `docs/screenshots/14_prompt_library.png`

**Schritte:**

1. Klicke auf Tab "Prompt Management"
2. Stelle sicher, dass 4-6 Prompts vorhanden sind (Seed-Daten)
3. Screenshot des Grid-Layouts
4. **macOS**: `Cmd+Shift+4` → Bereich auswählen
5. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Suchfeld oben
- Kategorie-Filter Dropdown
- Grid mit 4-6 Prompt-Karten
- Jede Karte zeigt:
  - Name
  - Beschreibung
  - Kategorie-Badge (farbcodiert)
  - Tags
  - Verwendungen
  - Aktiv/Inaktiv Status
  - Aktionen (Bearbeiten, Versionen, Löschen)

**Checkliste:**

- [ ] Suchfeld sichtbar
- [ ] Filter sichtbar
- [ ] Mindestens 4 Prompt-Karten sichtbar
- [ ] Alle Informationen pro Karte sichtbar
- [ ] Aktionen-Buttons sichtbar
- [ ] Datei gespeichert als `14_prompt_library.png`

---

### Screenshot 15: Prompt Editor ✅

**Datei**: `docs/screenshots/15_prompt_editor.png`

**Schritte:**

1. Klicke "Neuer Prompt" oder "Bearbeiten" bei einem Prompt
2. Fülle Formular mit Beispieldaten (oder nutze bestehende)
3. Stelle sicher, dass "Bearbeiten" Tab aktiv ist
4. Screenshot des Editors
5. **macOS**: `Cmd+Shift+4` → Bereich auswählen
6. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Name Eingabefeld
- Beschreibung Textarea
- Kategorie Dropdown
- Use Case Eingabe
- Tags Eingabe mit Chips
- Content Editor (Markdown)
- Tabs: Bearbeiten / Vorschau
- Aktiv Toggle
- "Speichern" Button

**Checkliste:**

- [ ] Alle Formularfelder sichtbar
- [ ] "Bearbeiten" Tab aktiv
- [ ] Content Editor sichtbar
- [ ] Aktiv Toggle sichtbar
- [ ] Speichern-Button sichtbar
- [ ] Datei gespeichert als `15_prompt_editor.png`

---

### Screenshot 16: Prompt Vorschau ✅

**Datei**: `docs/screenshots/16_prompt_preview.png`

**Schritte:**

1. Im Editor: Wechsle zu "Vorschau" Tab
2. Screenshot der gerenderten Markdown-Ansicht
3. **macOS**: `Cmd+Shift+4` → Bereich auswählen
4. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Gerenderte Markdown-Ansicht
- Formatierung sichtbar (Überschriften, Listen, Code)
- Template-Variablen hervorgehoben (optional)

**Checkliste:**

- [ ] "Vorschau" Tab aktiv
- [ ] Markdown gerendert
- [ ] Formatierung korrekt
- [ ] Datei gespeichert als `16_prompt_preview.png`

---

### Screenshot 17: Version History ✅

**Datei**: `docs/screenshots/17_version_history.png`

**Schritte:**

1. Klicke "Versionen" bei einem Prompt (in Prompt Library)
2. Screenshot der Version History Tabelle
3. **macOS**: `Cmd+Shift+4` → Bereich auswählen
4. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Tabelle mit allen Versionen
- Spalten: Version, Status, Beschreibung, Erstellt am, Aktionen
- Mindestens 2-3 Versionen sichtbar
- Aktionen: Vorschau, Aktivieren

**Checkliste:**

- [ ] Tabelle sichtbar
- [ ] Alle Spalten sichtbar
- [ ] Mindestens 2 Versionen sichtbar
- [ ] Aktionen-Buttons sichtbar
- [ ] Datei gespeichert als `17_version_history.png`

---

### Screenshot 18: Usage Analytics ✅

**Datei**: `docs/screenshots/18_usage_analytics.png`

**Schritte:**

1. Klicke "Analytics" oder öffne Usage Analytics für einen Prompt
2. Screenshot des Analytics-Dashboards
3. **macOS**: `Cmd+Shift+4` → Bereich auswählen
4. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- 4 Metrik-Karten:
  - Verwendungen (Zahl)
  - Erfolgsrate (% mit Farbindikator)
  - Ø Latenz (ms)
  - Tokens Total (Zahl)
- Verwendungsverlauf Tabelle

**Checkliste:**

- [ ] Alle 4 Metrik-Karten sichtbar
- [ ] Verwendungsverlauf Tabelle sichtbar
- [ ] Farbindikatoren sichtbar
- [ ] Datei gespeichert als `18_usage_analytics.png`

---

### Screenshot 19: Semantic Search ✅

**Datei**: `docs/screenshots/19_semantic_search.png`

**Schritte:**

1. Wechsle zu "Semantic Search" Tab (in Prompt Management)
2. Gib Suchanfrage ein: "Generiere Multiple Choice Fragen"
3. Klicke "Suchen"
4. Screenshot mit Suchergebnissen
5. **macOS**: `Cmd+Shift+4` → Bereich auswählen
6. **Windows**: `Win+Shift+S` → Bereich auswählen

**Erwartetes Ergebnis:**

- Suchanfrage Eingabefeld (ausgefüllt)
- Filter (Kategorie, Use Case)
- Advanced Settings (Limit, Score Threshold)
- Ergebnisliste mit:
  - Prompt-Name
  - Similarity Score (farbcodiert)
  - Beschreibung
  - Tags

**Checkliste:**

- [ ] Suchanfrage eingegeben
- [ ] Filter sichtbar
- [ ] Advanced Settings sichtbar
- [ ] Ergebnisliste mit Scores sichtbar
- [ ] Farbcodierung sichtbar
- [ ] Datei gespeichert als `19_semantic_search.png`

---

## 📋 Finale Checkliste

### Alle Screenshots erstellt?

- [ ] 01 - Hauptnavigation
- [ ] 02 - KI-Prüfung Konfiguration
- [ ] 03 - KI-Prüfung Ergebnis
- [ ] 04 - Dokument Upload (leer)
- [ ] 05 - Dokument Upload (in Progress)
- [ ] 06 - Dokument Upload (Erfolg)
- [ ] 07 - Dokumentenbibliothek
- [ ] 08 - Dokumentenauswahl
- [ ] 09 - RAG-Prüfung Konfiguration
- [ ] 10 - RAG-Prüfung Ergebnis
- [ ] 11 - ChatBot Übersicht
- [ ] 12 - ChatBot Konversation
- [ ] 13 - Chat Export
- [ ] 14 - Prompt Library
- [ ] 15 - Prompt Editor
- [ ] 16 - Prompt Vorschau
- [ ] 17 - Version History
- [ ] 18 - Usage Analytics
- [ ] 19 - Semantic Search

### Qualitätskontrolle

- [ ] Alle Screenshots im PNG-Format
- [ ] Auflösung mindestens 1920px Breite
- [ ] Dateigröße <500 KB pro Screenshot
- [ ] Namenskonvention korrekt (`XX_beschreibung.png`)
- [ ] Alle Screenshots in `docs/screenshots/` gespeichert
- [ ] Keine Browser-UI sichtbar (Adressleiste, etc.)
- [ ] Keine persönlichen Daten sichtbar

### Nachbearbeitung (optional)

- [ ] Zuschneiden auf relevanten Bereich
- [ ] Komprimieren (falls >500 KB)
- [ ] Annotationen hinzufügen (Pfeile, Nummern)
- [ ] Hervorhebungen für wichtige Features

---

## 🎯 Nächste Schritte

Nach Erstellung aller Screenshots:

1. **Dokumentation aktualisieren**
   - USER_GUIDE.md mit Screenshots ergänzen
   - ADMIN_PROMPT_MANAGEMENT.md mit Screenshots ergänzen

2. **Git Commit**

   ```bash
   git add docs/screenshots/*.png
   git commit -m "📸 docs: Füge 19 Screenshots für Benutzerdokumentation hinzu"
   git push origin develop
   ```

3. **Qualitätskontrolle**
   - Alle Screenshots in Dokumentation eingebunden
   - Links funktionieren
   - Bildunterschriften vorhanden

---

**Geschätzte Zeit**: 30-45 Minuten  
**Schwierigkeit**: Einfach  
**Voraussetzungen**: Laufende ExamCraft AI Instanz

Viel Erfolg! 🚀
