# 📄 Beispiel-Prompts für ExamCraft AI

Dieses Verzeichnis enthält Beispiel-Prompt-Vorlagen im YAML-Frontmatter-Format, die mit dem Drag & Drop Upload-Feature hochgeladen werden können.

## 📋 Verfügbare Beispiele

### 1. `question_generator_academic.md`
**Kategorie**: System Prompt
**Use Case**: Question Generation
**Schwierigkeit**: Medium

Generiert qualitativ hochwertige Prüfungsfragen für BSc Informatik aus akademischen Materialien mit automatischer Musterlösungsgenerierung.

**Variablen**:
- `{{target_audience}}` - Zielgruppe (z.B. "BSc Informatik, 3.-4. Semester")
- `{{topic}}` - Themenbereich (z.B. "Datenstrukturen und Algorithmen")
- `{{difficulty}}` - Schwierigkeitsgrad (easy, medium, hard)
- `{{num_questions}}` - Anzahl der zu generierenden Fragen
- `{{points_range}}` - Punktebereich pro Frage
- `{{source_material}}` - Bereitgestelltes Kursmaterial

**Basiert auf**: `.claude/commands/workshop/create-questions.md`

---

### 2. `multiple_choice_generator.md`
**Kategorie**: Template
**Use Case**: Question Generation
**Schwierigkeit**: Easy

Generiert Multiple-Choice-Fragen aus Textmaterial mit automatischer Distraktoren-Erstellung.

**Variablen**:
- `{{num_questions}}` - Anzahl der MC-Fragen
- `{{topic}}` - Thema der Fragen
- `{{difficulty}}` - Schwierigkeitsgrad (easy, medium, hard)
- `{{target_audience}}` - Zielgruppe
- `{{source_material}}` - Quellmaterial für Fragen
- `{{question_number}}` - Fragennummer (automatisch)
- `{{points}}` - Punkte pro Frage

**Ideal für**: Schnelle Quiz-Erstellung, Selbsttests, Lernkontrollen

---

### 3. `exam_assistant_system.md`
**Kategorie**: System Prompt
**Use Case**: Exam Creation
**Schwierigkeit**: Medium

System-Prompt für einen KI-Assistenten zur Prüfungserstellung mit Fokus auf akademische Integrität und Qualität.

**Keine Variablen** - Dieser Prompt definiert das Verhalten des Assistenten.

**Verwendung**: Als Basis-System-Prompt für ExamCraft AI

---

## 🚀 Verwendung

### Upload via Drag & Drop

1. Navigiere zur **Prompt-Bibliothek** in ExamCraft AI
2. Wechsle zum Tab **"Datei-Upload"**
3. Ziehe die `.md` Dateien in die Upload-Zone
4. Warte auf die Upload-Bestätigung
5. Prompts sind nach Review verfügbar

### Upload via API

```bash
# Single Upload
curl -X POST http://localhost:8000/api/v1/prompts/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@question_generator_academic.md"

# Bulk Upload
curl -X POST http://localhost:8000/api/v1/prompts/upload/bulk \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@question_generator_academic.md" \
  -F "files=@multiple_choice_generator.md" \
  -F "files=@exam_assistant_system.md"
```

### Download als Template

```bash
# Download eines Prompts als .md Datei
curl -X GET http://localhost:8000/api/v1/prompts/download/{prompt_id} \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o my_prompt.md
```

---

## 📝 YAML-Frontmatter Format

Alle Prompt-Dateien folgen diesem Format:

```markdown
---
name: unique_prompt_name
category: system_prompt|user_prompt|few_shot_example|template
description: Kurze Beschreibung des Prompts
use_case: question_generation|exam_creation|grading|...
tags: [tag1, tag2, tag3]
language: de|en
difficulty_level: easy|medium|hard
version_comment: Optionaler Versionskommentar
---

# Prompt-Titel

Hier beginnt der eigentliche Prompt-Content...

Variablen werden mit {{variable_name}} markiert.
```

### Pflichtfelder

- `name` - Eindeutiger Name (nur alphanumerisch + Unterstriche)
- `category` - Eine von: `system_prompt`, `user_prompt`, `few_shot_example`, `template`

### Optionale Felder

- `description` - Beschreibung (max 500 Zeichen)
- `use_case` - Anwendungsfall (max 100 Zeichen)
- `tags` - Liste von Tags (max 10, je max 30 Zeichen)
- `language` - Sprache (2-Buchstaben-Code, default: `de`)
- `difficulty_level` - Schwierigkeit (`easy`, `medium`, `hard`, default: `medium`)
- `version_comment` - Versionskommentar (max 200 Zeichen)

---

## ✅ Validierung

Beim Upload werden folgende Prüfungen durchgeführt:

- ✅ Dateiformat (.md oder .txt)
- ✅ UTF-8 Kodierung
- ✅ YAML-Frontmatter vorhanden und korrekt
- ✅ Pflichtfelder ausgefüllt
- ✅ Kategorie gültig
- ✅ Name eindeutig (keine Duplikate)
- ✅ Tags valide (Länge, Zeichen)
- ✅ Prompt-Content nicht leer

---

## 🎯 Best Practices

### Naming Convention
- Verwende beschreibende Namen: `question_generator_academic` statt `qg1`
- Nur Kleinbuchstaben, Zahlen und Unterstriche
- Keine Leerzeichen oder Sonderzeichen

### Kategorien
- **system_prompt**: Definiert Verhalten des AI-Assistenten
- **user_prompt**: Direkte Anweisungen für spezifische Aufgaben
- **few_shot_example**: Beispiele für Few-Shot Learning
- **template**: Wiederverwendbare Vorlagen mit Variablen

### Tags
- Verwende konsistente Tags über alle Prompts
- Beispiele: `exam`, `quiz`, `grading`, `feedback`, `academic`
- Max 10 Tags pro Prompt

### Variablen
- Verwende `{{variable_name}}` für Platzhalter
- Dokumentiere alle Variablen in der Beschreibung
- Verwende sprechende Variablennamen

---

## 📚 Weitere Ressourcen

- **API Dokumentation**: http://localhost:8000/docs
- **Prompt Engineering Guide**: `/docs/prompt-engineering.md`
- **ExamCraft AI Dokumentation**: `/README.md`

---

**Viel Erfolg beim Erstellen eigener Prompt-Vorlagen! 🚀**
