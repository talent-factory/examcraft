# ExamCraft AI - Mintlify Documentation

Diese Readme erklärt, wie Sie die Mintlify-Dokumentation für ExamCraft AI lokal entwickeln und deployen.

## 📚 Dokumentationsstruktur

```
examcraft/
├── mint.json                      # Mintlify Hauptkonfiguration
├── introduction.mdx               # Startseite
├── quickstart.mdx                 # Quick Start Guide
├── deployment.mdx                 # Deployment Guide
├── authentication.mdx             # Auth Guide
├── changelog.mdx                  # Changelog
├── essentials/                    # Kernkonzepte
│   ├── overview.mdx
│   ├── subscription-tiers.mdx
│   └── rbac.mdx
├── features/                      # Feature-Dokumentation
│   ├── document-upload.mdx
│   ├── question-generation.mdx
│   ├── rag-generation.mdx
│   ├── chatbot.mdx
│   ├── prompt-management.mdx
│   └── ...
├── guides/                        # How-To Guides
│   ├── first-exam.mdx
│   ├── rag-workflow.mdx
│   ├── chatbot-usage.mdx
│   ├── prompt-customization.mdx
│   └── best-practices.mdx
├── admin/                         # Admin-Guides
│   ├── user-management.mdx
│   ├── institution-setup.mdx
│   ├── prompt-management.mdx
│   └── subscription-management.mdx
└── api-reference/                 # API Dokumentation
    ├── introduction.mdx
    ├── authentication.mdx
    └── endpoints/
        ├── documents.mdx
        ├── questions.mdx
        ├── exams.mdx
        └── chat.mdx
```

## 🚀 Lokale Entwicklung

### Voraussetzungen

- Node.js 18+ installiert
- npm oder yarn

### Installation

1. **Mintlify CLI installieren:**

```bash
npm i -g mintlify
```

2. **Dokumentation im Development-Modus starten:**

```bash
cd /path/to/examcraft
mintlify dev
```

Die Dokumentation ist dann unter http://localhost:3000 verfügbar.

### Hot Reload

Mintlify unterstützt Hot Reload - Änderungen an `.mdx` Dateien werden sofort sichtbar.

## 📝 MDX Syntax

Mintlify verwendet MDX (Markdown + JSX). Sie können spezielle Komponenten verwenden:

### Cards

```mdx
<Card title="Title" icon="rocket" href="/link">
  Description
</Card>

<CardGroup cols={2}>
  <Card title="Card 1" icon="check">Content 1</Card>
  <Card title="Card 2" icon="star">Content 2</Card>
</CardGroup>
```

### Code Blocks

```mdx
<CodeGroup>

\`\`\`python Python
print("Hello World")
\`\`\`

\`\`\`javascript JavaScript
console.log("Hello World");
\`\`\`

</CodeGroup>
```

### Callouts

```mdx
<Info>
  Informative message
</Info>

<Warning>
  Warning message
</Warning>

<Check>
  Success message
</Check>

<Note>
  Note message
</Note>
```

### Accordions

```mdx
<AccordionGroup>
  <Accordion title="Question 1" icon="question">
    Answer 1
  </Accordion>
  <Accordion title="Question 2" icon="question">
    Answer 2
  </Accordion>
</AccordionGroup>
```

### Tabs

```mdx
<Tabs>
  <Tab title="Python">
    Python content
  </Tab>
  <Tab title="JavaScript">
    JavaScript content
  </Tab>
</Tabs>
```

### Steps

```mdx
<Steps>
  <Step title="Step 1">
    Description 1
  </Step>
  <Step title="Step 2">
    Description 2
  </Step>
</Steps>
```

## 🎨 Branding & Styling

### Farben anpassen

In `mint.json`:

```json
{
  "colors": {
    "primary": "#0D9488",
    "light": "#14B8A6",
    "dark": "#0D9488",
    "anchors": {
      "from": "#0D9488",
      "to": "#14B8A6"
    }
  }
}
```

### Logo hinzufügen

Legen Sie Logo-Dateien unter `/logo/` ab:
- `light.svg` - Logo für Light Mode
- `dark.svg` - Logo für Dark Mode

Update `mint.json`:

```json
{
  "logo": {
    "dark": "/logo/dark.svg",
    "light": "/logo/light.svg"
  },
  "favicon": "/favicon.svg"
}
```

## 📦 Deployment

### Mintlify Cloud (Empfohlen)

1. **Repository mit GitHub verbinden:**

   Gehen Sie zu [mintlify.com/dashboard](https://mintlify.com/dashboard) und verbinden Sie Ihr GitHub Repository.

2. **Mintlify konfigurieren:**

   Mintlify erkennt automatisch die `mint.json` Konfiguration.

3. **Auto-Deploy:**

   Bei jedem Push zu `main` wird die Dokumentation automatisch neu deployed.

### Custom Domain

In den Mintlify Dashboard Settings können Sie eine Custom Domain konfigurieren:

```
docs.examcraft.ai
```

### Build Commands

Mintlify führt automatisch folgende Schritte aus:

```bash
mintlify install  # Dependencies installieren
mintlify build    # Dokumentation bauen
mintlify deploy   # Deployment
```

## 🔍 SEO & Analytics

### Google Analytics

In `mint.json`:

```json
{
  "analytics": {
    "ga4": {
      "measurementId": "G-XXXXXXXXXX"
    }
  }
}
```

### Sitemap

Mintlify generiert automatisch eine Sitemap unter `/sitemap.xml`.

### Meta Tags

Für jede Seite in der Frontmatter:

```mdx
---
title: 'Page Title'
description: 'SEO-optimized description'
---
```

## 📖 Best Practices

### Struktur

1. **Logische Hierarchie:** Gruppieren Sie verwandte Seiten zusammen
2. **Kurze Titel:** Verwenden Sie prägnante Titel für Navigation
3. **Descriptions:** Jede Seite sollte eine description haben

### Inhalte

1. **User-First:** Schreiben Sie aus Sicht des Benutzers
2. **Code-Beispiele:** Nutzen Sie `<CodeGroup>` für Multi-Language
3. **Visuals:** Verwenden Sie Cards, Icons, und Callouts für bessere Lesbarkeit

### Navigation

1. **Max. 2-3 Ebenen:** Halten Sie die Navigation flach
2. **Logische Gruppierung:** Verwenden Sie `groups` in `mint.json`
3. **Cross-Links:** Verlinken Sie verwandte Seiten

## 🐛 Troubleshooting

### Mintlify CLI startet nicht

**Problem:** `mintlify dev` schlägt fehl

**Lösung:**
```bash
# Reinstall Mintlify
npm uninstall -g mintlify
npm i -g mintlify

# Clear cache
rm -rf node_modules .mintlify
mintlify dev
```

### Komponenten werden nicht gerendert

**Problem:** MDX-Komponenten zeigen nur Text

**Lösung:**
- Überprüfen Sie Syntax (selbstschließende Tags: `<Card ... />`)
- Prüfen Sie auf Leerzeichen in Attributen
- Validieren Sie `mint.json` mit [jsonlint.com](https://jsonlint.com)

### Build schlägt fehl

**Problem:** Deployment-Build-Fehler

**Lösung:**
```bash
# Lokal testen
mintlify build

# Logs prüfen
cat .mintlify/build.log
```

## 📚 Weitere Ressourcen

- **Mintlify Docs:** [mintlify.com/docs](https://mintlify.com/docs)
- **MDX Syntax:** [mdxjs.com](https://mdxjs.com)
- **Icon Library:** [fontawesome.com/icons](https://fontawesome.com/icons)

## 🤝 Contributing

Siehe [CONTRIBUTING.md](../CONTRIBUTING.md) für Contribution Guidelines.

## ✅ Completed Documentation

**Core Pages:**
- ✅ introduction.mdx - Landing Page mit Feature-Übersicht
- ✅ quickstart.mdx - Installation und erste Schritte
- ✅ changelog.mdx - Version History
- ✅ essentials/overview.mdx - Kernkonzepte und UI-Übersicht
- ✅ essentials/subscription-tiers.mdx - Detaillierte Tier-Vergleiche
- ✅ guides/first-exam.mdx - Schritt-für-Schritt Guide für erste Prüfung
- ✅ api-reference/introduction.mdx - API Dokumentation

## 🚧 TODO: Noch zu erstellen

**Fehlende Seiten:**
- [ ] deployment.mdx - Deployment Guide (basierend auf DEPLOYMENT.md)
- [ ] authentication.mdx - Auth Guide
- [ ] essentials/rbac.mdx - RBAC System
- [ ] features/document-upload.mdx
- [ ] features/question-generation.mdx
- [ ] features/question-review.mdx
- [ ] features/exam-export.mdx
- [ ] features/rag-generation.mdx
- [ ] features/chatbot.mdx
- [ ] features/prompt-management.mdx
- [ ] features/semantic-search.mdx
- [ ] features/sso.mdx
- [ ] features/custom-branding.mdx
- [ ] features/api-access.mdx
- [ ] features/analytics.mdx
- [ ] guides/rag-workflow.mdx
- [ ] guides/chatbot-usage.mdx
- [ ] guides/prompt-customization.mdx
- [ ] guides/best-practices.mdx
- [ ] admin/user-management.mdx
- [ ] admin/institution-setup.mdx
- [ ] admin/prompt-management.mdx
- [ ] admin/subscription-management.mdx
- [ ] api-reference/authentication.mdx
- [ ] api-reference/endpoints/documents.mdx
- [ ] api-reference/endpoints/questions.mdx
- [ ] api-reference/endpoints/exams.mdx
- [ ] api-reference/endpoints/chat.mdx

---

**Letzte Aktualisierung:** 08.11.2025
