# Auswertungen

!!! note "Voraussetzung"
    Um Prüfungsresultate auszuwerten, benötigen Sie eine fertige Prüfung im [Prüfungskomponisten](exam-composer.md). Die Resultate werden als CSV-Datei aus Ihrer Lernplattform (z.B. Moodle) exportiert und hier importiert.

Die Auswertungs-Pipeline führt von der Abgabe bis zur Notenliste in fünf Schritten: **Import → Automatische Bewertung → Review offener Fragen → Statistik → Notenexport**. Route: `/auswertungen`.

![Auswertungen — Übersicht](../screenshots/auswertungen/auswertungen-overview.png)

## Auswertungs-Pipeline starten

Navigieren Sie zu **Auswertungen** in der Hauptnavigation. Die Tabelle listet alle Ihre Prüfungen auf. Klicken Sie bei der gewünschten Prüfung auf **Resultate importieren**.

## Prüfungsresultate importieren

Der Import-Dialog führt Sie in zwei Schritten durch den CSV-Import.

### Schritt 1: CSV-Datei hochladen

![Import-Dialog — Quelle wählen](../screenshots/auswertungen/auswertungen-import-dialog.png)

Wählen Sie **CSV-Datei** als Quelle und laden Sie die Exportdatei Ihrer Lernplattform hoch. Moodle-Exporte (DE- und EN-Locale) werden direkt erkannt. Für den direkten API-Import aus Moodle lesen Sie den Abschnitt [Moodle-Integration](moodle-integration.md).

### Schritt 2: Spalten-Mapping prüfen

![Import — Mapping-Vorschau](../screenshots/auswertungen/auswertungen-import-preview.png)

Das System ordnet die CSV-Spalten automatisch den Fragen in Ihrer Prüfung zu. Prüfen Sie das Mapping:

| Spalte | Bedeutung |
|--------|-----------|
| Studierende | Name oder E-Mail des Prüflings |
| Fragen-Spalten | Antwort pro Frage — Zuweisung anhand der Moodle-Fragen-ID oder Spaltenposition |
| Gesamtpunkte | Wird aus den Einzelwertungen errechnet, nicht aus der CSV-Spalte übernommen |

Warnungen erscheinen, wenn eine Frage nicht zugeordnet werden kann. Sie können den Import trotzdem abschliessen — nicht zugeordnete Fragen werden übersprungen.

!!! note "Idempotenter Import"
    Ein zweiter Import derselben CSV-Datei erzeugt keine Duplikate. Bereits importierte Submissions werden aktualisiert, fehlende neu angelegt.

Klicken Sie auf **Importieren** um den Vorgang abzuschliessen.

## Submissions-Übersicht

![Submissions — Liste](../screenshots/auswertungen/auswertungen-submissions-tab.png)

Nach dem Import erscheinen alle Einreichungen im Tab **Submissions**. Die Liste zeigt:

| Spalte | Beschreibung |
|--------|-------------|
| Studierende | Name und E-Mail |
| Punkte | Erreichte / maximal mögliche Punkte |
| Prozent | Prozentualer Anteil |
| Status | Bewertungsstatus (siehe unten) |

### Status-Badges

| Badge | Bedeutung |
|-------|-----------|
| `pending_review` | Offene Fragen warten noch auf Review |
| `partially_reviewed` | Einige offene Fragen sind reviewed, andere noch nicht |
| `fully_reviewed` | Alle offenen Fragen bewertet — Notenexport möglich |

## Submission-Detail

![Submission-Detail — Drawer](../screenshots/auswertungen/auswertungen-submission-drawer.png)

Klicken Sie auf eine Zeile um den Detail-Drawer zu öffnen. Er zeigt alle Antworten mit Fragetext, Antworttyp (MC, Wahr/Falsch, Offen), abgegebene Antwort, Bewertungsstatus und erzielte Punkte. Bei offenen Fragen: KI-Vorschlag mit Konfidenz-Badge.

## Nächste Schritte

- [:octicons-arrow-right-24: Offene Fragen reviewen](review-grading.md)
- [:octicons-arrow-right-24: Statistik einsehen](statistik.md)
- [:octicons-arrow-right-24: Noten exportieren](notenexport.md)
- [:octicons-arrow-right-24: Moodle-Integration](moodle-integration.md)
- [:octicons-arrow-right-24: Subscription-Quotas](subscription.md)
