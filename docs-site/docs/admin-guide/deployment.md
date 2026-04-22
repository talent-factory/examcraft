# Installation und Deployment

ExamCraft AI kann in zwei verschiedenen Konfigurationen deployed werden:
die **Core-Version** (für OpenSource) und die **Full-Version** (mit Premium- und Enterprise-Features).

## Deployment-Modi

### Core-Modus (OpenSource)

Der Core-Modus ist die minimale, OpenSource-freundliche Konfiguration:

- **Docker Compose**: `docker-compose.yml`
- **Services**: Backend, Frontend, PostgreSQL, Redis
- **Keine Vektorsuche**: Qdrant ist nicht enthalten
- **Features**: Begrenzt auf Free Tier (5 Dokumente, 20 Fragen/Monat)
- **Zielgruppe**: Community-Deployment, Testing

**Speicheranforderungen**: ca. 2–3 GB RAM, 5 GB Disk

### Full-Modus (Premium + Enterprise)

Der Full-Modus enthält alle Features:

- **Docker Compose**: `docker-compose.full.yml`
- **Services**: Backend, Frontend, PostgreSQL, Redis, Qdrant, RabbitMQ, Celery, Flower
- **Vektorsuche**: Qdrant für RAG und semantische Suche
- **Async Tasks**: RabbitMQ + Celery für Hintergrund-Jobs
- **Monitoring**: Flower zur Celery-Überwachung
- **Features**: Alle Tiers verfügbar (Free, Starter, Professional, Enterprise)
- **Zielgruppe**: Private Entwicklung, Production, SaaS

**Speicheranforderungen**: ca. 4–6 GB RAM, 10+ GB Disk

## Schnellstart

### Voraussetzungen

- Docker und Docker Compose (v2.0+)
- Python 3.13+ (für lokale Entwicklung)
- Bun oder Node.js 20+ (für Frontend-Entwicklung)

### Core-Modus starten

```bash
# Git-Repository klonen
git clone https://github.com/talent-factory/examcraft.git
cd examcraft

# Umgebungsvariablen vorbereiten
cp .env.example .env

# Services starten
./start-dev.sh --core
```

### Full-Modus starten

```bash
# Mit allen Premium- und Enterprise-Services
./start-dev.sh --full
```

### Auto-Modus (empfohlen)

Das Skript `start-dev.sh` erkennt automatisch, welche Services verfügbar sind:

```bash
./start-dev.sh
```

## Umgebungsvariablen

Wichtige Umgebungsvariablen in `.env`:

| Variable | Beschreibung | Beispiel |
|----------|-------------|---------|
| `CLAUDE_API_KEY` | API-Key für Claude | `sk-ant-...` |
| `DATABASE_URL` | PostgreSQL-Verbindung | `postgresql://user:pass@localhost/examcraft` |
| `REDIS_URL` | Redis-Verbindung | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT Secret | Zufälliger String (min. 32 Zeichen) |
| `DEPLOYMENT_MODE` | `core` oder `full` | `full` |

Weitere Variablen: Siehe `.env.example`.

## Production-Deployment

Für Production-Umgebungen wird ein Managed-Hosting-Service wie **Fly.io** oder **Heroku** empfohlen.

### Fly.io Deployment

```bash
# Fly.io CLI installieren
curl -L https://fly.io/install.sh | sh

# App erstellen und deployen
fly launch --copy-config
fly deploy
```

Weitere Informationen: [Fly.io Dokumentation](https://fly.io/docs/)

## Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| "Umgebungsvariablen werden nicht geladen" | `--env-file .env` nicht gesetzt | `docker compose --env-file .env up` verwenden |
| "Qdrant-Verbindungsfehler" (Core-Modus) | Qdrant wird im Core-Modus nicht gestartet | Im Full-Modus deployen oder RAG-Features deaktivieren |
| "PostgreSQL-Fehler: Authentifizierung fehlgeschlagen" | Falsche DATABASE_URL | `DATABASE_URL` in `.env` prüfen |
| "Port bereits in Benutzung" | Port 3000, 5432, 6379, etc. bereits vergeben | Ports in `docker-compose.yml` ändern oder andere Services stoppen |

## Nächste Schritte

- [:octicons-arrow-right-24: Benutzer verwalten](user-mgmt.md)
- [:octicons-arrow-right-24: Monitoring und Nutzung](monitoring.md)
- [:octicons-arrow-right-24: Subscription-Tiers](subscription.md)
