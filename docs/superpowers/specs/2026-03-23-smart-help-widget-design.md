# Smart Help Widget & Docs-Site Design

## Zusammenfassung

ExamCraft AI erhält ein zweisäuliges Dokumentationssystem:

1. **Material for MkDocs** -- statische Docs-Site (DE + EN) für Dozenten und IT-Admins
2. **Smart Help Widget** -- ein In-App-Hilfe-Widget mit drei Modi (Onboarding, Kontext, Frage) und selbstverbesserndem Feedback-Loop

Das Widget nutzt die bestehende RAG-Infrastruktur (Qdrant + Claude API), eine separate Qdrant Collection `docs_help` und eine Two-Tier Kostenoptimierung (cached FAQ vs. Claude-Call). Der bestehende Document ChatBot bleibt unberührt.

## Zielgruppen

- **Dozenten/Lehrkräfte** -- End-User, die Prüfungen erstellen
- **IT-Admins** -- deployen und verwalten ExamCraft an Bildungseinrichtungen

## Marktpositionierung

### Aktuelle Marktlandschaft

| Kategorie | Beispiele | Stärken | Schwächen |
|-----------|-----------|---------|-----------|
| Docs-AI-Services | Kapa.ai, Inkeep | Schnelle Integration, gute RAG-Qualität | Extern gehostet, keine App-Kontext-Awareness |
| Onboarding-Tools | Userpilot, Gleap | Behavior-driven Flows, kontextuell | Kein freier Chat, keine Docs-Integration |
| Self-Hosted RAG | Dify, AnythingLLM | Volle Kontrolle, Open Source | Kein Onboarding, kein Feedback-Loop |
| Education AI | Google NotebookLM | Multimodal, Chat mit Materialien | Kein In-App-Onboarding, nicht self-hosted |

### Differenzierung ExamCraft

Kein recherchiertes Produkt bietet alle drei Elemente zusammen:

1. Kontextuelles Onboarding (kennt Rolle, Tier, App-State)
2. Freier Q&A-Chat über die eigene Dokumentation in beliebiger Sprache
3. Feedback-Loop (unbeantwortete Fragen fliessen als neue Docs zurück)

## Architektur

### Zwei Säulen

**Säule 1: Statische Docs-Site (Material for MkDocs)**

- Markdown-Dateien als Single Source of Truth (DE + EN)
- Gehostet via GitHub Pages
- Screenshots, Diagramme, API-Referenz
- Suchbar, versioniert, linkbar

**Säule 2: Smart Help Widget (In-App)**

- Floating-Button unten rechts in der ExamCraft-App
- Drei Modi: Onboarding, Kontext, Frage
- Wissensbasis = dieselben Markdown-Docs (via Qdrant indexiert)
- Kontextuell: kennt aktuelle Seite, User-Rolle, Subscription-Tier
- Antwortet in der Sprache des Benutzers

### Datenfluss

```text
Markdown-Docs (.md, DE+EN)
        |
        +---> MkDocs Material Build ---> Docs-Site (browse)
        |
        +---> Embedding-Pipeline ---> Qdrant Collection "docs_help"
                                           |
                                     Smart Help Widget
                                      +-----+------+
                                      |            |
                               Cached FAQ    Claude API
                             (schnell/gratis) (komplex)
```

### Trennung vom Document ChatBot

| Aspekt | Document ChatBot | Smart Help Widget |
|--------|-----------------|-------------------|
| Zweck | Chat mit Kursmaterialien | App-Hilfe und Onboarding |
| Qdrant Collection | `documents` (bestehend) | `docs_help` (neu) |
| Einstieg | Tab "Dokument ChatBot" | Floating Button (alle Seiten) |
| Kontext | Ausgewählte Kursdokumente | App-State + User-Rolle |
| Backend-Endpoint | `/api/v1/chat/message` | `/api/v1/help/message` (neu) |

### Deployment-Modi (Core vs. Full)

| Modus | Widget-Verfügbarkeit | Verhalten |
|-------|---------------------|-----------|
| **Full** (mit Qdrant) | Alle drei Modi aktiv | Volle RAG-Funktionalität |
| **Core** (ohne Qdrant) | Nur Onboarding + Kontext-Modus | Frage-Modus zeigt statische FAQ-Links und Verweis auf Docs-Site. Kein RAG, kein Claude-Call. |

Im Core-Modus prüft das Frontend via Feature-Detection (Health-Check auf `/api/v1/help/status`), ob der Frage-Modus verfügbar ist.

## Widget-Modi

### Modus 1: Onboarding (Erstkontakt)

**Trigger:** Benutzer hat `onboarding_completed: false` im Profil (oder erster Login).

**Ablauf:**

- Widget öffnet sich automatisch mit Willkommensnachricht
- Rollenabhängig:
  - Dozent: "Willkommen! Ich zeige dir in 3 Schritten, wie du deine erste Prüfung erstellst."
  - Admin: "Willkommen! Lass uns die Institution einrichten und erste Benutzer anlegen."
- Schrittweise Führung durch Kernfunktionen (max. 5--7 Schritte)
- Jeder Schritt highlightet den relevanten UI-Bereich (Spotlight-Overlay)
- Benutzer kann jederzeit "Überspringen" oder "Später fortsetzen"
- Fortschritt wird persistiert -- bei nächstem Login geht es dort weiter

**Abschluss:** Nach dem letzten Schritt wird `onboarding_completed: true` gesetzt, Widget wechselt in Kontext-Modus.

**Onboarding-Schritte (Dozent):**

1. Willkommen + Überblick über die App
2. Dokument hochladen (navigiert zu `/documents/upload`)
3. Dokumentenbibliothek kennenlernen
4. Erste KI-Prüfung erstellen (navigiert zu `/exam/create`)
5. Ergebnis reviewen und exportieren

**Onboarding-Schritte (Admin):**

1. Willkommen + Admin-Überblick
2. Institution einrichten (navigiert zu `/admin/institutions`)
3. Benutzer anlegen und Rollen zuweisen
4. Subscription-Tiers verstehen
5. Prompt Management kennenlernen
6. Monitoring und Logs

**Konfiguration:** Onboarding-Schritte sind in einer JSON-Konfigurationsdatei definiert (`help-onboarding-steps.json`), nicht hardcoded. Admins können Schritte über das Admin-Panel anpassen (Phase 2).

### Modus 2: Kontext (Proaktive Hilfe)

**Trigger:** Widget erkennt die aktuelle Route/Seite und den User-State.

**Beispiele:**

| Route | Rolle | Kontext-Hinweis |
|-------|-------|----------------|
| `/documents/upload` | Dozent | "Tipp: Strukturierte PDFs mit Überschriften liefern bessere Prüfungsfragen." |
| `/exam/create` | Dozent | "Neu hier? Wähle zuerst 3--5 Dokumente für optimale Qualität." |
| `/admin/users` | Admin | "Du kannst Benutzerrollen direkt in der Tabelle ändern." |
| `/prompts` | Admin | "Die Live-Vorschau zeigt dir, wie der Prompt mit echten Variablen aussieht." |

**Verhalten:**

- Kleine Notification-Badge am Widget-Button (nicht aufdringlich)
- Hinweis erscheint erst beim Öffnen des Widgets
- Jeder Hinweis hat "Verstanden" / "Mehr erfahren" Buttons
- "Nicht mehr anzeigen" pro Hinweis-Typ (gespeichert pro User)
- Max. 1 Hinweis pro Seite, max. 3 pro Session (keine Überflutung)

**Sprache der Kontext-Hinweise:** Hinweise werden nur in DE und EN ausgeliefert (analog zur Docs-Site). Die Sprache richtet sich nach der aktuellen App-Sprache des Benutzers (i18n-Setting).

### Modus 3: Frage (Freier Chat)

**Trigger:** Benutzer tippt eine Frage ins Widget.

**Ablauf:**

1. Frage wird als Embedding in `docs_help` Collection gesucht
2. **Fast Path:** Similarity-Score >= 0.92 und Frage in FAQ-Cache: sofortige Antwort ohne Claude-Call
3. **Standard Path:** Top-K Chunks aus Qdrant + User-Kontext (Rolle, Tier, aktuelle Seite) an Claude API
4. Antwort enthält Links zu relevanten Docs-Seiten
5. Benutzer kann Antwort bewerten (Daumen hoch/runter)

**Sprache:** Antwort immer in der Sprache der Frage. Claude erkennt die Sprache automatisch, unabhängig davon, ob die Source-Docs DE oder EN sind.

**Eskalation:** Bei Confidence < 0.5 wird dem Benutzer der Support-Kontakt angeboten und die Frage in die Admin-Queue geloggt.

**Konversations-Management:**

- Max. 10 Nachrichten History werden als Kontext an Claude gesendet
- Konversationen persistieren innerhalb einer Browser-Session
- Nach Session-Ende wird die Konversation archiviert (read-only in `help_conversations`)
- Benutzer kann jederzeit "Neue Konversation" starten

### Confidence-Definition

Der Confidence-Score ist ein **zusammengesetzter Wert**:

- **Fast Path (Score >= 0.92):** Confidence = Qdrant Similarity-Score (0.0--1.0). Keine separate Berechnung nötig, da die gecachte Antwort vorab validiert wurde.
- **Standard Path (Claude-Call):** Confidence wird von Claude als Teil der Antwort mitgeliefert. Der System-Prompt instruiert Claude, eine Confidence zwischen 0.0 und 1.0 anzugeben, basierend auf wie gut die bereitgestellten Docs-Chunks die Frage abdecken.

**Schwellenwerte:**

| Schwellenwert | Aktion |
|--------------|--------|
| Qdrant Score >= 0.92 | Fast Path: cached Antwort |
| Claude Confidence >= 0.6 | Normale Antwort (via Haiku) |
| Claude Confidence < 0.6 | Retry mit Sonnet für bessere Qualität |
| Claude Confidence < 0.5 (nach Retry) | Eskalation: Support-Kontakt anbieten |

## FAQ-Cache

### Speicher und Struktur

Der FAQ-Cache ist eine **PostgreSQL-Tabelle** `help_faq_cache`:

- `id`, `question_embedding` (vector), `answer_de`, `answer_en`, `docs_links[]`, `hit_count`, `last_used`, `created_at`

### Population

- **Initial:** Manuell kuratiert -- die 30--50 häufigsten Fragen werden aus dem User Guide und FAQ-Bereich der Docs extrahiert und als Frage-Antwort-Paare gespeichert.
- **Fortlaufend:** Fragen mit Confidence >= 0.9 und Daumen-hoch-Bewertung werden als Kandidaten markiert. Admin kann diese über die Admin-Queue in den Cache aufnehmen.

### Sprachbehandlung im Fast Path

FAQ-Antworten werden in DE und EN gespeichert. Beim Fast Path:

1. Sprache der Frage wird erkannt (einfache Heuristik oder `langdetect`)
2. Wenn DE oder EN: passende gecachte Antwort wird direkt ausgeliefert
3. Wenn andere Sprache: Frage wird an den Standard Path (Claude) weitergeleitet, der die DE/EN-Chunks automatisch in der Zielsprache beantwortet

### Cache-Invalidierung

- Bei Re-Indexierung der Docs werden gecachte Antworten, deren Source-Dokumente sich geändert haben, als `stale` markiert
- Admin kann einzelne Cache-Einträge manuell invalidieren

## Feedback-Loop und Admin-Queue

### Automatisches Erfassen von Wissenslücken

Was wird geloggt:

- Fragen mit Confidence < 0.5
- Fragen mit Daumen-runter-Bewertung
- Fragen, bei denen der Benutzer nachfragt ("Das stimmt nicht")

**Datenstruktur pro Eintrag:**

```json
{
  "question": "Wie exportiere ich nach Moodle?",
  "language": "de",
  "confidence": 0.35,
  "user_role": "teacher",
  "user_tier": "professional",
  "route": "/exam/export",
  "timestamp": "2026-03-23T16:00:00Z",
  "feedback": "thumbs_down",
  "similar_questions_count": 12
}
```

### Admin-Queue

**Ansicht:** Neue Seite unter `/admin/help-feedback`.

**Features:**

- Liste aller unbeantworteten/schlecht bewerteten Fragen
- Gruppiert nach Ähnlichkeit (Clustering via Embeddings)
- Sortierbar nach: Häufigkeit, Datum, Route, Rolle
- Status pro Cluster: `offen` / `in Bearbeitung` / `dokumentiert`

**Workflow:**

1. Admin sieht Cluster "Moodle-Export" (12 Fragen, Route: `/exam/export`)
2. Admin schreibt neuen Docs-Artikel oder erweitert bestehenden
3. Markiert Cluster als `dokumentiert` mit Link zum neuen Artikel
4. Nächster Docs-Index-Lauf nimmt den neuen Artikel auf
5. Zukünftige Fragen zum Thema werden korrekt beantwortet

### Re-Indexierung

- **Automatisch:** Cron-Job (täglich 02:00 UTC) liest alle `.md`-Dateien und aktualisiert `docs_help`
- **Manuell:** Admin kann Re-Index über Button im Admin-Panel auslösen
- **Smart Diff:** Der Indexer speichert den letzten indexierten Git-Commit-SHA in einer DB-Tabelle `help_index_state`. Bei jedem Lauf wird `git diff <last_sha>..HEAD -- docs-site/` ausgeführt. Geänderte Dateien werden neu eingebettet, gelöschte Dateien werden aus Qdrant entfernt (via `source_file` Payload-Filter), umbenannte Dateien werden als Löschung + Neuanlage behandelt. Der initiale Lauf (kein gespeicherter SHA) führt einen Full-Scan durch.

### Metriken-Dashboard

Kennzahlen im Admin-Panel:

- Anzahl Fragen pro Tag/Woche
- Prozent mit positivem Feedback
- Top 10 unbeantwortete Themen
- Durchschnittliche Confidence
- Fast-Path vs. Claude-Call Ratio (Kostenindikator)

## Technische Umsetzung

### Frontend: Widget-Komponente

Technologie: React-Komponente, eingebettet in das bestehende Layout.

```text
frontend/src/components/help/
+-- HelpWidget.tsx          # Floating Button + Panel Container
+-- HelpOnboarding.tsx      # Schritt-für-Schritt Onboarding Flow
+-- HelpContextHint.tsx     # Proaktive Kontext-Hinweise
+-- HelpChat.tsx            # Freier Chat-Modus
+-- HelpMessage.tsx         # Einzelne Chat-Nachricht
+-- HelpFeedback.tsx        # Daumen hoch/runter + Kommentar
+-- SpotlightOverlay.tsx    # Highlight für Onboarding-Schritte
+-- useHelpContext.ts       # Hook: aktuelle Route, Rolle, Tier
```

**Widget-Verhalten:**

- Floating Button immer sichtbar (ausser im Fullscreen-Modus)
- Panel öffnet sich als Slide-in von rechts (ca. 380px breit)
- Kein Overlay über die gesamte App -- Benutzer kann weiterarbeiten
- Responsive: auf Mobile wird das Panel fullscreen
- Tastaturkürzel: `Ctrl+/` (Windows/Linux) bzw. `Cmd+/` (macOS) öffnet/schliesst das Widget. Nur aktiv, wenn kein Eingabefeld fokussiert ist.

### Backend: Help-API

**Neue Endpoints:**

| Methode | Route | Rolle | Beschreibung |
|---------|-------|-------|-------------|
| `POST` | `/api/v1/help/message` | Authentifiziert | Frage senden, Antwort erhalten |
| `GET` | `/api/v1/help/context/{route}` | Authentifiziert | Kontext-Hinweis für Route abrufen |
| `POST` | `/api/v1/help/feedback` | Authentifiziert | Feedback zu einer Antwort senden |
| `GET` | `/api/v1/help/onboarding/status` | Authentifiziert | Onboarding-Fortschritt abrufen |
| `PUT` | `/api/v1/help/onboarding/step` | Authentifiziert | Onboarding-Schritt abschliessen |
| `GET` | `/api/v1/help/status` | Öffentlich | Health-Check: gibt verfügbare Modi zurück |
| `GET` | `/api/v1/help/admin/feedback-queue` | Admin | Feedback-Queue abrufen |
| `PUT` | `/api/v1/help/admin/feedback/{id}` | Admin | Cluster-Status aktualisieren |
| `POST` | `/api/v1/help/admin/reindex` | Admin | Docs Re-Indexierung auslösen |
| `GET` | `/api/v1/help/admin/metrics` | Admin | Metriken-Dashboard Daten |

**Rate Limiting:**

| Endpoint | Limit |
|----------|-------|
| `/api/v1/help/message` | 20 Anfragen pro Benutzer pro Stunde (alle Tiers gleich) |
| `/api/v1/help/feedback` | 60 Anfragen pro Benutzer pro Stunde |
| `/api/v1/help/admin/*` | 120 Anfragen pro Admin pro Stunde |

Die Rate Limits werden über die bestehende Rate-Limiting-Middleware (`middleware/rate_limit.py`) konfiguriert.

**Neue Backend-Services:**

```text
backend/services/
+-- help_service.py         # RAG-Logik für Docs-Fragen
+-- help_context_service.py # Kontext-Hinweise pro Route/Rolle
+-- help_feedback_service.py # Feedback-Speicherung und Clustering
+-- docs_indexer_service.py  # Markdown zu Embedding zu Qdrant
```

### Datenbank: Neue Tabellen

**help_onboarding_progress:**

- `user_id`, `role`, `current_step`, `completed_steps[]`, `completed_at`

**help_conversations:**

- `id`, `user_id`, `messages[]` (JSONB), `route`, `created_at`

**help_feedback:**

- `id`, `question`, `answer`, `confidence`, `rating` (up/down), `user_role`, `user_tier`, `route`, `cluster_id`, `status`, `created_at`

**help_context_hints:**

- `id`, `route_pattern`, `role`, `tier`, `hint_text_de`, `hint_text_en`, `priority`, `active`

**help_faq_cache:**

- `id`, `question_embedding` (vector), `answer_de`, `answer_en`, `docs_links[]`, `source_files[]`, `hit_count`, `last_used`, `stale`, `created_at`

**help_index_state:**

- `id`, `last_indexed_sha`, `last_indexed_at`, `files_indexed`, `files_deleted`

### Qdrant: Neue Collection

**Collection `docs_help`:**

- Getrennt von `documents` (Kursmaterialien)
- Payload: `source_file`, `language`, `section_title`, `content_preview`
- Embedding-Modell: gleich wie bestehend (OpenAI text-embedding-3-small)

### Two-Tier Kostenoptimierung

```text
Frage eingehend
      |
      v
 Embedding + Qdrant Suche
      |
      +-- Score >= 0.92 ---> Cached/Template-Antwort (kostenlos)
      |                      Vorformulierte Antworten für Top-50 FAQ
      |
      +-- Score < 0.92 ----> Claude API Call
                             Kontext: Top-5 Chunks + User-State
                             Modell: claude-haiku (günstig, schnell)
                             Fallback: claude-sonnet (bei Confidence < 0.6)
```

### Fehlerbehandlung

| Szenario | Verhalten |
|----------|-----------|
| Qdrant nicht erreichbar | Frage-Modus deaktiviert. Widget zeigt "Hilfe-Chat vorübergehend nicht verfügbar" + Link zur Docs-Site. Onboarding- und Kontext-Modus bleiben aktiv. |
| Claude API Timeout (>30s) | Antwort: "Die Anfrage hat zu lange gedauert. Bitte versuche es erneut oder besuche unsere Dokumentation." + Link zur relevanten Docs-Seite (basierend auf Route). |
| Claude API Fehler (5xx) | Gleich wie Timeout, plus Logging des Fehlers für Monitoring. |
| Embedding-Fehler | Fallback auf Keyword-Suche in `help_faq_cache` (Volltext-Match auf `answer_de`/`answer_en`). |
| Kein Ergebnis in Qdrant (Score < 0.3) | Direkt als "nicht beantwortbar" klassifiziert, Support-Kontakt angeboten, in Feedback-Queue geloggt. |

## Docs-Site (Material for MkDocs)

### Verzeichnisstruktur

```text
docs-site/
+-- mkdocs.yml              # MkDocs Material Konfiguration
+-- docs/
    +-- index.md            # Landing Page
    +-- getting-started/
    |   +-- quickstart.md   # Erste Prüfung in 5 Minuten
    |   +-- requirements.md # Browser, Systemanforderungen
    |   +-- registration.md # Account erstellen
    +-- user-guide/
    |   +-- documents.md    # Dokumente hochladen und verwalten
    |   +-- exam-create.md  # KI-Prüfung erstellen
    |   +-- rag-exam.md     # RAG-basierte Prüfungen
    |   +-- chatbot.md      # Document ChatBot nutzen
    |   +-- exam-export.md  # Prüfungen exportieren
    |   +-- best-practices.md
    +-- admin-guide/
    |   +-- deployment.md   # Installation und Deployment
    |   +-- user-mgmt.md    # Benutzerverwaltung
    |   +-- institutions.md # Institutionen einrichten
    |   +-- prompts.md      # Prompt Management
    |   +-- subscription.md # Tiers und Quotas
    |   +-- monitoring.md   # Logs, Metriken
    +-- faq/
    |   +-- general.md
    |   +-- troubleshooting.md
    +-- changelog.md
    +-- screenshots/
```

### i18n-Strategie

Plugin: `mkdocs-static-i18n`.

```text
docs/
+-- user-guide/
    +-- documents.md        # Deutsch (Default)
    +-- documents.en.md     # English
```

- Deutsch als Default-Sprache (DACH-Fokus)
- Englisch via `.en.md`-Suffix
- Sprachumschalter oben rechts in der Docs-Site
- Fehlende Übersetzungen fallen auf Deutsch zurück

### Hosting

- GitHub Pages via GitHub Actions (kostenlos, bei jedem Push auf `main`)
- Docs leben unter `docs-site/` (getrennt von `docs/` für interne Dev-Docs)

### Verhältnis zu Mintlify

| Docs-Site | Zweck | Zielgruppe |
|-----------|-------|------------|
| MkDocs Material | Benutzerhandbuch + Admin-Guide | Dozenten, IT-Admins |
| Mintlify | API-Referenz + Developer-Docs | Entwickler (Backlog) |

Mintlify wird vorerst nicht angefasst.

## Nicht im Scope

- Audio-Overviews / TTS (Ansatz C verworfen)
- Verschmelzung mit Document ChatBot (bewusst getrennt)
- Entwickler-Dokumentation (bleibt bei Mintlify)
- Multi-Tenant Docs (alle Institutionen sehen gleiche Docs)
- Video-Tutorials (separates Projekt)
