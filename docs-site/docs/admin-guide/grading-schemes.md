# Notenschemata

!!! note "Enterprise-Feature"
    Das Erstellen eigener Notenschemata erfordert die Permission `grading_schemes:manage`, die standardmässig Admin- und Institution-Owner-Rollen im Enterprise-Tier zugewiesen ist.

ExamCraft AI enthält acht voreingestellte System-Schemata (schreibgeschützt) und ermöglicht Institutionen, eigene Schemata zu definieren. Route: `/admin/grading-schemes`.

## System-Schemata vs. Institution-Schemata

| Typ | Herkunft | Bearbeitbar? |
|-----|---------|-------------|
| System-Schema | ExamCraft AI (vorinstalliert) | Nein |
| Institution-Schema | Von Ihnen erstellt | Ja — bearbeitbar und löschbar |

System-Schemata decken die gängigsten nationalen Notensysteme ab (Swiss, German, Austrian, French, Dutch, ECTS, Prozent, Pass/Fail). Eigene Schemata erweitern diese Liste.

## Konfigurations-Typen

### `linear`

Lineare Umrechnung vom Prozentwert zur Note zwischen `min_score` und `max_score`.

```yaml
type: linear
min_score: 1.0
max_score: 6.0
passing_percentage: 60
```

### `linear_segments`

Zwei lineare Segmente mit einem Knickpunkt bei `passing_percentage`. Noten unterhalb der Bestehensgrenze verlaufen flacher als oberhalb.

```yaml
type: linear_segments
min_score: 1.0
max_score: 6.0
passing_percentage: 60
passing_score: 4.0
```

### `stepped`

Noten in festen Stufen. Jede Stufe definiert einen Prozentbereich und die zugehörige Note.

```yaml
type: stepped
steps:
  - { min_percent: 0,  max_percent: 49,  grade: "F" }
  - { min_percent: 50, max_percent: 64,  grade: "D" }
  - { min_percent: 65, max_percent: 79,  grade: "C" }
  - { min_percent: 80, max_percent: 89,  grade: "B" }
  - { min_percent: 90, max_percent: 100, grade: "A" }
```

## Eigenes Schema erstellen

1. Navigieren Sie zu `/admin/grading-schemes`
2. Klicken Sie auf **Neues Schema**
3. Wählen Sie den Konfigurations-Typ
4. Füllen Sie die Parameter aus
5. Die **Live-Vorschau** zeigt sofort, welche Note bei welchem Prozentwert vergeben wird
6. **Speichern** — das Schema steht Lehrpersonen beim Notenexport zur Verfügung

## Institutions-Standard setzen

Klicken Sie auf das Stern-Symbol neben einem Schema um es als Standard für Ihre Institution festzulegen. Dieser Wert erscheint beim Notenexport vorausgewählt. Lehrpersonen können die Auswahl pro Export übersteuern.

## Nächste Schritte

- [:octicons-arrow-right-24: Moodle-Connection](moodle.md)
- [:octicons-arrow-right-24: Rollen und Berechtigungen](roles.md)
- [:octicons-arrow-right-24: Notenexport (Benutzerhandbuch)](../user-guide/notenexport.md)
