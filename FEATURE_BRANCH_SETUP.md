# Feature Branch Setup Guide: TF-187

## Für andere Entwickler: So arbeitest du mit diesem Feature Branch

### 📋 Repository-Struktur

**ExamCraft verwendet eine Monorepo-Struktur mit Git Submodules:**

```
examcraft/                          # Main Repository
├── packages/core/                  # Teil des Main Repos (KEIN Submodule)
├── packages/premium/               # Git Submodule (examcraft-premium)
├── packages/enterprise/            # Git Submodule (examcraft-enterprise)
└── docs-mintlify/                  # Git Submodule (examcraft-docs)
```

### 🚀 Initial Setup (Erstmaliges Klonen)

```bash
# 1. Main Repository klonen
git clone git@github.com:talent-factory/examcraft.git
cd examcraft

# 2. Feature Branch auschecken
git checkout feature/tf-187-resend-transactional-email

# 3. Submodules initialisieren und auschecken
git submodule update --init --recursive

# 4. Submodules auf Feature Branch wechseln
cd packages/premium
git checkout feature/tf-187-resend-transactional-email
git pull origin feature/tf-187-resend-transactional-email

cd ../enterprise
git checkout feature/tf-187-resend-transactional-email
git pull origin feature/tf-187-resend-transactional-email

cd ../..

# 5. Dependencies installieren
bun install

# 6. Docker Stack starten
./start-dev.sh --full
```

### 🔄 Updates holen (Wenn andere Entwickler gepusht haben)

```bash
# 1. Main Repository updaten
git pull origin feature/tf-187-resend-transactional-email

# 2. Submodules updaten
git submodule update --remote --merge

# ODER manuell für jedes Submodule:
cd packages/premium
git pull origin feature/tf-187-resend-transactional-email

cd ../enterprise
git pull origin feature/tf-187-resend-transactional-email

cd ../..
```

### ✏️ Änderungen committen und pushen

**WICHTIG:** Du musst in **jedem geänderten Repository** separat committen!

#### Beispiel: Änderungen in Premium Backend

```bash
# 1. In Premium Submodule committen
cd packages/premium
git add backend/api/v1/chat.py
git commit -m "🐛 fix(chat): Fix session loading"
git push origin feature/tf-187-resend-transactional-email

# 2. Zurück zum Main Repo
cd ../..

# 3. Submodule-Referenz im Main Repo updaten
git add packages/premium
git commit -m "📦 chore: Update Premium submodule reference"
git push origin feature/tf-187-resend-transactional-email
```

#### Beispiel: Änderungen in Core (Main Repo)

```bash
# Core ist Teil des Main Repos - normaler Git Workflow
git add packages/core/backend/main.py
git commit -m "✨ feat(backend): Add new feature"
git push origin feature/tf-187-resend-transactional-email
```

### 🔍 Status prüfen

```bash
# Main Repo Status
git status

# Submodule Status
git submodule status

# Detaillierter Submodule Status
git submodule foreach 'git status'

# Welcher Branch in jedem Submodule?
git submodule foreach 'git branch --show-current'
```

### ⚠️ Häufige Probleme

#### Problem: Submodule zeigt "detached HEAD"

```bash
cd packages/premium
git checkout feature/tf-187-resend-transactional-email
git pull origin feature/tf-187-resend-transactional-email
cd ../..
```

#### Problem: Submodule-Änderungen nicht sichtbar

```bash
# Submodules auf neuesten Stand bringen
git submodule update --remote --merge
```

#### Problem: Merge-Konflikte in Submodules

```bash
cd packages/premium
git status  # Prüfe Konflikte
# Löse Konflikte manuell
git add .
git commit -m "🔀 merge: Resolve conflicts"
git push origin feature/tf-187-resend-transactional-email
cd ../..
```

### 📝 Branch Protection Rules

**Alle `main` Branches sind geschützt:**
- ✅ examcraft (Main Repo)
- ✅ examcraft-premium
- ✅ examcraft-enterprise

**Du kannst NICHT direkt auf `main` pushen!**
- Alle Änderungen müssen via Pull Request erfolgen
- 1 Approval erforderlich

### 🎯 Zusammenfassung

**3 Repositories, 3 Feature Branches:**
1. **examcraft** → `feature/tf-187-resend-transactional-email`
2. **examcraft-premium** → `feature/tf-187-resend-transactional-email`
3. **examcraft-enterprise** → `feature/tf-187-resend-transactional-email`

**Bei Änderungen:**
- Committe in dem Repository, wo die Änderung ist
- Wenn Submodule geändert wurde: Update Submodule-Referenz im Main Repo
- Pushe beide Repositories

**Bei Updates holen:**
- Pull Main Repo
- Pull Submodules (oder `git submodule update --remote --merge`)
