# 🎯 Workshop-Präsentation erstellen

Erstelle eine professionelle Präsentation über ExamCraft AI für Workshop-Teilnehmende mit Fokus auf die praktischen Anwendungsschritte.

## Aufgabe

Du sollst eine umfassende Workshop-Präsentation erstellen, die:

1. **ExamCraft AI Plattform erklärt**:
   - KI-gestützte Prüfungserstellung für OpenBook-Prüfungen
   - Automatische Generierung von Prüfungsaufgaben aus Lehrmaterialien
   - Intelligente Bewertungskriterien und Musterlösungen

2. **Workshop-Teilnehmende durch den kompletten Prozess führt**:
   - Document Upload & Processing Pipeline
   - Semantic Search & Vector Database Integration
   - LLM-basierte Question Generation mit Claude API
   - Quality Review & Approval Workflow
   - Exam Composition & Export

3. **Praktische Anwendung demonstriert**:
   - Live-Demo-Szenarien vorbereitet
   - Hands-On Übungen für Teilnehmende
   - Konkrete Use Cases für verschiedene Fachbereiche

## Plattform-Details

<platform_details>
**ExamCraft AI** ist eine KI-gestützte Plattform zur automatischen Erstellung von Prüfungsaufgaben für OpenBook-Prüfungen.

**Core-Features:**

- **Document Processing**: Upload & Verarbeitung von PDF, DOC, Markdown-Dateien mit Docling
- **Vector Database**: Semantic Search mit ChromaDB und sentence-transformers (all-MiniLM-L6-v2)
- **AI Question Generation**: Claude API Integration mit PydanticAI für strukturierte Outputs
- **Quality Assurance**: Review Interface für Dozenten mit Approval Workflow
- **Export System**: Multiple Formate (PDF, Word, Moodle XML, Canvas LMS)

**Technischer Stack:**

- Backend: FastAPI + Python mit async Processing
- Frontend: React 18 + TypeScript mit TanStack Query
- Database: PostgreSQL + Redis für Caching
- AI: Claude API mit Rate Limiting und Cost Tracking
- Search: ChromaDB für Vector Storage
- Infrastructure: Docker Compose Development Environment

**Unique Value Proposition:**

- Bloom Taxonomy Integration für verschiedene Schwierigkeitsgrade
- Multi-Tier Lösungen (A/B/C Level) für unterschiedliche Leistungsniveaus
- Source Citation Integration für nachvollziehbare Quellenangaben
- RAG-basierte Kontextintegration für präzise Aufgabenstellung
</platform_details>

## Workshop-Anforderungen

<presentation_requirements>
**Zielgruppe**: Dozenten, Prüfungsverantwortliche, Educational Technology Enthusiasts

**Workshop-Kontext**: Blended Learning Tagung - Praktische AI-Tools für die Lehre

**Präsentations-Ziele:**

- Verständnis für AI-gestützte Prüfungserstellung schaffen
- Praktische Anwendung demonstrieren und erlebbar machen
- Implementierungsschritte für eigene Institution aufzeigen
- Q&A Session vorbereiten mit häufigen Fragen

**Interaktive Elemente:**

- Live-Demo mit echten Dokumenten
- Hands-On Session für Teilnehmende
- Beispieldokumente aus verschiedenen Fachbereichen
- Diskussion über Anwendungsmöglichkeiten

**Technische Demonstration:**

- Document Upload & Processing in Echtzeit
- Vector Search Capabilities zeigen
- Question Generation live erleben
- Review & Approval Workflow durchspielen
</presentation_requirements>

## Präsentationsstruktur

Deine Präsentation soll folgende Slides enthalten:

### 🎯 **Kern-Slides (8-12 Slides)**

1. **Titel & Welcome** - ExamCraft AI + Workshop-Agenda
2. **Problem-Statement** - Herausforderungen bei traditioneller Prüfungserstellung
3. **Solution Overview** - KI-gestützte Lösung mit ExamCraft AI
4. **Live Demo Ankündigung** - Was die Teilnehmenden erleben werden
5. **Technical Architecture** - Überblick über die Komponenten
6. **Workflow Step 1** - Document Upload & Processing Pipeline
7. **Workflow Step 2** - Semantic Search & Vector Database
8. **Workflow Step 3** - AI Question Generation mit Claude
9. **Workflow Step 4** - Quality Review & Approval
10. **Benefits & ROI** - Zeitersparnis, Qualität, Konsistenz
11. **Use Cases** - Verschiedene Fachbereiche und Szenarien
12. **Implementation & Next Steps** - Wie können Institutionen starten?

### 🔧 **Technische Deep-Dive Slides (3-5 Slides)**

13. **RAG Architecture** - Retrieval Augmented Generation erklärt
14. **Prompt Engineering** - Wie Claude optimale Questions generiert
15. **Quality Assurance** - Bloom Taxonomy und Multi-Tier Solutions
16. **Integration Options** - LMS Integration, Export Formate
17. **Security & Privacy** - Datenschutz und Compliance

### 🎪 **Workshop-Aktivität Slides (2-3 Slides)**

18. **Hands-On Activity** - Teilnehmende probieren selbst aus
19. **Discussion & Q&A** - Erfahrungsaustausch und Fragen
20. **Wrap-Up & Contact** - Zusammenfassung und Kontaktdaten

## Anforderungen pro Slide

Für jede Slide bereitstellen:

- **📋 Slide-Titel**: Prägnant und aussagekräftig
- **🎯 Hauptinhalt**: 3-5 Bullet Points (präzise aber informativ)
- **🎤 Speaker Notes**: Zusätzlicher Kontext und Talking Points
- **📊 Visual Suggestions**: Diagramme, Screenshots, Demos
- **⏱️ Timing**: Geschätzte Dauer für jede Slide

## Output-Format

Eine Planung in folgendem Format:

```text
<presentation>

=== SLIDE 1: [Titel] ===
**Slide Content:**
• Bullet Point 1
• Bullet Point 2
• Bullet Point 3

**Speaker Notes:**
Detaillierte Erklärungen, Anekdoten, zusätzlicher Kontext...

**Visual Suggestions:**
Screenshot, Diagramm, Animation...

**Timing:** 2-3 Minuten

---

[Weitere Slides im gleichen Format...]

</presentation>
```

Anschliessend eine HTML-Präsentation unter Verwendung von RevealJS.

## Demo-Vorbereitung

Die Präsentation soll auch folgende Demo-Materialien vorbereiten:

**Beispiel-Dokumente:**

- Informatik: Datenstrukturen & Algorithmen (PDF)
- BWL: Marketing Grundlagen (DOCX)
- Medizin: Anatomie Kapitel (Markdown)

**Demo-Szenarien:**

- Upload → Processing → Question Generation (5 Min)
- Review & Approval Workflow (3 Min)
- Export in verschiedene Formate (2 Min)

**Backup-Plan:**

- Pre-generated Questions falls Live-Demo fehlschlägt
- Screenshots aller wichtigen Schritte
- Video-Fallback für technische Probleme

Erstelle eine packende, praxisorientierte Präsentation die ExamCraft AI als innovative Lösung für moderne Prüfungserstellung positioniert!
