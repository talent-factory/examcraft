# 🎛️ Admin Guide: Prompt Knowledge Base Management

> **Vollständige Anleitung für Administratoren zur Verwaltung der AI-Prompts in ExamCraft AI**

**Version**: 1.0.0  
**Stand**: Oktober 2025  
**Zielgruppe**: System-Administratoren, Prompt Engineers

---

## 📖 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Architektur](#architektur)
3. [Prompt Library](#prompt-library)
4. [Prompt Editor](#prompt-editor)
5. [Version Control](#version-control)
6. [Usage Analytics](#usage-analytics)
7. [Semantic Search](#semantic-search)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Übersicht

### Was ist das Prompt Management System?

Das Prompt Management System ermöglicht die **zentrale Verwaltung aller AI-Prompts** ohne Code-Änderungen. Es bietet:

- ✅ **Versionierung** - Alle Änderungen werden getrackt
- ✅ **Rollback** - Zurück zu früheren Versionen
- ✅ **Semantic Search** - Finde Prompts nach Bedeutung
- ✅ **Analytics** - Überwache Performance und Kosten
- ✅ **Template System** - Wiederverwendbare Prompts mit Variablen
- ✅ **Web-Interface** - Keine Code-Änderungen nötig

### Warum Prompt Management?

**Vorteile:**
- 🚀 **Schnellere Iteration** - Teste neue Prompts ohne Deployment
- 📊 **Datengetrieben** - Entscheide basierend auf Metriken
- 🔄 **Sicherheit** - Rollback bei Problemen
- 👥 **Kollaboration** - Team kann gemeinsam optimieren
- 💰 **Kostenoptimierung** - Reduziere Token-Verbrauch

### Zugriff

**URL**: `http://localhost:3000` → Tab "Prompt Management"

**Berechtigungen**: Nur für Administratoren

---

## 🏗️ Architektur

### System-Komponenten

```
┌─────────────────────────────────────────────────────┐
│  React Frontend (Material-UI)                       │
│  ├─ Prompt Library                                  │
│  ├─ Prompt Editor                                   │
│  ├─ Version History                                 │
│  ├─ Usage Analytics                                 │
│  └─ Semantic Search                                 │
├─────────────────────────────────────────────────────┤
│  API Layer (Axios)                                  │
│  └─ /api/v1/prompts/*                               │
├─────────────────────────────────────────────────────┤
│  Backend Services (FastAPI)                         │
│  ├─ PromptService (CRUD)                            │
│  ├─ PromptVectorService (Search)                    │
│  └─ PromptUsageLogger                               │
├─────────────────────────────────────────────────────┤
│  Datenbanken                                        │
│  ├─ PostgreSQL (Prompts, Versionen, Logs)          │
│  └─ Qdrant (Vector Search)                          │
└─────────────────────────────────────────────────────┘
```

### Datenmodell

**Tabelle: `prompts`**
```sql
- id (UUID, PK)
- name (VARCHAR, UNIQUE)
- content (TEXT)
- description (TEXT)
- category (ENUM: system_prompt, user_prompt, few_shot_example, template)
- tags (TEXT[])
- use_case (VARCHAR)
- version (INTEGER)
- is_active (BOOLEAN)
- parent_id (UUID, FK → prompts.id)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

**Tabelle: `prompt_usage_logs`**
```sql
- id (UUID, PK)
- prompt_id (UUID, FK)
- prompt_version (INTEGER)
- use_case (VARCHAR)
- tokens_used (INTEGER)
- latency_ms (INTEGER)
- success (BOOLEAN)
- timestamp (TIMESTAMP)
```

### API Endpoints

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/v1/prompts` | Liste aller Prompts |
| GET | `/api/v1/prompts/{id}` | Einzelner Prompt |
| POST | `/api/v1/prompts` | Neuer Prompt |
| PUT | `/api/v1/prompts/{id}` | Prompt aktualisieren |
| DELETE | `/api/v1/prompts/{id}` | Prompt löschen |
| POST | `/api/v1/prompts/{id}/versions` | Neue Version |
| GET | `/api/v1/prompts/versions/{name}` | Version History |
| POST | `/api/v1/prompts/search` | Semantic Search |
| GET | `/api/v1/prompts/{id}/usage` | Usage Logs |
| PATCH | `/api/v1/prompts/{id}/active` | Aktivieren/Deaktivieren |

---

## 📚 Prompt Library

### Übersicht

Die Prompt Library zeigt alle verfügbaren Prompts in einem Grid-Layout.

**Features:**
- 🔍 **Suche** - Durchsuche Name, Beschreibung, Tags
- 🏷️ **Filter** - Nach Kategorie filtern
- 📊 **Sortierung** - Nach Name, Datum, Verwendungen
- 🎨 **Farbcodierung** - Kategorien visuell unterscheiden

### Kategorien

**System Prompt** (Blau)
- Grundlegende Instruktionen für AI
- Definiert Verhalten und Rolle
- Beispiel: "Du bist ein Experte für Prüfungsfragen..."

**User Prompt** (Grün)
- Spezifische Aufgaben für AI
- Enthält konkrete Anweisungen
- Beispiel: "Generiere 5 Multiple Choice Fragen zu {topic}"

**Few-Shot Example** (Orange)
- Beispiele für gewünschtes Output-Format
- Hilft AI, Struktur zu verstehen
- Beispiel: Beispiel-Frage mit Antworten

**Template** (Lila)
- Wiederverwendbare Prompt-Vorlagen
- Enthält Variablen {variable}
- Beispiel: "Erstelle {count} Fragen zum Thema {topic}"

### Aktionen

**Bearbeiten** (✏️)
- Öffnet Prompt Editor
- Lädt aktuelle Version
- Ermöglicht Änderungen

**Versionen** (🕐)
- Zeigt Version History
- Ermöglicht Rollback
- Vergleicht Versionen

**Löschen** (🗑️)
- Entfernt Prompt permanent
- Sicherheitsabfrage erforderlich
- **Achtung**: Kann nicht rückgängig gemacht werden!

### Suche & Filter

**Suchfunktion:**
- Echtzeit-Filterung
- Durchsucht: Name, Beschreibung, Tags
- Case-insensitive

**Kategorie-Filter:**
- Alle Kategorien
- System Prompts
- User Prompts
- Few-Shot Examples
- Templates

---

## ✏️ Prompt Editor

### Neuen Prompt erstellen

**Schritt 1: Grundinformationen**

**Name:**
- Format: `snake_case`
- Eindeutig im System
- Beispiel: `system_prompt_question_generation`

**Beschreibung:**
- Kurze Erklärung (1-2 Sätze)
- Zweck und Verwendung
- Beispiel: "Generiert Multiple Choice Fragen aus Dokumenten"

**Schritt 2: Kategorisierung**

**Kategorie:**
- Wähle passende Kategorie
- Beeinflusst Verwendung im System

**Use Case:**
- Spezifischer Anwendungsfall
- Beispiele: `question_generation`, `chatbot`, `evaluation`

**Tags:**
- Schlagwörter für Suche
- Mehrere Tags möglich
- Beispiele: `education`, `multiple-choice`, `bloom-taxonomy`

**Schritt 3: Content erstellen**

**Editor-Tabs:**
- **Bearbeiten** - Markdown-Editor
- **Vorschau** - Gerenderte Ansicht

**Template-Variablen:**

Syntax: `{variable_name}`

Beispiel:
```markdown
Du bist ein Experte für {subject}.

Erstelle {count} Fragen zum Thema "{topic}" mit Schwierigkeitsgrad {difficulty}.

Anforderungen:
- Bloom-Level: {bloom_level}
- Fragetyp: {question_type}
- Sprache: {language}
```

**Verfügbare Variablen:**
- `{topic}` - Thema der Fragen
- `{count}` - Anzahl Fragen
- `{difficulty}` - Schwierigkeitsgrad
- `{question_type}` - Fragetyp
- `{language}` - Sprache
- `{context}` - RAG-Kontext
- `{bloom_level}` - Bloom-Taxonomie Level

**Schritt 4: Aktivierung**

**Aktiv-Toggle:**
- ☑️ **Aktiv** - Prompt wird sofort verwendet
- ☐ **Inaktiv** - Prompt ist gespeichert, aber nicht aktiv

**Empfehlung:**
- Teste neue Prompts zuerst inaktiv
- Aktiviere nach erfolgreichen Tests

### Bestehenden Prompt bearbeiten

**Änderungen vornehmen:**
1. Öffne Prompt in Editor
2. Nehme Änderungen vor
3. Speichere

**Versionierung:**
- Jede Speicherung erstellt neue Version
- Alte Versionen bleiben erhalten
- Nur neueste Version ist aktiv

**Best Practice:**
- Beschreibe Änderungen in Commit-Message
- Teste vor Aktivierung
- Überwache Usage Analytics nach Änderung

---

## 🕐 Version Control

### Version History anzeigen

**Zugriff:**
- Klicke "Versionen" in Prompt Library
- Oder: "Versionen anzeigen" in Editor

**Anzeige:**
- Tabelle mit allen Versionen
- Sortiert nach Version (neueste zuerst)
- Zeigt: Version, Status, Beschreibung, Datum

### Versionen vergleichen

**Vorschau:**
1. Klicke "Vorschau" bei gewünschter Version
2. Dialog zeigt:
   - Beschreibung
   - Content
   - Tags
   - Metadaten

**Vergleich:**
- Aktuell: Manueller Vergleich
- Geplant (v1.1): Diff-Ansicht

### Rollback durchführen

**Wann Rollback?**
- Neue Version funktioniert nicht
- Performance-Probleme
- Qualitätsverschlechterung
- Fehlerhafte Generierungen

**Vorgehensweise:**
1. Öffne Version History
2. Finde gewünschte Version
3. Klicke "Aktivieren"
4. Bestätige Sicherheitsabfrage
5. Alte Version wird aktiv

**Wichtig:**
- Nur eine Version kann aktiv sein
- Rollback erstellt keine neue Version
- Alte Version wird reaktiviert

### Versionsmanagement Best Practices

**Naming Convention:**
- v1.0 - Initial Release
- v1.1 - Minor Update
- v2.0 - Major Rewrite

**Beschreibungen:**
- Kurz und prägnant
- Was wurde geändert?
- Warum wurde geändert?

**Testing:**
- Teste neue Versionen vor Aktivierung
- Überwache Metriken nach Rollout
- Halte Rollback-Plan bereit

---

## 📊 Usage Analytics

### Metriken-Übersicht

**4 Haupt-Metriken:**

**1. Verwendungen**
- Anzahl Aufrufe des Prompts
- Zeigt Popularität
- Hilft bei Priorisierung

**2. Erfolgsrate**
- % erfolgreiche Generierungen
- Indikator für Qualität
- Ziel: >95%

**3. Ø Latenz**
- Durchschnittliche Antwortzeit in ms
- Performance-Indikator
- Ziel: <2000ms

**4. Tokens Total**
- Gesamtverbrauch an Tokens
- Kosten-Indikator
- Optimierungspotential

### Verwendungsverlauf

**Tabelle zeigt:**
- Timestamp
- Use Case
- Tokens verwendet
- Latenz
- Erfolg/Fehler

**Filterung:**
- Letzte 100 Verwendungen
- Sortiert nach Datum (neueste zuerst)

### Interpretation

**Erfolgsrate:**
- >95%: Sehr gut ✅
- 90-95%: Gut ✅
- 80-90%: Akzeptabel ⚠️
- <80%: Optimierung nötig ❌

**Latenz:**
- <1000ms: Sehr schnell ✅
- 1000-2000ms: Schnell ✅
- 2000-5000ms: Akzeptabel ⚠️
- >5000ms: Zu langsam ❌

**Token-Verbrauch:**
- Vergleiche mit ähnlichen Prompts
- Identifiziere Optimierungspotential
- Reduziere unnötige Tokens

### Optimierung basierend auf Analytics

**Niedrige Erfolgsrate:**
1. Überprüfe Prompt-Formulierung
2. Füge mehr Kontext hinzu
3. Verbessere Beispiele
4. Teste mit verschiedenen Inputs

**Hohe Latenz:**
1. Reduziere Prompt-Länge
2. Entferne unnötige Instruktionen
3. Optimiere Template-Variablen
4. Prüfe API-Performance

**Hoher Token-Verbrauch:**
1. Kürze Prompt-Text
2. Entferne Redundanzen
3. Nutze effizientere Formulierungen
4. Teste kürzere Varianten

---

## 🔍 Semantic Search

### Übersicht

Semantic Search findet Prompts basierend auf **Bedeutung**, nicht nur Keywords.

**Technologie:**
- OpenAI Embeddings (text-embedding-3-small)
- Qdrant Vector Database
- Cosine Similarity

### Suchparameter

**Query:**
- Natürlichsprachige Suchanfrage
- Beispiel: "Generiere Multiple Choice Fragen für Informatik"

**Filter:**
- **Kategorie** - Einschränkung auf Kategorie
- **Use Case** - Spezifischer Anwendungsfall
- **Tags** - Schlagwörter

**Advanced:**
- **Limit** - Anzahl Ergebnisse (1-20)
- **Score Threshold** - Minimum Similarity (0-1)

### Ergebnisse interpretieren

**Similarity Score:**
- 0.9-1.0: Sehr relevant ✅
- 0.7-0.9: Relevant ✅
- 0.5-0.7: Teilweise relevant ⚠️
- <0.5: Wenig relevant ❌

**Farbcodierung:**
- Grün: >0.9
- Blau: 0.7-0.9
- Orange: 0.5-0.7
- Grau: <0.5

### Anwendungsfälle

**1. Ähnliche Prompts finden**
- Suche: "Fragen zu Algorithmen"
- Finde alle relevanten Prompts
- Vergleiche Ansätze

**2. Duplikate identifizieren**
- Suche nach Prompt-Namen
- Finde ähnliche Prompts
- Konsolidiere wenn nötig

**3. Best Practices entdecken**
- Suche nach Use Case
- Finde erfolgreiche Prompts
- Lerne von Beispielen

---

## 💡 Best Practices

### Prompt-Erstellung

**Struktur:**
```markdown
# Rolle
Du bist ein [Experte/Assistent] für [Bereich].

# Aufgabe
[Klare Beschreibung der Aufgabe]

# Anforderungen
- [Anforderung 1]
- [Anforderung 2]
- [Anforderung 3]

# Format
[Gewünschtes Output-Format]

# Beispiel
[Optional: Beispiel-Output]
```

**Dos:**
- ✅ Klare, präzise Instruktionen
- ✅ Konkrete Beispiele
- ✅ Strukturierte Formatierung
- ✅ Template-Variablen nutzen
- ✅ Testen vor Aktivierung

**Don'ts:**
- ❌ Vage Formulierungen
- ❌ Zu lange Prompts (>2000 Tokens)
- ❌ Widersprüchliche Anweisungen
- ❌ Unnötige Wiederholungen
- ❌ Direkt in Production aktivieren

### Versionierung

**Semantic Versioning:**
- v1.0.0 - Major.Minor.Patch
- Major: Breaking Changes
- Minor: Neue Features
- Patch: Bugfixes

**Changelog:**
- Dokumentiere alle Änderungen
- Nutze Beschreibungsfeld
- Referenziere Issues/Tickets

### Testing

**Test-Prozess:**
1. Erstelle Prompt (inaktiv)
2. Teste mit verschiedenen Inputs
3. Überprüfe Outputs
4. Messe Performance
5. Aktiviere wenn erfolgreich

**Test-Szenarien:**
- Normale Inputs
- Edge Cases
- Fehlerhafte Inputs
- Verschiedene Sprachen
- Verschiedene Schwierigkeitsgrade

### Monitoring

**Regelmäßige Checks:**
- Wöchentlich: Usage Analytics
- Monatlich: Erfolgsraten
- Quartalsweise: Optimierungspotential

**Alerts:**
- Erfolgsrate <90%
- Latenz >3000ms
- Ungewöhnlich hoher Token-Verbrauch

---

## 🔧 Troubleshooting

### Häufige Probleme

**Problem: Prompt wird nicht verwendet**

Lösungen:
1. Prüfe ob Prompt aktiv ist
2. Prüfe Use Case Zuordnung
3. Prüfe ob neueste Version aktiv
4. Restart Backend-Service

**Problem: Niedrige Erfolgsrate**

Lösungen:
1. Überprüfe Prompt-Formulierung
2. Füge mehr Kontext hinzu
3. Teste mit verschiedenen Inputs
4. Vergleiche mit erfolgreichen Prompts

**Problem: Hohe Latenz**

Lösungen:
1. Reduziere Prompt-Länge
2. Optimiere Template-Variablen
3. Prüfe API-Performance
4. Kontaktiere Support

**Problem: Semantic Search findet nichts**

Lösungen:
1. Reduziere Score Threshold
2. Erweitere Suchanfrage
3. Entferne Filter
4. Prüfe ob Prompts indexiert sind

### Logs & Debugging

**Backend Logs:**
```bash
docker-compose logs -f backend | grep prompt
```

**Database Queries:**
```sql
-- Alle aktiven Prompts
SELECT * FROM prompts WHERE is_active = true;

-- Usage Statistics
SELECT 
  prompt_id,
  COUNT(*) as uses,
  AVG(latency_ms) as avg_latency,
  SUM(tokens_used) as total_tokens
FROM prompt_usage_logs
GROUP BY prompt_id;
```

**Vector Search Status:**
```bash
# Qdrant Collection Info
curl http://localhost:6333/collections/prompts_knowledge_base
```

---

## 📞 Support

**Technische Fragen:**
- Email: admin@examcraft.ai
- Slack: #prompt-management

**Dokumentation:**
- [API Docs](http://localhost:8000/docs)
- [GitHub Wiki](https://github.com/examcraft/wiki)

---

**Letzte Aktualisierung**: Oktober 2025  
**Version**: 1.0.0  
**Autor**: ExamCraft AI Team

