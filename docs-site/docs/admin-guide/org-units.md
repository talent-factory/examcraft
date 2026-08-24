# Organisationseinheiten

!!! note "Neue Berechtigung erforderlich"
    Das Anlegen, Verschieben, Löschen und das Einsehen der vollständigen Liste von Organisationseinheiten erfordert die Permission `manage_org_units`, die standardmässig der ADMIN-Rolle zugewiesen ist. Ohne diese Permission ist der Tab **Organisationseinheiten** nicht sichtbar — jeder angemeldete Benutzer sieht lediglich seine eigenen Zugehörigkeiten, etwa bei der Wahl einer Team-Sichtbarkeit.

ExamCraft AI bildet die interne Struktur einer Institution über Organisationseinheiten ab — **Abteilungen** und darunter verschachtelte **Teams**. Navigieren Sie zu `/admin` und wählen Sie den Tab **Organisationseinheiten**.

## Organisationseinheit anlegen

1. Navigieren Sie zu `/admin` → Tab **Organisationseinheiten**
2. Klicken Sie auf **+ Anlegen**
3. Vergeben Sie einen **Namen** und wählen Sie den **Typ** (`Abteilung` oder `Team`)
4. Wählen Sie optional eine **Übergeordnete Einheit** — ein Team liegt typischerweise unterhalb einer Abteilung
5. Weisen Sie optional eine **Verliehene Rolle** zu (siehe unten)
6. **Speichern**

!!! warning "Typ nach dem Anlegen fix"
    Der Typ (`Abteilung`/`Team`) lässt sich nach dem Anlegen nicht mehr ändern.

    Der Name muss zudem innerhalb derselben Ebene eindeutig sein — zwei Einheiten mit demselben Namen und derselben übergeordneten Einheit sind nicht möglich.

## Organisationseinheit verschieben

Öffnen Sie die Einheit über das Bearbeiten-Symbol und wählen Sie im Feld **Übergeordnete Einheit** eine neue Elternposition. Eine Einheit lässt sich nicht unter eine ihrer eigenen Unter-Einheiten verschieben.

## Organisationseinheit löschen

Enthält eine Organisationseinheit Unter-Einheiten, werden beim Löschen **alle** untergeordneten Abteilungen/Teams unwiderruflich mitgelöscht. Der Bestätigungsdialog zeigt die Anzahl betroffener Unter-Einheiten an.

Referenzieren Dokumente, Prompts, Fragen, Prüfungen oder Kompetenzraster mit Team-Sichtbarkeit noch die Einheit oder eine ihrer Unter-Einheiten, wird das Löschen abgelehnt — entfernen oder verschieben Sie zuerst die betroffenen Ressourcen.

## Verliehene Rolle und Team-Sichtbarkeit

Die Organisationsstruktur ist nicht rein informativ — sie kann zwei Dinge steuern:

- **Verliehene Rolle**: Ist einer Organisationseinheit eine Rolle zugewiesen, erhalten alle **direkten** Mitglieder dieser Einheit automatisch deren Berechtigungen — zusätzlich zu ihrer eigenen Rolle. Die Vererbung wirkt nicht kaskadierend über Unter-Einheiten.
- **Team-Sichtbarkeit**: Bei Dokumenten, Prompts, Fragen, Prüfungen und Kompetenzrastern mit der Sichtbarkeitsstufe „Team" bestimmt die Organisationseinheits-Zugehörigkeit — inklusive Hierarchie — wer sie sehen kann.

Welcher Organisationseinheit ein Benutzer angehört, weisen Sie über den Button **Org-Units** in der [Benutzerverwaltung](user-mgmt.md) zu.

## Nächste Schritte

- [:octicons-arrow-right-24: Rollen und Berechtigungen](roles.md)
- [:octicons-arrow-right-24: Benutzer verwalten](user-mgmt.md)
