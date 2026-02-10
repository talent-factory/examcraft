# 📚 ExamCraft AI - Benutzerhandbuch

> **Vollständige Anleitung zur Nutzung von ExamCraft AI für die automatische Generierung von Prüfungsaufgaben**

**Version**: 1.0.0
**Stand**: Oktober 2025
**Zielgruppe**: Dozenten, Lehrkräfte, Bildungseinrichtungen

---

## 📖 Inhaltsverzeichnis

1. [Erste Schritte](#erste-schritte)
2. [Dokumente hochladen](#dokumente-hochladen)
3. [Dokumentenbibliothek verwalten](#dokumentenbibliothek-verwalten)
4. [KI-Prüfungen erstellen](#ki-prüfungen-erstellen)
5. [RAG-basierte Prüfungen](#rag-basierte-prüfungen)
6. [Dokument ChatBot nutzen](#dokument-chatbot-nutzen)
7. [Prompt Management](#prompt-management)
8. [Tipps & Best Practices](#tipps--best-practices)
9. [Häufige Fragen (FAQ)](#häufige-fragen-faq)
10. [Fehlerbehebung](#fehlerbehebung)

---

## 🚀 Erste Schritte

### System-Anforderungen

**Browser-Unterstützung:**

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

**Empfohlene Auflösung:**

- Desktop: 1920x1080 oder höher
- Tablet: 1024x768 oder höher
- Mobile: 375x667 oder höher

### Zugriff auf ExamCraft AI

1. Öffnen Sie Ihren Browser
2. Navigieren Sie zu `<http://localhost:3000`> (lokale Installation)
3. Die Hauptseite wird automatisch geladen

### Benutzeroberfläche-Übersicht

Die ExamCraft AI Oberfläche besteht aus 6 Hauptbereichen:

```text
┌─────────────────────────────────────────────────────┐
│  ExamCraft AI - Header                              │
├─────────────────────────────────────────────────────┤
│  [KI-Prüfung] [Dokumente] [Bibliothek] [RAG]        │
│  [ChatBot] [Prompt Management]                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Hauptarbeitsbereich                                │
│  (Wechselt je nach ausgewähltem Tab)                │
│                                                     │
├─────────────────────────────────────────────────────┤
│  System Status                                      │
└─────────────────────────────────────────────────────┘
```

**Tab-Navigation:**

- **KI-Prüfung erstellen** - Generiere Fragen zu einem Thema
- **Dokumente hochladen** - Lade Kursmaterialien hoch
- **Dokumentenbibliothek** - Verwalte hochgeladene Dokumente
- **RAG-Prüfung erstellen** - Erstelle Fragen aus Dokumenten
- **Dokument ChatBot** - Chatte mit deinen Dokumenten
- **Prompt Management** - Verwalte AI-Prompts (Admin)

---

## 📤 Dokumente hochladen

### Unterstützte Dateiformate

ExamCraft AI unterstützt folgende Formate:

| Format | Erweiterung | Max. Größe | Besonderheiten |
|--------|-------------|------------|----------------|
| PDF | `.pdf` | 50 MB | Tabellen, Formeln, Bilder |
| Word | `.doc`, `.docx` | 25 MB | Formatierung erhalten |
| Markdown | `.md` | 10 MB | Code-Blöcke, LaTeX |
| Text | `.txt` | 5 MB | Plain Text |

### Schritt-für-Schritt Anleitung

**1. Tab "Dokumente hochladen" öffnen**

Klicken Sie auf den Tab "Dokumente hochladen" in der Navigation.

**2. Dateien auswählen**

Sie haben zwei Möglichkeiten:

- **Drag & Drop**: Ziehen Sie Dateien in den Upload-Bereich
- **Datei-Browser**: Klicken Sie auf "Dateien auswählen"

**3. Upload-Fortschritt überwachen**

Während des Uploads sehen Sie:

- Dateiname und Größe
- Fortschrittsbalken (0-100%)
- Status: "Wird verarbeitet..." → "Verarbeitet"

**4. Verarbeitung abwarten**

Nach dem Upload werden die Dokumente automatisch:

- Text extrahiert
- In semantische Chunks aufgeteilt
- In der Vektordatenbank indexiert
- Für RAG-Suche vorbereitet

**Verarbeitungszeit:**

- PDF (10 Seiten): ~30 Sekunden
- Word (20 Seiten): ~45 Sekunden
- Markdown (5 Seiten): ~15 Sekunden

### Best Practices für Uploads

✅ **Empfohlen:**

- Klare Dateinamen (z.B. `Algorithmen_Kapitel_3.pdf`)
- Strukturierte Dokumente mit Überschriften
- Hochwertige PDFs (nicht gescannt)
- Batch-Upload von zusammengehörigen Dokumenten

❌ **Vermeiden:**

- Gescannte PDFs ohne OCR
- Passwortgeschützte Dateien
- Sehr große Dateien (>50 MB)
- Duplikate

---

## 📚 Dokumentenbibliothek verwalten

### Übersicht

Die Dokumentenbibliothek zeigt alle hochgeladenen Dokumente in einer übersichtlichen Liste.

**Angezeigte Informationen:**

- Dateiname
- Upload-Datum
- Dateigröße
- Anzahl Seiten
- Verarbeitungsstatus
- Tags (falls vorhanden)

### Dokumente durchsuchen

**Suchfunktion:**

1. Geben Sie Suchbegriffe in das Suchfeld ein
2. Ergebnisse werden in Echtzeit gefiltert
3. Suche durchsucht: Dateiname, Tags, Inhalt

**Filter:**

- **Alle Formate** - Zeige alle Dokumente
- **PDF** - Nur PDF-Dateien
- **Word** - Nur Word-Dokumente
- **Markdown** - Nur Markdown-Dateien

### Dokumente auswählen

**Für RAG-Prüfung:**

1. Aktivieren Sie die Checkboxen neben den gewünschten Dokumenten
2. Klicken Sie auf "Prüfung aus Auswahl erstellen"
3. Sie werden zum RAG-Prüfungs-Creator weitergeleitet

**Mehrfachauswahl:**

- Einzeln: Klicken Sie auf einzelne Checkboxen
- Alle: Nutzen Sie "Alle auswählen" (falls verfügbar)

### Dokumente löschen

**Einzelnes Dokument:**

1. Klicken Sie auf das Löschen-Symbol (🗑️)
2. Bestätigen Sie die Sicherheitsabfrage
3. Dokument wird aus Bibliothek und Vektordatenbank entfernt

**Wichtig:** Gelöschte Dokumente können nicht wiederhergestellt werden!

---

## 🤖 KI-Prüfungen erstellen

### Themenbasierte Fragenerstellung

Diese Funktion generiert Fragen zu einem beliebigen Thema **ohne** hochgeladene Dokumente.

### Konfiguration

**1. Prüfungsthema eingeben**

Geben Sie ein spezifisches Thema ein:

- ✅ Gut: "Python Programmierung - Listen und Dictionaries"
- ✅ Gut: "Datenstrukturen - Heapsort Algorithmus"
- ❌ Schlecht: "Informatik" (zu allgemein)
- ❌ Schlecht: "Programmieren" (zu breit)

**2. Schwierigkeitsgrad wählen**

- **Einfach** - Grundlegendes Verständnis (Bloom: Remember, Understand)
- **Mittel** - Anwendung und Analyse (Bloom: Apply, Analyze)
- **Schwer** - Evaluation und Kreation (Bloom: Evaluate, Create)

**3. Anzahl Fragen festlegen**

- Minimum: 1 Frage
- Maximum: 20 Fragen
- Empfohlen: 5-10 Fragen pro Durchlauf

**4. Fragetypen auswählen**

Aktivieren Sie die gewünschten Typen:

- ☑️ **Multiple Choice** - 4 Antwortoptionen, 1 korrekt
- ☑️ **Offene Fragen** - Freitext-Antworten

**5. Sprache wählen**

- **Deutsch** - Fragen und Antworten auf Deutsch
- **English** - Questions and answers in English

### Generierung starten

1. Klicken Sie auf "Prüfung generieren"
2. Warten Sie 10-30 Sekunden (abhängig von Anzahl Fragen)
3. Fortschrittsanzeige: "Generiere Prüfung..."

### Ergebnis anzeigen

Nach erfolgreicher Generierung sehen Sie:

**Prüfungsübersicht:**

- Thema
- Anzahl Fragen
- Schwierigkeitsgrad
- Generierungszeit

**Einzelne Fragen:**

- Fragenummer
- Fragetext
- Antwortoptionen (bei Multiple Choice)
- Korrekte Antwort (grün markiert)
- Erklärung/Begründung
- Bloom-Level
- Schwierigkeitsgrad (1-5)

### Aktionen

**Neue Prüfung erstellen:**

- Klicken Sie auf "Neue Prüfung erstellen"
- Kehrt zum Konfigurationsformular zurück

**Exportieren:**

- Aktuell: Manuelles Kopieren
- Geplant (v1.1): PDF, JSON, Moodle XML Export

---

## 🔍 RAG-basierte Prüfungen

### Was ist RAG?

**RAG** (Retrieval-Augmented Generation) kombiniert:

- **Retrieval**: Semantische Suche in Ihren Dokumenten
- **Generation**: KI-basierte Fragenerstellung

**Vorteil**: Fragen sind direkt aus Ihren Kursmaterialien abgeleitet und enthalten Quellenangaben.

### Voraussetzungen

- Mindestens 1 Dokument hochgeladen
- Dokument erfolgreich verarbeitet
- Dokument in Bibliothek ausgewählt

### Schritt-für-Schritt

**1. Dokumente auswählen**

In der Dokumentenbibliothek:

- Wählen Sie 1-10 Dokumente aus
- Klicken Sie "Prüfung aus Auswahl erstellen"

**2. RAG-Konfiguration**

**Thema/Fokus:**

- Geben Sie einen spezifischen Fokus ein
- Beispiel: "Sortieralgorithmen Komplexität"
- Leer lassen für allgemeine Fragen

**Anzahl Fragen:**

- 1-20 Fragen möglich
- Empfohlen: 5-10 für beste Qualität

**Fragetypen:**

- Multiple Choice
- Offene Fragen
- True/False (falls verfügbar)

**Schwierigkeitsgrad:**

- Einfach / Mittel / Schwer

**Prompt-Auswahl (NEU):**

- Wählen Sie für jeden Fragetyp einen Prompt-Template
- **Live-Vorschau** zeigt den gerenderten Prompt
- **Template-Variablen** werden automatisch befüllt:
  - `topic` - aus Thema/Fokus-Feld
  - `difficulty` - aus Schwierigkeitsgrad-Dropdown
  - `language` - aus Sprache-Dropdown
  - `context` - aus ausgewählten Dokumenten
- **Zusätzliche Variablen** können manuell angepasst werden
- Beispiel: `bloom_level`, `question_count`, `include_examples`

**Tipp**: Nutzen Sie die Live-Vorschau, um zu sehen, wie der finale Prompt aussieht, bevor Sie die Generierung starten!

**3. Generierung starten**

- Klicken Sie "RAG-Prüfung generieren"
- Wartezeit: 20-60 Sekunden
- Fortschritt wird angezeigt

**4. Ergebnis prüfen**

Jede Frage enthält:

- **Fragentext**
- **Antwortoptionen**
- **Korrekte Antwort**
- **Erklärung**
- **Quelldokumente** (mit Seitenzahl)
- **Confidence Score** (0-1)

### Qualitätsindikatoren

**Confidence Score:**

- 0.9-1.0: Sehr hohe Qualität ✅
- 0.7-0.9: Gute Qualität ✅
- 0.5-0.7: Akzeptabel ⚠️
- <0.5: Überprüfung empfohlen ❌

**Quellenangaben:**

- Jede Frage zeigt verwendete Dokumente
- Klicken Sie auf Quelle für Details
- Überprüfen Sie Relevanz

---

## 💬 Dokument ChatBot nutzen

Der ChatBot ermöglicht interaktive Gespräche mit Ihren hochgeladenen Dokumenten - ähnlich wie NotebookLM.

### Dokument auswählen

**1. ChatBot-Tab öffnen**

Klicken Sie auf "Dokument ChatBot" in der Navigation.

**2. Dokument wählen**

- Dropdown-Menü zeigt alle verfügbaren Dokumente
- Wählen Sie das gewünschte Dokument
- ChatBot lädt Kontext (2-5 Sekunden)

### Chat starten

**Beispiel-Fragen:**

- "Erkläre mir den Heapsort Algorithmus"
- "Was sind die Unterschiede zwischen Quicksort und Mergesort?"
- "Welche Komplexität hat Dijkstra's Algorithmus?"
- "Fasse Kapitel 3 zusammen"

**Tipps für gute Fragen:**

- ✅ Spezifisch und klar formuliert
- ✅ Bezug auf Dokumentinhalt
- ✅ Folge-Fragen möglich
- ❌ Zu allgemeine Fragen
- ❌ Themen außerhalb des Dokuments

### Antworten verstehen

**Jede Antwort enthält:**

- **Haupttext** - KI-generierte Antwort
- **Quellen** - Relevante Textabschnitte
- **Confidence** - Zuverlässigkeit (0-1)

**Confidence-Interpretation:**

- `>0.8`: Sehr zuverlässig
- `0.6-0.8`: Zuverlässig
- `<0.6`: Mit Vorsicht verwenden

### Chat-Historie

**Funktionen:**

- Alle Nachrichten werden gespeichert
- Scrollen Sie nach oben für ältere Nachrichten
- Kontext bleibt erhalten (Multi-Turn)

**Neue Konversation:**

- Wählen Sie ein anderes Dokument
- Chat-Historie wird zurückgesetzt

### Export (geplant v1.1)

- Markdown-Export
- PDF-Export
- Teilen-Funktion

---

## 🎛️ Prompt Management

Das Prompt Management ermöglicht Administratoren die Verwaltung aller AI-Prompts ohne Code-Änderungen.

**Zugriff:**

- Tab "Prompt Management" in der Navigation
- Nur für Administratoren sichtbar

### Prompt Library

**Ansicht:**

- Grid-Layout mit allen Prompts
- Suchfunktion
- Kategorie-Filter

**Angezeigte Informationen:**

- Prompt-Name
- Beschreibung
- Kategorie (System/User/Template)
- Use Case
- Version
- Status (Aktiv/Inaktiv)
- Tags
- Verwendungen

**Aktionen:**

- **Bearbeiten** - Prompt editieren
- **Versionen** - Version History anzeigen
- **Löschen** - Prompt entfernen

### Prompt Editor

**Neuen Prompt erstellen:**

1. Klicken Sie "Neuer Prompt"
2. Füllen Sie Formular aus
3. Speichern

**Formularfelder:**

- **Name** - Eindeutiger Identifier (z.B. `system_prompt_question_generation`)
- **Beschreibung** - Kurze Erklärung
- **Kategorie** - System Prompt / User Prompt / Few-Shot Example / Template
- **Use Case** - Verwendungszweck (z.B. `question_generation`)
- **Content** - Prompt-Text (Markdown unterstützt)
- **Tags** - Schlagwörter für Suche
- **Aktiv** - Sofort aktivieren?

**Tabs:**

- **Bearbeiten** - Markdown-Editor
- **Vorschau** - Gerenderte Ansicht

**Template-Variablen:**

- Syntax: `{variable_name}`
- Beispiel: `Generiere {count} Fragen zum Thema {topic}`
- Werden zur Laufzeit ersetzt

### Version History

**Funktionen:**

- Alle Versionen eines Prompts anzeigen
- Vergleich zwischen Versionen
- Rollback zu alter Version
- Aktivierung/Deaktivierung

**Versionierung:**

- Automatische Versionsnummern (v1, v2, v3...)
- Nur eine Version kann aktiv sein
- Alte Versionen bleiben erhalten

**Rollback:**

1. Öffnen Sie Version History
2. Wählen Sie gewünschte Version
3. Klicken Sie "Aktivieren"
4. Bestätigen Sie

### Usage Analytics

**Metriken:**

- **Verwendungen** - Anzahl Aufrufe
- **Erfolgsrate** - % erfolgreiche Generierungen
- **Ø Latenz** - Durchschnittliche Antwortzeit
- **Tokens Total** - Gesamtverbrauch

**Verwendungsverlauf:**

- Letzte 100 Verwendungen
- Timestamp
- Use Case
- Tokens
- Latenz
- Erfolg/Fehler

### Semantic Search

**Prompt-Suche:**

1. Wechseln Sie zu "Semantic Search" Tab
2. Geben Sie Suchanfrage ein
3. Optional: Filter setzen
4. Klicken Sie "Suchen"

**Filter:**

- Kategorie
- Use Case
- Anzahl Ergebnisse (1-20)
- Similarity Threshold (0-1)

**Ergebnisse:**

- Sortiert nach Relevanz
- Similarity Score angezeigt
- Klicken für Details

---

## 💡 Tipps & Best Practices

### Dokumenten-Upload

**Optimale Vorbereitung:**

1. Strukturieren Sie Dokumente mit klaren Überschriften
2. Verwenden Sie konsistente Formatierung
3. Fügen Sie Metadaten hinzu (Titel, Autor, Datum)
4. Vermeiden Sie Wasserzeichen und Hintergrundbilder

**Batch-Upload:**

- Laden Sie zusammengehörige Dokumente gemeinsam hoch
- Beispiel: Alle Kapitel eines Lehrbuchs
- Erleichtert spätere RAG-Prüfungen

### Fragenerstellung

**Themenformulierung:**

- Spezifisch statt allgemein
- Kontext angeben
- Bloom-Level im Hinterkopf behalten

**Beispiele:**

- ✅ "Python Listen - Methoden append(), extend(), insert()"
- ✅ "Algorithmen - Zeitkomplexität von Sortierverfahren"
- ❌ "Python" (zu breit)
- ❌ "Programmierung" (zu allgemein)

**Qualitätskontrolle:**

- Überprüfen Sie generierte Fragen
- Achten Sie auf Confidence Scores
- Passen Sie Schwierigkeitsgrad an
- Nutzen Sie Quellenangaben

### RAG-Prüfungen

**Dokumentenauswahl:**

- Wählen Sie relevante Dokumente
- 3-5 Dokumente optimal
- Zu viele Dokumente → niedrigere Qualität

**Fokus setzen:**

- Geben Sie spezifischen Fokus an
- Hilft bei der Relevanz
- Verbessert Confidence Scores

### ChatBot-Nutzung

**Effektive Fragen:**

- Beginnen Sie mit Überblicksfragen
- Vertiefen Sie schrittweise
- Nutzen Sie Folge-Fragen
- Referenzieren Sie vorherige Antworten

**Beispiel-Dialog:**

```text
User: "Was ist Heapsort?"
Bot: [Erklärt Heapsort]

User: "Wie unterscheidet sich das von Quicksort?"
Bot: [Vergleicht beide Algorithmen]

User: "Welcher ist effizienter für große Datenmengen?"
Bot: [Analysiert Komplexität]
```

---

## ❓ Häufige Fragen (FAQ)

### Allgemein

**Q: Wie viele Dokumente kann ich hochladen?**
A: Abhängig von Ihrem Plan:

- Free: 5 Dokumente
- Starter: 50 Dokumente
- Professional: Unbegrenzt

**Q: Welche Sprachen werden unterstützt?**
A: Aktuell Deutsch und Englisch. Weitere Sprachen geplant.

**Q: Kann ich Fragen exportieren?**
A: Aktuell nur manuell. PDF/JSON/Moodle XML Export kommt in v1.1.

### Technisch

**Q: Warum dauert die Verarbeitung so lange?**
A: Große PDFs (>20 Seiten) benötigen mehr Zeit. Gescannte PDFs noch länger.

**Q: Was passiert mit meinen Daten?**
A: Alle Daten werden verschlüsselt gespeichert. Siehe [Datenschutz](PRIVACY.md).

**Q: Kann ich offline arbeiten?**
A: Nein, ExamCraft AI benötigt Internetverbindung für AI-Funktionen.

### Fehlerbehebung

**Q: Upload schlägt fehl - was tun?**
A:

1. Prüfen Sie Dateigröße (<50 MB)
2. Prüfen Sie Format (PDF, DOC, MD, TXT)
3. Versuchen Sie es erneut
4. Kontaktieren Sie Support

**Q: Fragen sind von schlechter Qualität?**
A:

1. Überprüfen Sie Themenformulierung
2. Wählen Sie passenden Schwierigkeitsgrad
3. Bei RAG: Prüfen Sie Dokumentenauswahl
4. Nutzen Sie Confidence Scores

**Q: ChatBot antwortet nicht korrekt?**
A:

1. Formulieren Sie Frage spezifischer
2. Prüfen Sie, ob Thema im Dokument enthalten
3. Wählen Sie anderes Dokument
4. Starten Sie neue Konversation

---

## 🔧 Fehlerbehebung

### Upload-Probleme

**Symptom**: "Upload fehlgeschlagen"

**Lösungen:**

1. Prüfen Sie Internetverbindung
2. Reduzieren Sie Dateigröße
3. Konvertieren Sie Format
4. Leeren Sie Browser-Cache
5. Versuchen Sie anderen Browser

### Generierungs-Fehler

**Symptom**: "Fehler bei der Generierung"

**Lösungen:**

1. Warten Sie 30 Sekunden und versuchen Sie erneut
2. Reduzieren Sie Anzahl Fragen
3. Vereinfachen Sie Thema
4. Prüfen Sie Systemstatus

### Performance-Probleme

**Symptom**: Langsame Ladezeiten

**Lösungen:**

1. Schließen Sie andere Browser-Tabs
2. Leeren Sie Browser-Cache
3. Aktualisieren Sie Browser
4. Prüfen Sie Internetgeschwindigkeit

### Anzeige-Fehler

**Symptom**: Elemente werden nicht korrekt angezeigt

**Lösungen:**

1. Aktualisieren Sie Seite (F5)
2. Leeren Sie Cache (Strg+Shift+R)
3. Prüfen Sie Browser-Version
4. Deaktivieren Sie Browser-Erweiterungen

---

## 📞 Support & Kontakt

**Technischer Support:**

- Email: <support@examcraft.ai>
- Response Time: <24h (Werktage)

**Dokumentation:**

- [Vollständige Docs](https://docs.examcraft.ai)
- [API Reference](https://api.examcraft.ai/docs)
- [Video Tutorials](https://youtube.com/examcraft)

**Community:**

- [Discord Server](https://discord.gg/examcraft)
- [GitHub Discussions](https://github.com/examcraft/discussions)

---

**Letzte Aktualisierung**: Oktober 2025
**Version**: 1.0.0
**Lizenz**: MIT License
