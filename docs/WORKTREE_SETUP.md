# Git Worktrees Setup für ExamCraft AI

Dieses Dokument beschreibt, wie man Git Worktrees für parallele Entwicklung mit ExamCraft AI nutzt.

## Überblick

Git Worktrees ermöglichen es, mehrere Branches gleichzeitig in separaten Verzeichnissen zu bearbeiten, ohne zwischen Branches wechseln zu müssen. Dies ist besonders nützlich für:

- Parallele Feature-Entwicklung
- Schnelle Context-Switches zwischen Features
- Gleichzeitiges Testen mehrerer Branches

## Setup für Worktrees

### 1. Neuen Worktree erstellen

```bash
# Hauptverzeichnis
cd /Users/daniel/GitRepository/ExamCraft-develop

# Neuen Worktree für Feature-Branch erstellen
git worktree add ../ExamCraft-feature-gui feature/gui-modernization

# In den neuen Worktree wechseln
cd ../ExamCraft-feature-gui
```

### 2. Docker-Compose mit dynamischen Ports

Jeder Worktree benötigt eigene Ports für Frontend und Backend, um Konflikte zu vermeiden.

**Konfiguration in `.env.local`:**

```bash
# Main Worktree (ExamCraft-develop)
FRONTEND_PORT=3000
BACKEND_PORT=8000

# Feature Worktree (ExamCraft-feature-gui)
FRONTEND_PORT=3001
BACKEND_PORT=8001
```

### 3. Docker-Compose starten

```bash
# Im Feature-Worktree
cd ../ExamCraft-feature-gui

# .env.local erstellen
cat > .env.local << EOF
FRONTEND_PORT=3001
BACKEND_PORT=8001
EOF

# Docker-Container starten
docker-compose up -d

# Logs überprüfen
docker-compose logs -f frontend backend
```

### 4. Zugriff auf die Anwendung

- **Frontend**: http://localhost:3001 (Feature-Worktree)
- **Backend API**: http://localhost:8001 (Feature-Worktree)
- **Frontend**: http://localhost:3000 (Main-Worktree)
- **Backend API**: http://localhost:8000 (Main-Worktree)

## Datenbank-Sharing

**Wichtig**: PostgreSQL, Redis und Qdrant sind **shared** across all worktrees:

- **PostgreSQL**: localhost:5432 (shared)
- **Redis**: localhost:6380 (shared)
- **Qdrant**: localhost:6333 (shared)

Dies bedeutet:
- ✅ Alle Worktrees nutzen die gleiche Datenbank
- ✅ Keine Datenduplizierung
- ✅ Einfacheres Setup
- ⚠️ Datenbankänderungen sind in allen Worktrees sichtbar

## Cleanup

### Worktree entfernen

```bash
# Aus dem Worktree herausgehen
cd ../ExamCraft-develop

# Docker-Container stoppen
cd ../ExamCraft-feature-gui
docker-compose down

# Worktree entfernen
cd ../ExamCraft-develop
git worktree remove ../ExamCraft-feature-gui
```

## Tipps & Best Practices

### 1. Separate Terminal-Fenster

Nutze separate Terminal-Fenster für jeden Worktree:

```bash
# Terminal 1: Main Worktree
cd /Users/daniel/GitRepository/ExamCraft-develop
docker-compose up -d

# Terminal 2: Feature Worktree
cd /Users/daniel/GitRepository/ExamCraft-feature-gui
FRONTEND_PORT=3001 BACKEND_PORT=8001 docker-compose up -d
```

### 2. Port-Verwaltung

Wenn du mehrere Worktrees hast, nutze ein Schema:

```
Main (develop):           3000, 8000
Feature 1 (gui):          3001, 8001
Feature 2 (auth):         3002, 8002
Feature 3 (rag):          3003, 8003
```

### 3. .env.local pro Worktree

Erstelle `.env.local` in jedem Worktree mit den richtigen Ports:

```bash
# Feature-Worktree
echo "FRONTEND_PORT=3001" > .env.local
echo "BACKEND_PORT=8001" >> .env.local
```

### 4. Docker-Compose Befehle

```bash
# Status überprüfen
docker-compose ps

# Logs anschauen
docker-compose logs -f frontend

# Container neu starten
docker-compose restart frontend

# Alles stoppen
docker-compose down
```

## Troubleshooting

### Port bereits in Verwendung

```bash
# Überprüfe, welcher Prozess den Port nutzt
lsof -i :3000

# Oder nutze einen anderen Port in .env.local
FRONTEND_PORT=3005
```

### Datenbank-Verbindungsfehler

```bash
# Stelle sicher, dass PostgreSQL läuft
docker-compose ps postgres

# Logs überprüfen
docker-compose logs postgres
```

### Container-Fehler

```bash
# Container neu bauen
docker-compose build --no-cache

# Neu starten
docker-compose up -d
```

## Weitere Ressourcen

- [Git Worktrees Dokumentation](https://git-scm.com/docs/git-worktree)
- [Docker Compose Dokumentation](https://docs.docker.com/compose/)
- [ExamCraft AI README](../README.md)

