# Notenexport

!!! warning "Alle Reviews müssen abgeschlossen sein"
    Der Notenexport ist blockiert, solange Submissions mit Status `pending_review` oder `partially_reviewed` vorhanden sind. Schliessen Sie zuerst alle Reviews im [Review-Tab](review-grading.md) ab.

Der Notenexport erstellt eine fertige Notenliste in drei Formaten: als CSV für Excel, als Moodle-Reimport-CSV oder als druckfertige PDF. Route: Tab **Notenexport** in `/auswertungen/:examId/submissions`.

## Notenmodell

### Voreingestellte Schemata

ExamCraft AI enthält acht voreingestellte Noten-Schemata:

| Schema | Bereich | Hinweis |
|--------|---------|---------|
| Swiss 1.0–6.0 | 1.0 (ungenügend) – 6.0 (sehr gut) | Standard-Schweizer Notenskala |
| German 1.0–5.0 | 1.0 (sehr gut) – 5.0 (ungenügend) | Umgekehrte Skala |
| Austrian 1–5 | 1 (sehr gut) – 5 (nicht genügend) | Ganzzahlig |
| French 0–20 | 0–20 Punkte | Französisches System |
| Dutch 1–10 | 1–10 | Niederländisches System |
| ECTS A–F | A–F + FX | Europäisches Transfer-System |
| Prozent | 0–100 % | Direkte Prozentanzeige |
| Pass/Fail | Bestanden / Nicht bestanden | Binär |

### Eigene Schemata

Institutionen mit Enterprise-Tier können unter `/admin/grading-schemes` eigene Schemata definieren und als Institutions-Standard hinterlegen. Weitere Details: [Notenschemata (Admin-Guide)](../admin-guide/grading-schemes.md).

## Exportformat wählen

![Notenexport — Format-Auswahl](../screenshots/notenexport/notenexport-format-selection.png)

| Format | Verwendung |
|--------|-----------|
| **CSV (Excel)** | UTF-8 mit BOM, Semikolon-getrennt — direkt in Excel (DE) zu öffnen |
| **Moodle-Reimport-CSV** | Moodle-kompatibles Format zum Zurückspielen der Noten |
| **PDF** | Druckfertige Notenliste mit Schulkopf, Tabelle und Signatur-Footer |

## Notenexport durchführen

1. Wählen Sie das **Notenschema** im Dropdown (voreingestellt: Institutions-Standard)
2. Wählen Sie das **Exportformat**
3. Die ersten 5 Zeilen erscheinen als **Vorschau** — prüfen Sie Namen und Noten
4. Klicken Sie auf **Exportieren** — der Download startet sofort

## Block bei ausstehenden Reviews

![Notenexport blockiert — Banner](../screenshots/notenexport/notenexport-blocked.png)

Solange Reviews ausstehen, erscheint ein gelber Hinweis-Banner mit der Anzahl offener Fälle und einem direkten Link in die [Review-Queue](review-grading.md). Der Export-Button ist deaktiviert bis alle Submissions den Status `fully_reviewed` erreicht haben.

## PDF-Inhalt

![Notenexport — PDF-Beispiel](../screenshots/notenexport/notenexport-pdf-preview.png)

Die PDF enthält:
- **Kopfzeile**: Institutionsname, Prüfungstitel, Datum
- **Notentabelle**: Alle Studierenden mit Punkten, Prozent und Note
- **Signatur-Footer**: Platzhalter für Lehrperson und Prüfungsleitung

## Nächste Schritte

- [:octicons-arrow-right-24: Klassen verwalten](klassen.md)
- [:octicons-arrow-right-24: Moodle-Integration](moodle-integration.md)
- [:octicons-arrow-right-24: Subscription-Quotas](subscription.md)
