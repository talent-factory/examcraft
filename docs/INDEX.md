# 📚 ExamCraft AI - Dokumentations-Index

> **Zentrale Übersicht aller verfügbaren Dokumentationen**

**Version**: 1.0.0
**Stand**: Oktober 2025

---

## 🎯 Schnellzugriff

### 👥 Für Benutzer

| Dokument | Beschreibung | Zielgruppe |
|----------|--------------|------------|
| **[📚 Benutzerhandbuch](USER_GUIDE.md)** | Vollständige Anleitung zur Nutzung von ExamCraft AI | Dozenten, Lehrkräfte |
| **[🎛️ Admin Guide: Prompt Management](ADMIN_PROMPT_MANAGEMENT.md)** | Verwaltung der AI-Prompts | Administratoren, Prompt Engineers |
| **[📸 Screenshot-Anleitung](SCREENSHOTS.md)** | Anleitung zur Erstellung von Screenshots | Dokumentations-Team |

### 📊 Für Stakeholder

> **Note:** Business documentation has been moved to the private `packages/premium/internal/` directory.
> For public roadmap information, see the [main README.md](../README.md#-public-roadmap).

### 🔧 Für Entwickler

| Dokument | Beschreibung | Zielgruppe |
|----------|--------------|------------|
| **[🚀 Deployment Guide](../DEPLOYMENT.md)** | Production Deployment auf Fly.io | DevOps, Entwickler |
| **[🔄 Qdrant Migration](QDRANT_MIGRATION.md)** | Migration zu Qdrant Cloud | Backend-Entwickler |
| **[📖 API Dokumentation](http://localhost:8000/docs)** | Interaktive API-Docs (lokal) | Backend-Entwickler |

---

## 📖 Dokumentations-Kategorien

### 1️⃣ Benutzer-Dokumentation

**Ziel**: Endbenutzer befähigen, ExamCraft AI effektiv zu nutzen

**Dokumente:**

- **[USER_GUIDE.md](USER_GUIDE.md)** - Vollständiges Benutzerhandbuch
  - Erste Schritte
  - Dokumente hochladen & verwalten
  - KI-Prüfungen erstellen
  - RAG-basierte Prüfungen
  - Dokument ChatBot
  - Tipps & Best Practices
  - FAQ & Fehlerbehebung

**Umfang**: 300+ Zeilen, 10 Hauptkapitel

---

### 2️⃣ Administrator-Dokumentation

**Ziel**: Administratoren befähigen, das System zu konfigurieren und zu optimieren

**Dokumente:**

- **[ADMIN_PROMPT_MANAGEMENT.md](ADMIN_PROMPT_MANAGEMENT.md)** - Prompt Management Guide
  - Architektur & Datenmodell
  - Prompt Library Verwaltung
  - Prompt Editor & Templates
  - Version Control & Rollback
  - Usage Analytics
  - Semantic Search
  - Best Practices & Troubleshooting

**Umfang**: 300+ Zeilen, 9 Hauptkapitel

---

### 3️⃣ Business-Dokumentation

**Ziel**: Stakeholder über Geschäftspotential und Strategie informieren

> **Note:** Business documentation has been moved to the private `packages/premium/internal/` directory for security reasons.
>
> **Available documents (internal only):**
> - Executive Summary → `packages/premium/internal/EXECUTIVE_SUMMARY.md`
> - Feature Overview → `packages/premium/internal/FEATURES_COMPETITIVE.md`
> - Monetization Strategy → `packages/premium/internal/MONETIZATION_STRATEGY.md`
> - Product Roadmap → `packages/premium/internal/ROADMAP_INTERNAL.md`
> - Release Timeline → `packages/premium/internal/RELEASE_TIMELINE.md`
>
> **Public information:** See [main README.md](../README.md#-public-roadmap) for public roadmap.

---

### 4️⃣ Technische Dokumentation

**Ziel**: Entwickler befähigen, das System zu verstehen, zu erweitern und zu deployen

**Dokumente:**

- **[../DEPLOYMENT.md](../DEPLOYMENT.md)** - Deployment Guide
  - Fly.io Setup
  - Environment Variables
  - Database Configuration
  - CI/CD Pipeline

- **[QDRANT_MIGRATION.md](QDRANT_MIGRATION.md)** - Qdrant Migration
  - ChromaDB → Qdrant Cloud
  - Collection Setup
  - Data Migration
  - Performance Tuning

- **[API Docs](http://localhost:8000/docs)** - FastAPI Swagger UI
  - REST API Endpoints
  - Request/Response Schemas
  - Authentication
  - Rate Limiting

**Umfang**: 800+ Zeilen gesamt

---

### 5️⃣ Visuelle Dokumentation

**Ziel**: Screenshots und Diagramme für besseres Verständnis bereitstellen

**Dokumente:**

- **[SCREENSHOTS.md](SCREENSHOTS.md)** - Screenshot-Anleitung
  - 19 definierte Screenshots
  - Detaillierte Anweisungen
  - Browser-Einstellungen
  - Nachbearbeitung
  - Integration in Docs

**Verzeichnis:**

- **[screenshots/](screenshots/)** - Screenshot-Sammlung
  - Hauptnavigation
  - KI-Prüfung erstellen
  - Dokumente hochladen
  - RAG-Prüfung
  - ChatBot
  - Prompt Management

**Umfang**: 300+ Zeilen Anleitung, 19 Screenshots geplant

---

## 🎯 Dokumentations-Roadmap

### ✅ Abgeschlossen (v1.0)

- [x] Benutzerhandbuch (Mintlify User Guide)
- [x] Admin Guide (Mintlify Admin Guide)
- [x] Screenshot-Anleitung (SCREENSHOTS.md)
- [x] Feature-Übersicht (Moved to Premium Package)
- [x] Executive Summary (Moved to Premium Package)
- [x] Monetization Strategy (Moved to Premium Package)
- [x] Product Roadmap (Moved to Premium Package)
- [x] Release Timeline (Moved to Premium Package)
- [x] Deployment Guide (../DEPLOYMENT.md)
- [x] Qdrant Migration (QDRANT_MIGRATION.md)

### 🔄 In Arbeit

- [ ] Screenshots erstellen (19 Stück)
- [ ] Video-Tutorials (YouTube)
- [ ] Interactive Demos (Loom)

### 📋 Geplant (v1.1)

- [ ] Developer Guide (DEVELOPER_GUIDE.md)
- [ ] API Integration Examples (API_EXAMPLES.md)
- [ ] Troubleshooting Guide (TROUBLESHOOTING.md)
- [ ] Performance Tuning (PERFORMANCE.md)
- [ ] Security Best Practices (SECURITY.md)
- [ ] Backup & Recovery (BACKUP.md)

---

## 📊 Dokumentations-Statistiken

### Umfang

| Kategorie | Dokumente | Zeilen | Status |
|-----------|-----------|--------|--------|
| Benutzer | 2 (Mintlify) | 900+ | ✅ Fertig |
| Business | 5 (Private) | 1500+ | ✅ Fertig (Internal) |
| Technisch | 3 | 800+ | ✅ Fertig |
| Visuell | 2 | 300+ | 🔄 In Arbeit |
| **Gesamt** | **12** | **3500+** | **85% Fertig** |

### Zielgruppen-Abdeckung

- ✅ **Endbenutzer** - 100% (Mintlify User Guide, Screenshots)
- ✅ **Administratoren** - 100% (Mintlify Admin Guide, Deployment)
- ✅ **Stakeholder** - 100% (Internal Business Docs in Premium Package)
- ✅ **Entwickler** - 80% (API Docs, Deployment, Migration)
- 🔄 **Marketing** - 60% (Features, Use Cases, Screenshots in Arbeit)

---

## 🔍 Dokumentations-Suche

### Nach Thema

**Erste Schritte:**

- [USER_GUIDE.md - Erste Schritte](USER_GUIDE.md#erste-schritte)
- [README.md - Quick Start](../README.md#quick-start)

**Features:**

- [README.md - Features](../README.md#-core-features-open-source)
- [Mintlify Docs - Features](https://docs.examcraft.ch/core-features)

**Deployment:**

- [../DEPLOYMENT.md](../DEPLOYMENT.md)
- [README.md - Docker Installation](../README.md#docker-installation)

**Prompt Management:**

- [Mintlify Docs - Admin Guide](https://docs.examcraft.ch/guides/admin-guide)

**Business:**

> Business documentation is now private. See `packages/premium/internal/` for internal access.

### Nach Rolle

**Dozent/Lehrkraft:**

1. [Mintlify Docs - User Guide](https://docs.examcraft.ch/guides/user-guide) - Hauptdokumentation
2. [README.md - Features](../README.md#-core-features-open-source) - Feature-Übersicht
3. [SCREENSHOTS.md](SCREENSHOTS.md) - Visuelle Anleitung

**Administrator:**

1. [Mintlify Docs - Admin Guide](https://docs.examcraft.ch/guides/admin-guide) - Prompt Management
2. [../DEPLOYMENT.md](../DEPLOYMENT.md) - Deployment
3. [QDRANT_MIGRATION.md](QDRANT_MIGRATION.md) - Vector DB Setup

**Manager/Investor:**

> Business documentation is now private. See `packages/premium/internal/` for internal access.

**Entwickler:**

1. [API Docs](http://localhost:8000/docs) - API Reference
2. [../DEPLOYMENT.md](../DEPLOYMENT.md) - Deployment
3. [README.md](../README.md) - Development Setup

---

## 🤝 Beitragen zur Dokumentation

### Dokumentations-Standards

**Markdown-Konventionen:**

- Überschriften: `#` für H1, `##` für H2, etc.
- Listen: `-` für ungeordnet, `1.` für geordnet
- Code: ` ``` ` für Code-Blöcke
- Links: `[Text](URL)`
- Bilder: `![Alt](URL)`

**Struktur:**

- Inhaltsverzeichnis am Anfang
- Klare Abschnitte mit Überschriften
- Beispiele und Screenshots
- FAQ-Sektion
- Letzte Aktualisierung am Ende

**Sprache:**

- Deutsch für Benutzer-Docs
- Englisch für technische Docs (optional)
- Klare, präzise Formulierungen
- Aktive Sprache

### Neue Dokumentation erstellen

1. **Template verwenden** (falls vorhanden)
2. **Inhaltsverzeichnis** erstellen
3. **Abschnitte** strukturieren
4. **Beispiele** hinzufügen
5. **Screenshots** integrieren
6. **Review** durch Team
7. **Commit** mit aussagekräftiger Message
8. **Index aktualisieren** (diese Datei)

### Bestehende Dokumentation aktualisieren

1. **Änderungen** vornehmen
2. **"Letzte Aktualisierung"** Datum anpassen
3. **Versionsnummer** erhöhen (falls Major Update)
4. **Changelog** aktualisieren (falls vorhanden)
5. **Commit** mit Beschreibung der Änderungen

---

## 📞 Support & Feedback

**Dokumentations-Feedback:**

- Email: <docs@examcraft.ai>
- GitHub Issues: [Documentation](https://github.com/examcraft/issues?label=documentation)

**Fragen zur Dokumentation:**

- Slack: #documentation
- Discord: #docs-help

**Verbesserungsvorschläge:**

- Pull Requests willkommen!
- Issues für fehlende Dokumentation
- Feedback zu Klarheit und Vollständigkeit

---

## 📋 Checkliste für neue Releases

Vor jedem Release sicherstellen:

- [ ] Alle Dokumente aktualisiert
- [ ] Screenshots aktuell
- [ ] API Docs generiert
- [ ] Changelog aktualisiert
- [ ] Version Numbers konsistent
- [ ] Links funktionieren
- [ ] Rechtschreibung geprüft
- [ ] Technische Korrektheit verifiziert
- [ ] Peer Review durchgeführt
- [ ] Index aktualisiert

---

**Letzte Aktualisierung**: Oktober 2025
**Version**: 1.0.0
**Maintainer**: ExamCraft AI Documentation Team
