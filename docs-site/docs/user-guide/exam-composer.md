# Prüfungskomponist

Der Prüfungskomponist ermöglicht es, genehmigte Fragen zu einer vollständigen Prüfung zusammenzustellen und in verschiedenen Formaten zu exportieren.

!!! note "Voraussetzung"
    Im Prüfungskomponisten stehen nur Fragen zur Verfügung, die in der [Review Queue](review-queue.md) genehmigt wurden. Generieren Sie zuerst Fragen und reviewen Sie diese, bevor Sie eine Prüfung zusammenstellen.

## Neue Prüfung erstellen

### Schritt 1: Prüfungskomponist öffnen

Klicken Sie in der Navigation auf **Prüfungskomponist** oder wählen Sie die entsprechende Kachel auf dem [Dashboard](dashboard.md). Route: `/exams/compose`.

![Prüfungskomponist — Startansicht](../screenshots/exam-composer/exam-composer-overview.png)

### Schritt 2: Neue Prüfung starten

![Prüfungskomponist — Neues Formular](../screenshots/exam-composer/exam-composer-new.png)

Klicken Sie auf **Neue Prüfung erstellen** und füllen Sie die folgenden Felder aus:

| Feld | Beschreibung |
|------|-------------|
| Titel | Bezeichnung der Prüfung (z.B. „Algorithmen — Semesterprüfung 2026") |
| Beschreibung | Optionale Zusatzinformationen zur Prüfung |
| Datum | Geplantes Prüfungsdatum |

Der Titel ist das Schlüsselelement, das Ihre Prüfung eindeutig identifiziert. Wählen Sie eine aussagekräftige Bezeichnung, die Fach, Kurs und zeitliche Einordnung deutlich macht. Die Beschreibung bietet zusätzlichen Kontext für Sie und Ihre Kolleginnen und Kollegen — etwa Informationen zum Schwierigkeitsgrad, der Zielgruppe oder speziellen Schwerpunkten.

### Notenskala wählen

Im `ExamMetadataBar` oben auf der Seite finden Sie den **Notenskala**-Selector. Wählen Sie das gewünschte Notenschema für diese Prüfung:

![Prüfungskomponist — Notenskala-Selector](../screenshots/exam-composer/exam-composer-grading-scheme.png)

| Option | Beschreibung |
|--------|-------------|
| Institutions-Standard | Voreingestelltes Schema Ihrer Institution (Standard) |
| System-Schemata | 8 vorinstallierte Schemata (Swiss, German, ECTS, etc.) |
| Eigene Schemata | Von Ihrer Institution definierte Schemata (Enterprise) |

Die Notenskala beeinflusst den [Notenexport](notenexport.md). Sie kann jederzeit geändert werden, solange noch kein Export erstellt wurde.

### Schritt 3: Fragen auswählen

![Prüfungskomponist — Fragenauswahl](../screenshots/exam-composer/exam-composer-question-selection.png)

Wählen Sie Fragen aus der Liste der genehmigten Fragen:

- Klicken Sie auf **+ Hinzufügen** neben jeder gewünschten Frage
- Nutzen Sie die Filter um gezielt Fragen nach **Fragetyp**, **Schwierigkeit**, **Quelldokument** oder —
  sofern Fragen einem [Kompetenzrahmen](kompetenzrahmen.md) zugeordnet sind — nach **Handlungskompetenz**
  und **LN-Stufe** zu finden
- Die Gesamtanzahl der ausgewählten Fragen wird oben angezeigt

!!! tip "Ausgewogene Prüfung zusammenstellen"
    Achten Sie auf eine ausgewogene Mischung: verschiedene Fragetypen (Multiple Choice und offene Fragen), unterschiedliche Schwierigkeitsgrade und wenn möglich verschiedene Themengebiete. Eine ausgewogene Prüfung fördert gerechte Leistungsbewertung und authentisches Verständnis der Inhalte.

Die Filterfunktionen helfen Ihnen, effizient die passenden Fragen zu finden. Nutzen Sie die Filteroptionen systematisch: Beginnen Sie mit dem gewünschten Fragetyp (z.B. nur Multiple-Choice-Fragen für Schnelltests oder ein Mix aus MC und offenen Fragen für umfassendere Prüfungen). Anschliessend filtern Sie nach Schwierigkeit, um eine ausgewogene Verteilung zu erreichen. Zuletzt können Sie gezielt nach Quelldokumenten filtern, wenn Sie bestimmte Kapitel oder Themenbereiche schwerpunktmässig prüfen möchten.

### Schritt 4: Reihenfolge festlegen

![Prüfungskomponist — Reihenfolge festlegen](../screenshots/exam-composer/exam-composer-reorder.png)

Ordnen Sie die ausgewählten Fragen per Drag & Drop in die gewünschte Reihenfolge. Die Fragen werden automatisch nummeriert. Überlegen Sie sich, ob Sie mit einfacheren Fragen beginnen, um Prüflinge in das Thema einzuführen, oder ob Sie bewusst schwierigere Fragen voranstellen möchten. Die Reihenfolge kann auch thematisch sinnvoll sein — gruppieren Sie zusammenhängende Fragen, um Prüflingen das Verständnis von Zusammenhängen zu ermöglichen.

### Schritt 5: Prüfung exportieren

![Prüfungskomponist — Export-Dialog](../screenshots/exam-composer/exam-composer-export.png)

Klicken Sie auf **Exportieren** und wählen Sie das gewünschte Format:

| Format | Beschreibung |
|--------|-------------|
| Markdown (.md) | Textbasiertes Format, ideal für die weitere Bearbeitung oder Veröffentlichung. Optional können die Lösungen eingeschlossen werden. |
| PDF (druckfertig) | Fertig gesetzter Prüfungsbogen zum Ausdrucken. Optional können die Lösungen eingeschlossen werden. |
| JSON (.json) | Maschinenlesbares Format für die weitere Verarbeitung, Integration mit externen Systemen oder Datenanalyse |
| Moodle XML (.xml) | Direkt importierbares Format für das Lernmanagementsystem Moodle |

!!! tip "Lösungen einschliessen"
    Beim Export im Markdown- und im PDF-Format können Sie optional die Lösungen einschliessen. Aktivieren Sie dazu die Checkbox **Lösungen einschliessen** im Export-Dialog — praktisch für die Erstellung von Lösungsblättern oder zur internen Überprüfung.

Das Markdown-Format eignet sich für die weitere Bearbeitung oder Integration in Dokumentationssysteme. Das JSON-Format ist ideal für technische Integration — etwa wenn Sie Prüfungsdaten in ein eigenes System importieren oder automatisierte Auswertungen durchführen möchten. Das Moodle-XML-Format ermöglicht den direkten Import in Moodle, ohne manuelle Nachbearbeitung.

### PDF-Export für die Durchführung auf Papier

Das PDF-Format liefert einen druckfertigen Prüfungsbogen — ohne Nachbearbeitung in einem Textprogramm:

- **Kopfbereich** mit Titel, Kurs, Datum, Zeitlimit, erlaubten Hilfsmitteln, Gesamtpunktzahl und Bestehensgrenze (in Prozent und in Punkten). Nicht gesetzte Felder werden weggelassen.
- **Ausfüllzeilen** für Name und Klasse direkt unter dem Kopfbereich.
- **Ankreuzkästchen** bei Einfach- und Mehrfachauswahl sowie bei Wahr/Falsch-Fragen.
- **Antwortlinien** bei offenen Fragen — drei Linien pro Punkt, mindestens jedoch drei.
- **Fusszeile** mit Prüfungstitel und „Seite X von Y" auf jeder Seite.

Der Bogen erscheint in der **Sprache der Prüfung**, nicht in Ihrer Anzeigesprache — er geht schliesslich an die Prüflinge. Übersetzt werden dabei nur die Beschriftungen (Kurs, Frage, Punkte, Musterlösung …); Fragetexte und Antworten bleiben unverändert, so wie sie verfasst wurden. Das gilt auch für den Dateinamen: das Lösungsblatt heisst je nach Prüfungssprache `…_Lösungen.pdf`, `…_solutions.pdf`, `…_corrigé.pdf` oder `…_soluzioni.pdf`.

Eine Frage bleibt mit ihrem Antwortbereich zusammen, solange dieser auf eine Seite passt: Passt der ganze Block nicht mehr auf die aktuelle Seite, beginnt er auf der nächsten. Nur ein aussergewöhnlich umfangreicher Antwortbereich — etwa bei einer offenen Frage mit sehr vielen Punkten — kann selbst über eine Seite hinausgehen. Wählen Sie **Lösungen einschliessen**, erscheint zu jeder Frage ein abgesetzter Kasten mit Musterlösung und Erklärung — geeignet als Korrekturvorlage.

## Bestehende Prüfungen verwalten

![Prüfungskomponist — Prüfungsübersicht](../screenshots/exam-composer/exam-composer-builder.png)

Alle erstellten Prüfungen erscheinen in der Übersichtsliste. Dort können Sie:

- **Öffnen**: Prüfung bearbeiten und ergänzen
- **Duplizieren**: Als Grundlage für eine neue, ähnliche Prüfung verwenden
- **Exportieren**: Erneut in einem beliebigen Format exportieren
- **Löschen**: Prüfung entfernen (nicht rückgängig machbar)

Die Übersichtsliste zeigt wichtige Metadaten wie Erstellungsdatum, Anzahl der Fragen und letzter Änderungszeitstempel. Nutzen Sie die Duplikatfunktion, um schnell ähnliche Prüfungen zu erstellen — z.B. für verschiedene Klassen desselben Jahrgangs oder für eine Nachholprüfung. Diese Funktion spart Zeit bei der Zusammenstellung ähnlicher Prüfungen und minimiert Fehler.

!!! warning "Gelöschte Prüfungen"
    Das Löschen einer Prüfung entfernt nur die Prüfungszusammenstellung, nicht die einzelnen Fragen. Die Fragen bleiben in der Review Queue erhalten und können für zukünftige Prüfungen wiederverwendet werden.

## Nächste Schritte

- [:octicons-arrow-right-24: Mehr Fragen generieren](exam-create.md)
- [:octicons-arrow-right-24: RAG-Prüfung aus Dokumenten](rag-exam.md)
- [:octicons-arrow-right-24: Review Queue — Fragen prüfen](review-queue.md)
- [:octicons-arrow-right-24: Best Practices](best-practices.md)
