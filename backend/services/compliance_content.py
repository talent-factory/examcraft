"""Static compliance-document content — DSGVO AVV/TOM package (TF-746).

Single source of truth for the AVV (Art. 28 DSGVO), the TOM annex
(Art. 32 DSGVO), the subprocessor list, the VVT text module for
schools, and the state-specific review notes. Both the public
frontend compliance page (``GET /api/v1/legal/compliance``) and the
PDF exporters (``services.compliance_pdf_service``) render from this
one module, so page and PDF content cannot drift apart.

DRAFT STATUS (TF-746): every document carries ``DRAFT_NOTICE`` — this
content has not been reviewed or approved by external legal/DPO
counsel yet (see the ticket's explicit note). Content is grounded in
what the codebase actually does today (Fly.io Frankfurt hosting,
force_https, audit_service.py, RBACService, the backup/restore-
rehearsal GitHub Actions workflows) — it does not claim certifications
or measures that are not implemented.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES

DRAFT_NOTICE = (
    "ENTWURF – juristische Prüfung ausstehend. Dieses Dokument ist ein "
    "Muster auf Basis gängiger DSGVO-Vorlagen (u. a. DSK-Struktur) und "
    "wurde noch nicht von einem externen Datenschutz-/IT-Rechtsspezialisten "
    "geprüft oder freigegeben. Es ist nicht rechtsverbindlich."
)

_LAST_UPDATED = "Stand: August 2026"


@dataclass(frozen=True)
class ComplianceSection:
    heading: str
    paragraphs: tuple[str, ...]


@dataclass(frozen=True)
class ComplianceDocument:
    title: str
    last_updated: str
    draft_notice: str
    sections: tuple[ComplianceSection, ...]


@dataclass(frozen=True)
class Subprocessor:
    name: str
    purpose: str
    location: str
    transfer_mechanism: str
    change_notice: str


@dataclass(frozen=True)
class ComplianceContent:
    avv: ComplianceDocument
    tom: ComplianceDocument
    subprocessors: tuple[Subprocessor, ...]
    vvt_text: str
    state_specific_notes: ComplianceSection


def _build_avv() -> ComplianceDocument:
    sections = (
        ComplianceSection(
            "1. Gegenstand und Dauer der Verarbeitung",
            (
                "Gegenstand dieser Vereinbarung ist die Verarbeitung personen"
                'bezogener Daten durch die Talent Factory GmbH ("Auftrag'
                'nehmer") im Auftrag der Schule bzw. des Schulträgers '
                '("Auftraggeber") im Rahmen der Nutzung der Plattform '
                "ExamCraft AI zur Erstellung, Durchführung, Korrektur und "
                "Auswertung von Prüfungen.",
                "Die Vereinbarung gilt für die Dauer des zugrunde liegenden "
                "Hauptvertrags (Nutzungsvertrag / Lizenzvereinbarung) und "
                "endet automatisch mit dessen Beendigung, vorbehaltlich der "
                "in Abschnitt 7 geregelten Lösch- und Rückgabepflichten.",
            ),
        ),
        ComplianceSection(
            "2. Art und Zweck der Verarbeitung",
            (
                "Die Verarbeitung umfasst: Erfassung und Speicherung von "
                "hochgeladenen Unterrichtsmaterialien, KI-gestützte "
                "Generierung von Prüfungsfragen auf Basis dieser Materialien, "
                "Erfassung und automatisierte Vorbewertung von Prüfungs"
                "antworten (als Vorschlag, nicht als finale Note), Speicherung "
                "von Prüfungsergebnissen sowie Audit-Protokollierung "
                "sicherheitsrelevanter Vorgänge.",
            ),
        ),
        ComplianceSection(
            "3. Art der personenbezogenen Daten",
            (
                "Kontaktdaten von Lehrpersonen und Institutions-"
                "Administratoren (Name, E-Mail-Adresse), pseudonyme "
                "Kennungen von Lernenden (external_id — Klarnamen werden "
                "gemäss Systemdesign standardmässig nicht gespeichert), "
                "Prüfungsantworten und daraus abgeleitete Bewertungen, "
                "technische Zugriffsdaten (IP-Adresse, User-Agent, "
                "Zeitstempel) im Audit-Log.",
            ),
        ),
        ComplianceSection(
            "4. Kategorien betroffener Personen",
            (
                "Lernende (Schülerinnen und Schüler bzw. Studierende), "
                "Lehrpersonen, Institutions-Administratoren des "
                "Auftraggebers.",
            ),
        ),
        ComplianceSection(
            "5. Rechte und Pflichten des Auftraggebers",
            (
                "Der Auftraggeber ist im Sinne von Art. 4 Nr. 7 DSGVO "
                "Verantwortlicher für die Verarbeitung. Ihm obliegen die "
                "Prüfung der Rechtsgrundlage (Erforderlichkeit bzw. "
                "Einwilligung), die Information der betroffenen Personen "
                "sowie — soweit landesrechtlich vorgesehen — die Eintragung "
                "in das Verzeichnis von Verarbeitungstätigkeiten (siehe "
                "VVT-Textbaustein).",
            ),
        ),
        ComplianceSection(
            "6. Weisungsgebundenheit (Art. 28 Abs. 3 lit. a DSGVO)",
            (
                "Der Auftragnehmer verarbeitet personenbezogene Daten "
                "ausschliesslich auf dokumentierte Weisung des Auftraggebers, "
                "einschliesslich in Bezug auf Übermittlungen an ein "
                "Drittland, es sei denn, eine gesetzliche Verpflichtung "
                "besteht.",
            ),
        ),
        ComplianceSection(
            "7. Vertraulichkeit (Art. 28 Abs. 3 lit. b DSGVO)",
            (
                "Der Auftragnehmer stellt sicher, dass zur Verarbeitung "
                "befugte Personen sich zur Vertraulichkeit verpflichtet "
                "haben oder einer angemessenen gesetzlichen "
                "Verschwiegenheitspflicht unterliegen.",
            ),
        ),
        ComplianceSection(
            "8. Technische und organisatorische Massnahmen (Art. 32 DSGVO)",
            (
                "Der Auftragnehmer trifft die in der TOM-Anlage (separates "
                "Dokument) beschriebenen technischen und organisatorischen "
                "Massnahmen und passt diese dem Stand der Technik "
                "entsprechend fortlaufend an.",
            ),
        ),
        ComplianceSection(
            "9. Einsatz weiterer Auftragsverarbeiter (Unterauftragsverhältnisse, "
            "Art. 28 Abs. 3 lit. d DSGVO)",
            (
                "Der Auftraggeber erteilt eine allgemeine Genehmigung zum "
                "Einsatz der in der Subprozessoren-Liste (separates "
                "Dokument) genannten Unterauftragsverarbeiter. Der "
                "Auftragnehmer informiert den Auftraggeber vorab über jede "
                "beabsichtigte Änderung in Bezug auf die Hinzuziehung oder "
                "Ersetzung weiterer Auftragsverarbeiter gemäss der dort "
                "dokumentierten Änderungsbenachrichtigungs-Regelung; der "
                "Auftraggeber kann gegen solche Änderungen Einspruch "
                "erheben.",
            ),
        ),
        ComplianceSection(
            "10. Unterstützung bei der Wahrnehmung der Betroffenenrechte",
            (
                "Der Auftragnehmer unterstützt den Auftraggeber, soweit "
                "möglich, mit geeigneten technischen und organisatorischen "
                "Massnahmen bei der Erfüllung von Anträgen auf Wahrnehmung "
                "der in Kapitel III der DSGVO genannten Rechte der "
                "betroffenen Person (Auskunft, Berichtigung, Löschung, "
                "Einschränkung, Datenübertragbarkeit, Widerspruch). Die "
                "Plattform stellt hierfür API-Funktionen für Datenexport "
                "(Art. 20 DSGVO) und Löschantrag (Art. 17 DSGVO) bereit.",
            ),
        ),
        ComplianceSection(
            "11. Unterstützung bei Sicherheit der Verarbeitung, Meldepflichten "
            "und Datenschutz-Folgenabschätzung (Art. 28 Abs. 3 lit. f DSGVO)",
            (
                "Der Auftragnehmer unterstützt den Auftraggeber unter "
                "Berücksichtigung der Art der Verarbeitung und der ihm zur "
                "Verfügung stehenden Informationen bei der Einhaltung der in "
                "den Art. 32 bis 36 DSGVO genannten Pflichten, insbesondere "
                "bei der Meldung von Datenschutzverletzungen und der "
                "Erstellung einer Datenschutz-Folgenabschätzung.",
            ),
        ),
        ComplianceSection(
            "12. Löschung und Rückgabe personenbezogener Daten",
            (
                "Nach Beendigung der Erbringung der Verarbeitungstätigkeiten "
                "löscht der Auftragnehmer sämtliche personenbezogenen Daten "
                "oder gibt sie nach Wahl des Auftraggebers zurück und löscht "
                "bestehende Kopien, soweit nicht eine gesetzliche "
                "Aufbewahrungspflicht entgegensteht. Nutzerinnen und Nutzer "
                "können die Löschung ihres Kontos jederzeit selbst "
                "beantragen; nach Ablauf einer 30-tägigen Widerrufsfrist "
                "wird die Löschung automatisiert durch einen täglichen "
                "Systemlauf ausgeführt (siehe TOM-Anlage Abschnitt 5).",
            ),
        ),
        ComplianceSection(
            "13. Nachweis- und Kontrollrechte (Art. 28 Abs. 3 lit. h DSGVO)",
            (
                "Der Auftragnehmer stellt dem Auftraggeber alle "
                "erforderlichen Informationen zum Nachweis der Einhaltung "
                "der in diesem Artikel niedergelegten Pflichten zur "
                "Verfügung und ermöglicht Überprüfungen — einschliesslich "
                "Inspektionen — durch den Auftraggeber oder einen anderen "
                "von ihm beauftragten Prüfer und trägt zu diesen bei.",
            ),
        ),
        ComplianceSection(
            "14. Haftung",
            (
                "Es gelten die gesetzlichen Haftungsregelungen der DSGVO "
                "sowie ergänzend die Haftungsregelungen des Hauptvertrags, "
                "soweit die DSGVO keine abweichenden zwingenden Vorgaben "
                "macht.",
            ),
        ),
        ComplianceSection(
            "15. Schlussbestimmungen",
            (
                "Sollten einzelne Bestimmungen dieser Vereinbarung "
                "unwirksam sein oder werden, bleibt die Wirksamkeit der "
                "übrigen Bestimmungen unberührt. Änderungen und Ergänzungen "
                "bedürfen der Textform.",
            ),
        ),
    )
    return ComplianceDocument(
        title="Muster — Auftragsverarbeitungsvertrag (AVV) nach Art. 28 DSGVO",
        last_updated=_LAST_UPDATED,
        draft_notice=DRAFT_NOTICE,
        sections=sections,
    )


def _build_tom() -> ComplianceDocument:
    sections = (
        ComplianceSection(
            "1. Vertraulichkeit (Art. 32 Abs. 1 lit. b DSGVO)",
            (
                "Zutrittskontrolle: Die Plattform läuft ausschliesslich in "
                "Rechenzentren des Hosting-Anbieters Fly.io am Standort "
                "Frankfurt am Main (EU); physischer Zutritt liegt in der "
                "Verantwortung des Anbieters gemäss dessen eigenen "
                "Sicherheitsmassnahmen.",
                "Zugangskontrolle: Passwörter werden ausschliesslich als "
                "bcrypt-Hash gespeichert, nie im Klartext; Authentifizierung "
                f"erfolgt über kurzlebige JWT-Access-Tokens "
                f"({ACCESS_TOKEN_EXPIRE_MINUTES} Minuten) mit "
                "serverseitigem Session-Tracking; alle Verbindungen werden "
                "per erzwungenem HTTPS (force_https) verschlüsselt.",
                "Zugriffskontrolle: Rollenbasierte Zugriffssteuerung (RBAC) "
                "beschränkt den Datenzugriff auf das jeweils erforderliche "
                "Mass je Rolle (Lehrperson, Institutions-Admin, Superuser); "
                "Mandantentrennung erfolgt auf Institutionsebene.",
            ),
        ),
        ComplianceSection(
            "2. Integrität (Art. 32 Abs. 1 lit. b DSGVO)",
            (
                "Weitergabekontrolle: Datenübertragung erfolgt ausschliesslich "
                "TLS-verschlüsselt (erzwungenes HTTPS); Datenübermittlungen "
                "an Subprozessoren sind in der Subprozessoren-Liste "
                "dokumentiert.",
                "Eingabekontrolle: Sicherheitsrelevante Vorgänge (u. a. "
                "DSGVO-Aktionen wie Datenexport und Löschanträge, "
                "administrative Änderungen, Notenänderungen) werden "
                "durchgängig mit Zeitstempel, IP-Adresse und User-Agent "
                "protokolliert und sind über ein Audit-Log nachvollziehbar.",
            ),
        ),
        ComplianceSection(
            "3. Verfügbarkeit und Belastbarkeit (Art. 32 Abs. 1 lit. b/c DSGVO)",
            (
                "Regelmässige automatisierte Backups der Datenbank und der "
                "Vektor-Datenbank werden über eine geplante, tägliche "
                "Backup-Pipeline erstellt; zur Überprüfung der "
                "Wiederherstellbarkeit ist eine eigenständige, monatlich "
                "geplante Restore-Rehearsal-Pipeline eingerichtet.",
                "Die Infrastruktur ist containerbasiert und horizontal "
                "skalierbar; Fehler und Ausfälle werden über ein "
                "Error-Tracking-System (Sentry, EU-Region; ohne "
                "standardmässige Übermittlung personenbezogener Inhalte) "
                "überwacht.",
            ),
        ),
        ComplianceSection(
            "4. Verfahren zur regelmässigen Überprüfung, Bewertung und "
            "Evaluierung (Art. 32 Abs. 1 lit. d DSGVO)",
            (
                "Codeänderungen durchlaufen verpflichtend eine "
                "Continuous-Integration-Pipeline (automatisierte Tests, "
                "Linting) sowie eine Pull-Request-Review vor dem Deployment. "
                "Für die Wiederherstellbarkeit von Backups ist zusätzlich "
                "die in Abschnitt 3 genannte, monatlich geplante "
                "Restore-Rehearsal-Pipeline eingerichtet. Diese TOM-Anlage "
                "wird regelmässig auf ihre Aktualität geprüft.",
            ),
        ),
        ComplianceSection(
            "5. Speicherbegrenzung und Löschfristen (Art. 32 i.V.m. "
            "Art. 5 Abs. 1 lit. e DSGVO)",
            (
                "Nutzerinnen und Nutzer können die Löschung ihres Kontos "
                "über die Plattform selbst beantragen (Art. 17 DSGVO); nach "
                "einer 30-tägigen Widerrufsfrist wird das Konto samt "
                "personenbezogener Daten automatisiert gelöscht. Ein "
                "täglicher, geplanter Systemlauf ermittelt fällige "
                "Löschungen und führt sie aus, ohne dass eine manuelle "
                "Aktion durch den Auftragnehmer erforderlich ist.",
                "Über die Kontolöschung hinausgehende, generelle "
                "Aufbewahrungsfristen für einzelne Datenkategorien während "
                "der laufenden Vertragslaufzeit sind derzeit nicht separat "
                "automatisiert; dies ist Gegenstand der laufenden "
                "Überprüfung dieser TOM-Anlage.",
            ),
        ),
        ComplianceSection(
            "6. Auftragskontrolle",
            (
                "Der Auftragnehmer verarbeitet Daten ausschliesslich auf "
                "dokumentierte Weisung des Auftraggebers (siehe AVV Abschnitt "
                "6). Der Einsatz von Subprozessoren ist vertraglich an die "
                "gleichen datenschutzrechtlichen Pflichten gebunden und in "
                "der Subprozessoren-Liste dokumentiert.",
            ),
        ),
    )
    return ComplianceDocument(
        title="Anlage — Technische und organisatorische Massnahmen (TOM) "
        "nach Art. 32 DSGVO",
        last_updated=_LAST_UPDATED,
        draft_notice=DRAFT_NOTICE,
        sections=sections,
    )


_CHANGE_NOTICE_STANDARD = (
    "Änderungen an dieser Liste (neuer Subprozessor, Wechsel des "
    "Sitzes/der Region, geänderter Transfermechanismus) werden mindestens "
    "30 Tage im Voraus auf dieser Seite dokumentiert; Institutions-"
    "Administratoren werden zusätzlich per E-Mail an die hinterlegte "
    "Kontaktadresse benachrichtigt."
)


def _build_subprocessors() -> tuple[Subprocessor, ...]:
    return (
        Subprocessor(
            name="Anthropic PBC",
            purpose="KI-gestützte Fragengenerierung und Korrekturvorschläge "
            "(Claude-Modelle)",
            location="USA (Sub-Verarbeiter/Rechenzentren; Prüfung EU-"
            "Inferenzoption offen — siehe Landesspezifika)",
            transfer_mechanism="EU-Standardvertragsklauseln (SCC); "
            "Zero-Data-Retention ist für die eingesetzten Modelle nicht "
            "durchgängig verfügbar und daher aktuell nicht vertraglich "
            "zugesichert",
            change_notice=_CHANGE_NOTICE_STANDARD,
        ),
        Subprocessor(
            name="OpenAI, L.L.C.",
            purpose="Embeddings für die semantische Dokumentensuche (RAG)",
            location="USA (Prüfung EU-Projekt/Azure-OpenAI offen — siehe "
            "Landesspezifika)",
            transfer_mechanism="EU-Standardvertragsklauseln (SCC)",
            change_notice=_CHANGE_NOTICE_STANDARD,
        ),
        Subprocessor(
            name="Fly.io, Inc.",
            purpose="Hosting der Plattform (Applikationsserver, "
            "Datenbank, Vektor-Datenbank, Warteschlange)",
            location='Frankfurt am Main, Deutschland (EU) — primary_region "fra"',
            transfer_mechanism="Verarbeitung innerhalb der EU, kein Drittlandtransfer",
            change_notice=_CHANGE_NOTICE_STANDARD,
        ),
        Subprocessor(
            name="Fly.io Tigris (Objektspeicher)",
            purpose="Speicherung hochgeladener Unterrichtsmaterialien und "
            "generierter Exportdateien (S3-kompatibler Objektspeicher)",
            location="Tigris ist standardmässig global-verteilt "
            "(multi-region); eine EU-exklusive Zusicherung erfordert eine "
            "gesonderte Regionsprüfung — siehe Landesspezifika",
            transfer_mechanism="EU-Standardvertragsklauseln (SCC), soweit "
            "die Speicherung ausserhalb der EU erfolgt",
            change_notice=_CHANGE_NOTICE_STANDARD,
        ),
        Subprocessor(
            name="Stripe Payments Europe, Ltd.",
            purpose="Zahlungsabwicklung für kostenpflichtige Abonnements",
            location="EU/Irland (Zahlungsdaten); ggf. Sub-Verarbeitung "
            "ausserhalb der EU gemäss Stripe-eigenem AVV",
            transfer_mechanism="EU-Standardvertragsklauseln (SCC) gemäss "
            "Stripe-Auftragsverarbeitungsvertrag",
            change_notice=_CHANGE_NOTICE_STANDARD,
        ),
        Subprocessor(
            name="Resend (Resend, Inc.)",
            purpose="Versand transaktionaler E-Mails (Verifizierung, "
            "Benachrichtigungen)",
            location="USA/EU je nach Versanderegion",
            transfer_mechanism="EU-Standardvertragsklauseln (SCC)",
            change_notice=_CHANGE_NOTICE_STANDARD,
        ),
        Subprocessor(
            name="Sentry (Functional Software, Inc.)",
            purpose="Fehler- und Performance-Überwachung",
            location="EU (Sentry-Projektregion; genaue Ingest-Subdomain "
            "ausserhalb dieses Codebase-Checks zu bestätigen); "
            "PII-Maskierung aktiv (send_default_pii=False)",
            transfer_mechanism="EU-Datenverarbeitung; EU-Standardvertrags"
            "klauseln (SCC) für etwaige Sub-Verarbeitung",
            change_notice=_CHANGE_NOTICE_STANDARD,
        ),
        Subprocessor(
            name="PostgreSQL / Redis (selbst betrieben)",
            purpose="Primärdatenbank und Session-/Cache-Speicher",
            location="Frankfurt am Main, Deutschland (EU) — als Fly.io-"
            "App im gleichen Rechenzentrum wie die Applikation betrieben",
            transfer_mechanism="Kein Drittlandtransfer (Selbstbetrieb "
            "innerhalb der EU)",
            change_notice=_CHANGE_NOTICE_STANDARD,
        ),
        Subprocessor(
            name="Google LLC / Microsoft Corporation (OAuth-Provider)",
            purpose="Optionale Single-Sign-On-Anmeldung; verarbeitet nur "
            "Identitätsdaten des anmeldenden Nutzers (E-Mail, Name), "
            "sofern der Nutzer diese Anmeldeart aktiv wählt",
            location="USA (OAuth-Identitätsdienste)",
            transfer_mechanism="EU-Standardvertragsklauseln (SCC) gemäss "
            "Google/Microsoft-Datenverarbeitungsbedingungen",
            change_notice=_CHANGE_NOTICE_STANDARD,
        ),
    )


_VVT_TEXT = """Verzeichnis von Verarbeitungstätigkeiten — Textbaustein für Schulen

Bezeichnung der Verarbeitungstätigkeit: Erstellung, Durchführung und
Korrektur von Prüfungen mittels ExamCraft AI

Verantwortlicher: [Schule/Schulträger einsetzen]
Auftragsverarbeiter: Talent Factory GmbH, Hofstattweg 6, 3422 Kirchberg BE
(siehe AVV vom [Datum])

Zweck der Verarbeitung: Digitale Erstellung, Durchführung und
KI-unterstützte Vorkorrektur von Prüfungen für Lernende der Schule;
KI-generierte Bewertungen sind Vorschläge und werden durch eine
Lehrperson geprüft und freigegeben.

Kategorien betroffener Personen: Lernende, Lehrpersonen,
Institutions-Administratoren.

Kategorien personenbezogener Daten: Pseudonyme Lernenden-Kennungen,
Prüfungsantworten, Bewertungen, Kontaktdaten von Lehrpersonen/Admins,
technische Zugriffsprotokolle.

Empfänger: Talent Factory GmbH als Auftragsverarbeiter; die in der
Subprozessoren-Liste genannten Unterauftragsverarbeiter (u. a. für
KI-Inferenz, Hosting, E-Mail-Versand).

Fristen für die Löschung: Kontolöschung auf Antrag der betroffenen
Person, automatisiert nach einer 30-tägigen Widerrufsfrist (siehe
TOM-Anlage Abschnitt 5); vollständige Löschung/Rückgabe sämtlicher
Daten nach Vertragsende.

Technische und organisatorische Massnahmen: siehe TOM-Anlage der
Talent Factory GmbH (separates Dokument).

Hinweis: Dieser Textbaustein ersetzt keine Rechtsberatung. Schulen
sollten den Eintrag vor Übernahme in das eigene Verzeichnis von
Verarbeitungstätigkeiten (Art. 30 DSGVO) durch die jeweils zuständige
Datenschutzbeauftragte Person prüfen lassen."""


_STATE_SPECIFIC_NOTES = ComplianceSection(
    "Landesspezifika — Prüfhinweis für Legal",
    (
        "Die schulrechtlichen Vorgaben zum Einsatz digitaler "
        "Lernplattformen und KI-Systeme unterscheiden sich zwischen den "
        "Bundesländern und sind vor einer Landesfassung durch einen "
        "Datenschutz-/IT-Rechtsspezialisten zu prüfen.",
        "Baden-Württemberg: § 115b SchulG regelt die Verarbeitung "
        "personenbezogener Daten durch Schulen bei der Nutzung digitaler "
        "Verfahren; zusätzlich sind die Vorgaben der DSK-Orientierungshilfe "
        '"KI und Datenschutz" sowie ggf. landesspezifische '
        "IT-Sicherheitsvorgaben zu berücksichtigen.",
        "Hessen: landesspezifische Vorgaben zur Auftragsverarbeitung im "
        "Schulbereich (u. a. Anforderungen des Hessischen Kultusministeriums "
        "an digitale Lernmittel) sind gesondert zu prüfen; eine hessische "
        "Landesfassung dieses AVV-Pakets liegt noch nicht vor.",
        "Diese Liste ist nicht abschliessend — weitere Länder sind bei "
        "Bedarf zu ergänzen. Bis zum Abschluss der juristischen Prüfung "
        "gilt ausschliesslich die allgemeine Muster-AVV.",
    ),
)


def get_compliance_content() -> ComplianceContent:
    """Return the full compliance-document package (AVV, TOM, ...)."""
    return ComplianceContent(
        avv=_build_avv(),
        tom=_build_tom(),
        subprocessors=_build_subprocessors(),
        vvt_text=_VVT_TEXT,
        state_specific_notes=_STATE_SPECIFIC_NOTES,
    )
