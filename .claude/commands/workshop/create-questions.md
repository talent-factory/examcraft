# Create Programming Questions from Academic Materials

Erstelle qualitativ hochwertige Prüfungsfragen für BSc Informatik Studierende basierend auf bereitgestellten akademischen Materialien (typischerweise PDF-Dokumente) mit automatischer Musterlösungsgenerierung.

## 🎯 Aufgabe

Du sollst aus den bereitgestellten Unterlagen Prüfungsfragen erstellen, die:

1. **Akademische PDF-Dokumente analysieren**:
   - Lese und analysiere alle PDF-Dateien im `./demo/` Verzeichnis
   - Identifiziere relevante Konzepte, Algorithmen und Datenstrukturen
   - Extrahiere Code-Beispiele und theoretische Grundlagen
   - Verstehe den akademischen Kontext und das Niveau

2. **Prüfungsfragen entwickeln**:
   - **Format**: Code-Vervollständigung (fehlende Methoden ergänzen)
   - **Sprache**: Python (BSc Informatik Standard)
   - **Schwierigkeit**: BSc-Niveau im Modul "Datenstrukturen und Algorithmen"
   - **Typ**: Praxisorientierte Programmieraufgaben mit Verständnisfragen

3. **Qualitätssicherung implementieren**:
   - Validiere, dass Fragen das PDF-Material korrekt reflektieren
   - Stelle sicher, dass Code syntaktisch korrekt ist
   - Prüfe, dass Schwierigkeitsgrad angemessen ist
   - Verifiziere Vollständigkeit und Korrektheit der Musterlösungen

4. **Strukturierte Ausgabe generieren**:
   - Fragen als Markdown-Dateien im `./demo/` Verzeichnis
   - Separate Musterlösungen mit detaillierter Punkteverteilung
   - Konsistente Namenskonvention und Formatierung

## 📋 Aufgabenformat Spezifikation

### Titel-Schema

```text
Aufgabe {Nummer} | {Themenbereich} | {Maximale Punktzahl} Punkte
```

**Beispiel**: `Aufgabe 1 | Heapsort Implementation | 15 Punkte`

### Frage-Struktur

1. **Kontext-Erklärung** (aus PDF abgeleitet)
2. **Programmvorgabe** (unvollständiger Python-Code)
3. **Spezifische Aufgabenstellung** (welche Methode zu implementieren)
4. **Bewertungskriterien** (was wird bewertet)
5. **Hinweise** (falls erforderlich)

### Musterlösung-Struktur

1. **Vollständiger Python-Code**
2. **Detaillierte Punkteverteilung**:
   - Algorithmus-Verständnis (X Punkte)
   - Korrekte Implementierung (Y Punkte)
   - Code-Qualität/Effizienz (Z Punkte)
   - **Gesamtsumme muss maximaler Punktzahl entsprechen**
3. **Erklärung der Lösung**
4. **Typische Fehler und Abzüge**

## 🔧 Automatisierter Workflow

### Schritt 1: Material-Analyse

```bash
# PDF-Dateien im demo/ Verzeichnis identifizieren
find ./demo -name "*.pdf" -type f

# Für jede PDF-Datei:
# - Vollständigen Inhalt mit Read-Tool erfassen
# - Relevante Konzepte und Code-Beispiele extrahieren
# - Schwierigkeitsgrad und Themen identifizieren
```

### Schritt 2: Fragen-Generierung

```python
# Pro PDF oder Themenbereich:
# 1. Identifiziere 3-5 Kern-Algorithmen/Konzepte
# 2. Entwickle realistische Code-Vervollständigungsaufgaben
# 3. Erstelle ausführbare Python-Grundgerüste
# 4. Definiere spezifische Implementierungsaufgaben
```

### Schritt 3: Qualitäts-Validation

```python
# Für jede generierte Frage:
# 1. Syntax-Check des Python-Codes
# 2. Ausführbarkeit der Musterlösung testen
# 3. Punkteverteilung validieren (Summe = Maximum)
# 4. Schwierigkeitsgrad gegen BSc-Standard prüfen
```

### Schritt 4: Ausgabe-Generierung

```text
# Datei-Naming Convention:
# frage_01_heapsort.md
# loesung_01_heapsort.md
# frage_02_priority_queue.md
# loesung_02_priority_queue.md
```

## 🎯 Standard-Konfiguration

**Default Parameters** (anpassbar):

- **Anzahl Fragen**: 3 pro Themenbereich
- **Punkteverteilung**: 10-20 Punkte pro Frage
- **Zielgruppe**: BSc Informatik, 3.-4. Semester
- **Programmiersprache**: Python 3.8+
- **Fokus**: Datenstrukturen und Algorithmen

## 📁 Ausgabeformat

### Frage-Datei Template

```markdown
# Aufgabe {N} | {Thema} | {Punkte} Punkte

## Kontext
[Theoretischer Hintergrund aus PDF]

## Aufgabenstellung
[Spezifische Implementierungsaufgabe]

## Code-Grundgerüst
```python
# Bereitgestellter unvollständiger Code
class ExampleAlgorithm:
    def __init__(self):
        pass

    def missing_method(self, parameter):
        """
        TODO: Implementieren Sie diese Methode
        """
        pass
```

## Anforderungen

- [Spezifische Implementierungsanforderungen]
- [Erwartete Zeitkomplexität]
- [Besondere Hinweise]

## Bewertung

- **Algorithmus-Verständnis**: X Punkte
- **Korrekte Implementierung**: Y Punkte
- **Code-Qualität**: Z Punkte
- **Gesamt**: {X+Y+Z} Punkte

### Musterlösung-Datei Template

```markdown
# Musterlösung: Aufgabe {N} | {Thema}

## Vollständige Implementierung
```python
[Kompletter, ausführbarer Python-Code]
```

## Punkteverteilung

### Algorithmus-Verständnis (X Punkte)

- [Detaillierte Kriterien für Teilpunkte]

### Korrekte Implementierung (Y Punkte)

- [Spezifische Code-Abschnitte und Bewertung]

### Code-Qualität (Z Punkte)

- [Effizienz, Lesbarkeit, Best Practices]

## Erklärung

[Didaktische Erklärung der Lösung]

## Häufige Fehler

- [Typische Studierenden-Fehler]
- [Entsprechende Punktabzüge]

## 🚀 Verwendung

### Basic Usage

```bash
# Standard-Anwendung für alle PDFs im demo/ Verzeichnis
/create-questions

# Mit spezifischem Thema
/create-questions "Heapsort und Priority Queues"

# Mit angepasster Fragenzahl
/create-questions --count 5 --theme "Graph Algorithms"
```

### Advanced Usage

```bash
# Für spezifisches PDF
/create-questions --source "demo/algorithm_book.pdf" --theme "Dynamic Programming"

# Mit angepasster Schwierigkeit
/create-questions --difficulty advanced --points-range 15-25
```

## ⚠️ Best Practices & Guidelines

### Academic Integrity

- **Originalität**: Fragen müssen eigenständig aus dem Material entwickelt werden
- **Fairness**: Angemessener Schwierigkeitsgrad für die Zielgruppe
- **Vollständigkeit**: Alle notwendigen Informationen in der Aufgabe enthalten

### Code Quality

- **Syntax**: Fehlerfreier, ausführbarer Python-Code
- **Standards**: PEP 8 Konformität
- **Kommentare**: Ausreichende, aber nicht übermäßige Dokumentation
- **Testbarkeit**: Code sollte einfach testbar sein

### Educational Design

- **Progression**: Logische Schwierigkeitssteigerung
- **Relevanz**: Direkte Verbindung zum Kursmaterial
- **Praxisbezug**: Realistische Anwendungsszenarien
- **Verständnis**: Fokus auf Konzept-Verständnis, nicht nur Syntax

## 🔍 Quality Assurance Checklist

Vor Finalisierung jeder Frage:

- [ ] PDF-Material korrekt analysiert und referenziert
- [ ] Python-Code syntaktisch korrekt und ausführbar
- [ ] Musterlösung vollständig und korrekt
- [ ] Punkteverteilung summiert sich zur Maximalpunktzahl
- [ ] Schwierigkeitsgrad angemessen für BSc-Niveau
- [ ] Aufgabenstellung eindeutig und verständlich
- [ ] Dateien korrekt benannt und im `./demo/` Verzeichnis gespeichert
- [ ] Markdown-Formatierung konsistent und professionell

## 🎓 Pädagogische Ziele

Jede generierte Frage sollte:

1. **Verstehen**: Algorithmisches Verständnis demonstrieren
2. **Anwenden**: Konzepte in praktischen Code umsetzen
3. **Analysieren**: Code-Effizienz und Korrektheit bewerten
4. **Synthetisieren**: Verschiedene Konzepte kombinieren

---

**Verwende diesen Befehl, um professionelle, akademisch fundierte Programmieraufgaben aus PDF-Materialien zu generieren, die sowohl pädagogisch wertvoll als auch fair bewertbar sind.**
