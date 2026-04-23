# Häufig gestellte Fragen

## Allgemein

**Wie viele Dokumente kann ich hochladen?**

Abhängig von Ihrem Plan:

- Free: 5 Dokumente
- Starter: 50 Dokumente
- Professional: Unbegrenzt

**Welche Sprachen werden unterstützt?**

Aktuell Deutsch und Englisch. Weitere Sprachen sind in Planung.

**Kann ich Fragen exportieren?**

Aktuell nur manuell. PDF/JSON/Moodle XML Export ist in Entwicklung.

## Review Queue und Prüfungskomponist

## Was ist die Review Queue?

Die Review Queue ist der Bereich, in dem KI-generierte Fragen manuell geprüft und
freigegeben werden, bevor sie im Prüfungskomponisten verwendet werden können.
Nur genehmigte Fragen stehen für die Prüfungszusammenstellung zur Verfügung.

→ Mehr dazu: [Review Queue](../user-guide/review-queue.md)

## Was ist der Prüfungskomponist?

Der Prüfungskomponist ermöglicht es, genehmigte Fragen zu einer vollständigen Prüfung
zusammenzustellen und in verschiedenen Formaten (PDF, Word, JSON) zu exportieren.

→ Mehr dazu: [Prüfungskomponist](../user-guide/exam-composer.md)

## Abonnement

## Wie viele Fragen kann ich pro Monat generieren?

Das hängt von Ihrem Abonnementplan ab:

| Plan | Fragen pro Monat |
|------|-----------------|
| Free | 20 |
| Starter | 200 |
| Professional | Unbegrenzt |
| Enterprise | Unbegrenzt |

→ Mehr dazu: [Abonnement](../user-guide/subscription.md)

## Wo finde ich die Prompt-Bibliothek?

Die Prompt-Bibliothek ist über die Navigation unter **Prompts** erreichbar (Route: `/prompts`).
Sie steht Benutzern mit den Rollen ADMIN und DOZENT zur Verfügung.

→ Mehr dazu: [Prompt-Bibliothek](../user-guide/prompt-library.md)

## Was passiert mit meinen Daten bei einem Abonnement-Downgrade?

Ihre Daten (Dokumente, Fragen, Prüfungen) bleiben vollständig erhalten.
Sie können auf sie zugreifen, aber keine neuen erstellen, sobald die Limits des
niedrigeren Plans erreicht sind. Premium-Features wie der Dokument-Chat sind
nicht mehr zugänglich, bis Sie wieder upgraden.

## Technisch

**Warum dauert die Verarbeitung so lange?**

Grosse PDFs (über 20 Seiten) benötigen mehr Zeit für die Textextraktion und Indexierung. Gescannte PDFs benötigen zusätzlich OCR-Verarbeitung.

**Was passiert mit meinen Daten?**

Alle Daten werden verschlüsselt gespeichert. Hochgeladene Dokumente verbleiben auf den Servern und werden nicht an Dritte weitergegeben.

**Kann ich offline arbeiten?**

Nein, ExamCraft AI benötigt eine Internetverbindung für die KI-Funktionen (Embedding-Berechnung und Fragengenerierung).
