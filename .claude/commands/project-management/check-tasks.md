# Check Linear Tasks & Recommendations

Hole alle aktuellen Linear Issues für ExamCraft AI ab und gib eine intelligente Empfehlung für die nächste zu bearbeitende Aufgabe basierend auf Priorität, Dependencies und aktuellem Projektstand.

## Aufgabe

Du sollst:

1. **Linear Issues abrufen**:
   - Verwende `mcp__linear-server__list_issues` für Projekt ID: `6eebcff0-9f2f-4bff-a4ea-2a68bb367577`
   - Hole alle Issues unabhängig vom Status
   - Gruppiere nach Status (Todo, In Progress, Done, Backlog)

2. **Issues kategorisieren und analysieren**:
   - **Urgent** (Priority 1): Workshop-kritische Aufgaben
   - **High** (Priority 2): Wichtige Core-Features
   - **Medium** (Priority 3): Standard-Features
   - **Low** (Priority 4): Nice-to-have Features

3. **Next-Task Recommendation Algorithm**:
   - **Zuerst**: Urgent + Todo Issues ohne Dependencies
   - **Dann**: High Priority Issues die bereit sind
   - **Berücksichtige**: Bereits abgeschlossene Aufgaben
   - **Ignoriere**: Backlog Items (außer sie sind urgent)

4. **Smart Filtering**:
   - Zeige nur Issues die **aktuell bearbeitbar** sind
   - Prüfe Dependencies (Parent/Child Relationships)
   - Berücksichtige bereits abgeschlossene Basis-Features
   - Fokus auf **realisierbare** nächste Schritte

5. **Empfehlungs-Output**:
   - **Top Recommendation**: Die eine beste nächste Aufgabe
   - **Alternative Options**: 2-3 weitere gute Optionen
   - **Reasoning**: Warum diese Aufgabe empfohlen wird
   - **Prerequisites**: Was muss vor dieser Aufgabe erledigt sein

## MCP Commands zu verwenden

```bash
# Alle Issues für ExamCraft AI holen
mcp__linear-server__list_issues project="6eebcff0-9f2f-4bff-a4ea-2a68bb367577"

# Für Details zu spezifischen Issues:
mcp__linear-server__get_issue id="<issue-id>"
```

## Expected Output Format

```
📋 ExamCraft AI - Linear Tasks Overview

📊 STATUS SUMMARY:
┌─────────────┬───────┬────────────────────────────────────────┐
│ Status      │ Count │ Items                                  │
├─────────────┼───────┼────────────────────────────────────────┤
│ ✅ Done     │   6   │ Setup, Documents, API, Frontend, etc. │
│ 🔄 Todo     │   3   │ Review UI, Demo Materials, Export     │
│ ⚡ Urgent   │   1   │ Workshop Demo Preparation              │
│ 📚 Backlog  │   4   │ Testing, Performance, Auth, etc.      │
└─────────────┴───────┴────────────────────────────────────────┘

🎯 NEXT TASK RECOMMENDATION:

**PRIMARY RECOMMENDATION: TF-58 - Workshop Demo & Presentation Materials**
🔥 Priority: Urgent | Status: Todo | Assignee: Available

**Why this task?**
• Highest business priority (Workshop deadline approaching)
• All technical prerequisites are complete (API, Frontend, Setup done)
• Directly blocks demo success
• Can be completed independently

**What's needed:**
• Create presentation slides
• Prepare demo scenarios
• Test live demo flow
• Prepare Q&A materials

**Estimated effort:** 1-2 days

📋 ALTERNATIVE OPTIONS:

2. **TF-60 - Question Review & Approval Interface** (Urgent, UI-focused)
3. **TF-56 - Exam Composition & Export** (Medium priority, extends functionality)

🧱 BLOCKED/WAITING:
• TF-61 (Performance): Wait for core features completion
• TF-57 (Authentication): Lower priority for demo

⚡ QUICK WINS AVAILABLE:
• Update documentation
• Create more demo content
• Prepare backup scenarios
```

## Recommendation Logic

**Priority Matrix:**
1. **Urgent + No Dependencies** = Immediate Action
2. **High + Prerequisites Met** = Next Sprint
3. **Medium + Easy Implementation** = Quick Wins
4. **Everything else** = Future Planning

**Current Project State berücksichtigen:**
- Core API ✅ (TF-52)
- Frontend ✅ (TF-54)
- Setup ✅ (TF-50)
- Document Processing ✅ (TF-51)
- Vector Search ✅ (TF-55)

**Dependencies tracking:**
- Prüfe Parent/Child Issue Relationships
- Identifiziere Blocker
- Empfehle nur **ready-to-start** Tasks

## Smart Insights

Füge contextuelle Insights hinzu:
- "Based on recent completions, focus on demo preparation"
- "Core infrastructure is complete, time for user-facing features"
- "Workshop deadline approaching - prioritize demo materials"

Zeige auch **was NICHT empfohlen wird** und warum:
- "Authentication (TF-57) not recommended: not needed for demo"
- "Performance optimization (TF-61) can wait: core features work"