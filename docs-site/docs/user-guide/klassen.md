# Klassen und Studierende

!!! note "Tier-Hinweis"
    Klassen, Studi-Verlaufsstatistik und Cross-Exam-Auswertungen sind Enterprise-Features. Studierende werden jedoch in allen Tiers automatisch beim CSV-Import angelegt und können eingesehen werden.

Mit Klassen gruppieren Sie Studierende und erhalten einen prüfungsübergreifenden Überblick über deren Leistungsentwicklung. Routen: `/auswertungen/klassen`, `/auswertungen/klassen/:classId`, `/auswertungen/studierende`, `/auswertungen/studierende/:studentId`.

![Klassen — Übersicht](../screenshots/klassen/klassen-liste.png)

## Klasse erstellen

1. Navigieren Sie zu **Auswertungen → Klassen**
2. Klicken Sie auf **Klasse anlegen**
3. Vergeben Sie einen Namen (z.B. „Informatik B 2026")
4. Optional: Beschreibung und Schuljahr eintragen
5. **Speichern** — die Klasse ist jetzt leer

## Studierende zuweisen

Wählen Sie die Klasse in der Liste und klicken Sie auf **Studierende zuweisen**. Im Dialog können Sie einzelne Studierende per Suche hinzufügen oder alle Prüflinge einer importierten Prüfung übernehmen.

!!! tip "Auto-Zuweisung beim CSV-Import"
    Enthält die Import-CSV eine Spalte `class_hint`, werden Studierende automatisch der passenden Klasse zugewiesen — ohne manuellen Schritt. Klassen, die noch nicht existieren, werden dabei ebenfalls automatisch angelegt.

## Klassen-Detail und Verlauf

![Klassen — Detail mit Verlaufs-Charts](../screenshots/klassen/klassen-detail.png)

Im Klassen-Detail sehen Sie für alle bisher absolvierten Prüfungen:

| Ansicht | Inhalt |
|---------|--------|
| Verlauf-Diagramm | Durchschnittswert pro Prüfung chronologisch |
| Prüfungsliste | Alle Prüfungen mit Datum, Durchschnitt und Erfolgsquote |
| Mitglieder-Liste | Alle Studierenden mit ihrem letzten Ergebnis |

## Studierenden-Übersicht

![Studierende — Stammdaten-Liste](../screenshots/klassen/studierende-liste.png)

Navigieren Sie zu **Auswertungen → Studierende** für eine institutionsweite Übersicht aller Prüflinge mit Name, E-Mail, Klasse(n) und letztem Prüfungsdatum.

## Studierenden-Detail

![Studierende — Verlauf-Detail](../screenshots/klassen/studierende-detail.png)

Das Detail einer Studierenden zeigt:

- **Alle Submissions** chronologisch mit erreichter Punktzahl und Note
- **Verlauf-Chart** über alle Prüfungen
- **Bloom-Taxonomie-Mix** der bearbeiteten Fragen (falls Tags vergeben)
- **Stärken/Schwächen-Heatmap** pro Themengebiet (falls Tags vergeben)

## Nächste Schritte

- [:octicons-arrow-right-24: Moodle-Integration](moodle-integration.md)
- [:octicons-arrow-right-24: Auswertungen](auswertungen.md)
- [:octicons-arrow-right-24: Statistik](statistik.md)
- [:octicons-arrow-right-24: Subscription-Quotas](subscription.md)
