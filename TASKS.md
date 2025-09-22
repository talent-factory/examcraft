# ExamCraft AI - Aufgabenliste 📋

## 🚀 Aktuelle Sprint-Aufgaben

### 🔥 Höchste Priorität - Document-Upload & RAG-Integration

#### TASK-001: Document Upload System

- **Status**: ✅ Abgeschlossen
- **Assignee**: Daniel Senften
- **Deadline**: 22.09.2025
- **Beschreibung**: Implementierung eines File-Upload-Systems für PDF, DOC, DOCX, TXT Dateien

**Akzeptanzkriterien**:

- [x] Drag & Drop Interface
- [x] Multi-File Upload Support
- [x] Progress-Anzeige
- [x] File-Validation
- [x] Error Handling

#### TASK-002: Docling Integration

- **Status**: ✅ Abgeschlossen
- **Assignee**: Daniel Senften
- **Deadline**: 22.09.2025
- **Beschreibung**: Integration von IBM Docling für strukturierte Dokumentenverarbeitung

**Akzeptanzkriterien**:

- [x] Docling Service implementiert
- [x] PDF/DOC/DOCX Processing
- [x] Metadata Extraktion
- [x] Text Chunking Strategy
- [x] Error Recovery

#### TASK-002.5: Test Implementation für Document System

- **Status**: ✅ Abgeschlossen
- **Assignee**: Daniel Senften
- **Deadline**: 22.09.2025
- **Beschreibung**: Umfassende Tests für Document Upload & Docling Integration

**Akzeptanzkriterien**:

- [x] Unit Tests für DocumentService
- [x] Unit Tests für DoclingService  
- [x] API Integration Tests
- [x] File Upload Tests mit Mock-Dateien
- [x] Error Handling Tests
- [x] Test Coverage > 69% (Ziel erreicht)

#### TASK-003: Vector Database Setup

- **Status**: ✅ Abgeschlossen
- **Assignee**: Daniel Senften
- **Deadline**: 22.09.2025
- **Beschreibung**: ChromaDB Integration für lokale Vektor-Suche

**Akzeptanzkriterien**:

- [x] ChromaDB lokale Installation
- [x] Embedding Pipeline (sentence-transformers)
- [x] Collection Management
- [x] Similarity Search API
- [x] Persistierung

#### TASK-004: RAG-basierte Fragenerstellung

- **Status**: ✅ Abgeschlossen
- **Assignee**: Daniel Senften
- **Deadline**: 22.09.2025
- **Beschreibung**: RAG Service für dokumentenbasierte Fragenerstellung

**Akzeptanzkriterien**:

- [x] Context Retrieval aus Vector DB
- [x] RAG-Prompts für Claude API
- [x] Quality Assurance
- [x] Source Attribution
- [x] Fallback Strategies

#### TASK-005: Document Management UI

- **Status**: ✅ Abgeschlossen
- **Assignee**: Daniel Senften
- **Deadline**: 22.09.2025
- **Beschreibung**: Frontend für Dokumentenverwaltung und RAG-Exam-Erstellung

**Akzeptanzkriterien**:

- [x] Document Upload Component
- [x] Document Library View
- [x] Processing Status Display
- [x] RAG Exam Creator Interface
- [x] Document Preview

### 🟡 Hohe Priorität - Core Features

#### TASK-006: Claude API Vollintegration

- **Status**: 🟡 In Arbeit
- **Assignee**: Daniel Senften
- **Deadline**: 22.09.2025
- **Beschreibung**: Vollständige Claude API Integration mit Error Handling

**Akzeptanzkriterien**:

- [ ] API Key Konfiguration
- [ ] Rate Limiting
- [ ] Retry Logic
- [ ] Fallback auf Demo-Modus
- [ ] Cost Tracking

#### TASK-007: User Authentication System

- **Status**: 🔴 Nicht begonnen
- **Assignee**: -
- **Deadline**: -
- **Beschreibung**: JWT-basierte Benutzerauthentifizierung

**Akzeptanzkriterien**:

- [ ] User Registration/Login
- [ ] JWT Token Management
- [ ] Password Reset
- [ ] Role-based Access Control
- [ ] Session Management

#### TASK-008: PDF Export Funktionalität

- **Status**: 🔴 Nicht begonnen
- **Assignee**: -
- **Deadline**: -
- **Beschreibung**: Export von generierten Prüfungen als PDF

**Akzeptanzkriterien**:

- [ ] PDF Template Design
- [ ] Question Formatting
- [ ] Answer Key Generation
- [ ] Branding/Logo Integration
- [ ] Download Functionality

### 🟢 Mittlere Priorität - Erweiterte Features

#### TASK-009: Erweiterte Fragetypen

- **Status**: 🔴 Nicht begonnen
- **Assignee**: -
- **Deadline**: -
- **Beschreibung**: True/False, Lückentext, Drag & Drop Fragen

**Akzeptanzkriterien**:

- [ ] True/False Questions
- [ ] Fill-in-the-blank
- [ ] Drag & Drop Matching
- [ ] Code Questions mit Syntax Highlighting
- [ ] Image-based Questions

#### TASK-010: Prüfungsverwaltung (CRUD)

- **Status**: 🔴 Nicht begonnen
- **Assignee**: -
- **Deadline**: -
- **Beschreibung**: Vollständige CRUD-Operationen für Prüfungen

**Akzeptanzkriterien**:

- [ ] Prüfung speichern/laden
- [ ] Prüfung bearbeiten
- [ ] Prüfung duplizieren
- [ ] Prüfung löschen
- [ ] Versionierung

#### TASK-011: Moodle Integration

- **Status**: 🔴 Nicht begonnen
- **Assignee**: -
- **Deadline**: -
- **Beschreibung**: Export-Funktionalität für Moodle XML Format

**Akzeptanzkriterien**:

- [ ] Moodle XML Export
- [ ] Question Bank Integration
- [ ] Category Management
- [ ] Import/Export Testing
- [ ] Documentation

## 📊 Sprint Übersicht

### Sprint 1: Document-Upload Foundation (2 Wochen)

- TASK-001: Document Upload System
- TASK-002: Docling Integration (Basis)
- TASK-006: Claude API Vollintegration

### Sprint 2: RAG Implementation (2 Wochen)

- TASK-003: Vector Database Setup
- TASK-004: RAG-basierte Fragenerstellung
- TASK-002: Docling Integration (Vervollständigung)

### Sprint 3: UI/UX & Management (2 Wochen)

- TASK-005: Document Management UI
- TASK-007: User Authentication System
- TASK-008: PDF Export Funktionalität

### Sprint 4: Advanced Features (2 Wochen)

- TASK-009: Erweiterte Fragetypen
- TASK-010: Prüfungsverwaltung (CRUD)
- TASK-011: Moodle Integration

## 🏷️ Labels & Status

### Status Labels

- 🔴 **Nicht begonnen**: Aufgabe noch nicht gestartet
- 🟡 **In Arbeit**: Aufgabe wird bearbeitet
- 🟢 **Review**: Aufgabe fertig, wartet auf Review
- ✅ **Abgeschlossen**: Aufgabe vollständig erledigt
- ❌ **Blockiert**: Aufgabe blockiert durch Dependencies

### Priorität Labels

- 🔥 **Kritisch**: Muss sofort bearbeitet werden
- 🚀 **Hoch**: Hohe Priorität für aktuellen Sprint
- 🟡 **Mittel**: Normale Priorität
- 🟢 **Niedrig**: Kann später bearbeitet werden
- 💡 **Nice-to-have**: Optional für zukünftige Releases

### Typ Labels

- 🆕 **Feature**: Neue Funktionalität
- 🐛 **Bug**: Fehlerbehebung
- 📚 **Docs**: Dokumentation
- 🔧 **Tech**: Technische Verbesserung
- 🎨 **UI/UX**: Design/Benutzerfreundlichkeit

## 📝 Notizen

### Technische Entscheidungen

- **Docling vs. Alternative**: Docling gewählt für strukturierte PDF-Verarbeitung
- **ChromaDB vs. FAISS**: ChromaDB für einfache lokale Persistierung
- **sentence-transformers**: all-MiniLM-L6-v2 für deutsche/englische Texte

### Risiken & Mitigation

- **Docling Kompatibilität**: Fallback auf pypdf/python-docx
- **Vector DB Performance**: Chunking-Strategien optimieren
- **Claude API Costs**: Rate Limiting und Caching implementieren

---

**Letzte Aktualisierung**: 2025-09-22  
**Nächstes Review**: TBD

Diese Aufgabenliste dient als Alternative zu Linear und wird regelmäßig aktualisiert.
