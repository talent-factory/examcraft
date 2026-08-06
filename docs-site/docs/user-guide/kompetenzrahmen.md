# Kompetenzrahmen und Leistungsniveau (LN)

<!-- TODO screenshot: ../screenshots/kompetenzrahmen/settings-list.png (Übersicht /settings/competency-frameworks) -->

Ein **Kompetenzrahmen** (auch Handlungskompetenzbereich, HKB) beschreibt, welche Handlungskompetenzen in einem Fach oder Modul geprüft werden sollen — und auf welchem Anspruchsniveau. ExamCraft AI nutzt diese Information, um generierte Fragen gezielt einer Handlungskompetenz zuzuordnen und ihre Zielstufe (**LN**, Leistungsniveau) zu markieren, statt Fragen nur nach Schwierigkeit (easy/medium/hard) zu klassifizieren.

## Kompetenzrahmen verwalten

Navigieren Sie zu **Einstellungen → Kompetenzrahmen** (`/settings/competency-frameworks`). Dieser Bereich ist für Dozierende mit der Berechtigung `create_questions` sichtbar; Administratoren verwalten Kompetenzrahmen ihrer Institution zusätzlich über das Admin-Panel.

<!-- TODO screenshot: ../screenshots/kompetenzrahmen/framework-form.png (Erstellen/Bearbeiten-Dialog) -->

### Kompetenzrahmen anlegen

1. Klicken Sie auf **Neuer Kompetenzrahmen**
2. Vergeben Sie einen Namen und optional einen Modul-Code (z. B. `HKB-A`)
3. Fügen Sie den vollständigen Text im folgenden Format ein:

```markdown
### A1 Regeln zur internen Zusammenarbeit vereinbaren

- Sie analysieren und reflektieren die Zusammenarbeit im eigenen Unternehmen. (LN 4)
- Sie fördern die Zusammenarbeit mit geeigneten Interventionen. (LN 2)

### A2 Mitarbeitendengespräche führen

- Sie legen ein Ziel für das Gespräch fest und überprüfen die Erreichung. (LN 2)
- Sie bereiten und strukturieren das Gespräch situationsgerecht vor. (LN 3)
```

4. Legen Sie die Sichtbarkeit fest: **Privat** (nur Sie) oder **Institution** (alle Dozierenden Ihrer Institution)
5. Speichern

Jede `###`-Überschrift mit einem Code (Buchstabe + Ziffern, z. B. `A1`, `B3`) wird als eigene Handlungskompetenz erkannt; die darunter aufgeführten Bullet-Punkte sind die Leistungskriterien. Die Angabe `(LN <Zahl>)` am Ende einer Zeile wird automatisch als Ziel-LN-Stufe (1–4) erfasst — fehlt sie, wird das Kriterium ohne LN-Stufe übernommen.

!!! tip "Vorlage vom Bildungsanbieter übernehmen"
    Häufig liefert Ihre Institution oder der Ausbildungsbetrieb (z. B. im Rahmen der Qualifikationsverfahren) den Handlungskompetenzbereich bereits als Markdown- oder Word-Dokument. Kopieren Sie den Text möglichst unverändert — er wird auch wörtlich in die Fragengenerierung eingespeist.

### Kompetenzrahmen bearbeiten und archivieren

Bestehende Kompetenzrahmen können jederzeit bearbeitet werden; Änderungen wirken sich nur auf künftig generierte Fragen aus, nicht auf bereits erzeugte. Nicht mehr benötigte Kompetenzrahmen werden **archiviert**, nicht gelöscht — archivierte Rahmen bleiben für bestehende Fragen als Referenz erhalten, stehen aber bei neuen Generierungen nicht mehr zur Auswahl.

## Was bedeutet „LN"?

**LN (Leistungsniveau)** ist eine Skala von **1 bis 4**, die angibt, wie anspruchsvoll ein Leistungskriterium ist — unabhängig von der technischen Schwierigkeit (`easy`/`medium`/`hard`) und unabhängig von der Bloom-Stufe. LN wird direkt im Kompetenzrahmen-Text je Kriterium festgelegt (siehe oben) und von Claude bei der Fragengenerierung übernommen.

Die konkrete inhaltliche Bedeutung der vier Stufen wird von Ihrer Institution definiert. Ein verbreitetes Interpretationsmuster (nach Komplexität der Aufgabe, Veränderlichkeit/Unvorhersehbarkeit des Kontexts und Verantwortlichkeit) orientiert sich an den Niveaustufen N1–N4 der beruflichen Handlungskompetenz, ergänzt mit den Taxonomiestufen K2–K6:

| LN-Stufe | Bezeichnung | Beschreibung |
|---|---|---|
| **LN 1** (N1 / K2) | Orientierungswissen | Spricht in der Fachsprache über ein Thema. |
| **LN 2** (N2 / K3) | Standardsituation | Führt Arbeiten in wiederkehrenden Situationen korrekt und selbständig aus, trägt Verantwortung. |
| **LN 3** (N3 / K3–K4) | Verändernde Situation | Bearbeitet Aufgaben in sich verändernden Situationen unter Analyse der Komplexität korrekt und selbständig, trägt Verantwortung. |
| **LN 4** (N4 / K4–K6) | Problemsituation | Analysiert und bearbeitet neue, komplexe, nicht vorhersehbare Probleme; trägt operative Verantwortung; entscheidet und reflektiert kritisch. |

!!! note "Beispiel, keine feste Vorgabe"
    Diese Tabelle ist eine Orientierungshilfe, keine von ExamCraft AI erzwungene Definition. LN ist als reine Zahl 1–4 im Datenmodell hinterlegt — welche Kompetenzbeschreibung dahintersteckt, bestimmt der Kompetenzrahmen-Text Ihrer Institution. Weichen Ihre Stufenbeschreibungen ab, richten Sie sich nach der Definition Ihres Bildungsanbieters.

## LN in der Praxis

LN begegnet Ihnen an drei weiteren Stellen in ExamCraft AI:

- **Bei der Fragengenerierung** ([RAG-Prüfung erstellen](rag-exam.md)) wählen Sie einen Kompetenzrahmen aus; jede generierte Frage wird automatisch genau einer Handlungskompetenz und deren LN-Stufe zugeordnet.
- **Im Review** ([Fragen prüfen](review-queue.md)) zeigt jede Fragekarte einen Chip mit Kompetenz-Code und LN-Stufe (z. B. `B3 · LN 2`), damit Sie das Anspruchsniveau auf einen Blick erkennen.
- **Im Prüfungskomponisten** ([Prüfung zusammenstellen](exam-composer.md)) können Sie den Fragenpool gezielt nach Handlungskompetenz und LN-Stufe filtern, um eine ausgewogene Prüfung zusammenzustellen.

## Häufige Fragen

**Was passiert, wenn ein Kriterium keine LN-Angabe hat?**
Das Kriterium wird trotzdem als Leistungskriterium erfasst, die LN-Stufe bleibt leer (`null`). Die generierte Frage erhält dann keine LN-Kennzeichnung.

**Kann ich eine LN-Stufe ausserhalb von 1–4 vergeben?**
Nein. Werte ausserhalb von 1–4 werden beim Einlesen und bei der Fragengenerierung verworfen (auf „keine Angabe" zurückgesetzt), damit keine ungültigen Stufen ins Tagging gelangen.

**Ist LN dasselbe wie die Schwierigkeit (easy/medium/hard)?**
Nein, beide Achsen sind unabhängig voneinander. LN beschreibt das Anspruchsniveau der Handlungskompetenz, die Schwierigkeit die Komplexität der einzelnen Prüfungsfrage.

## Nächste Schritte

- [:octicons-arrow-right-24: Fragen aus Dokumenten generieren (RAG)](rag-exam.md)
- [:octicons-arrow-right-24: Fragen reviewen](review-queue.md)
- [:octicons-arrow-right-24: Prüfung zusammenstellen](exam-composer.md)
