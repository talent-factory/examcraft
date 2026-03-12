# ExamCraft AI - Fly.io Deployment (Intern)

> **Stand:** 11. Februar 2026
> **Region:** Frankfurt (fra)
> **Organisation:** personal

## Deployment-Architektur

```mermaid
flowchart TB
    subgraph Internet["Internet"]
        User[("Benutzer")]
    end

    subgraph FlyEdge["Fly.io Edge Network"]
        direction TB
        LB_Web["Load Balancer<br/>examcraft-web.fly.dev<br/>66.241.125.175"]
        LB_API["Load Balancer<br/>examcraft-api.fly.dev<br/>66.241.125.207"]
    end

    subgraph FlyFRA["Fly.io Frankfurt (fra)"]
        subgraph Public["Public Services"]
            Web["Frontend (Nginx)<br/>examcraft-web<br/>Port 80<br/>256MB RAM"]
            API["Backend (FastAPI)<br/>examcraft-api<br/>Port 8000<br/>512MB RAM"]
        end

        subgraph Private["Private Network (.internal)"]
            DB[("PostgreSQL 17.2<br/>examcraft-db.internal<br/>fdaa:45:8931:0:1::4<br/>Managed Postgres")]
            Redis[("Redis (Upstash)<br/>examcraft-redis<br/>Pay-as-you-go")]
            Qdrant[("Qdrant Vector DB<br/>examcraft-qdrant.internal:6333<br/>fdaa:45:8931:0:1::6<br/>1GB RAM + Volume")]
            RabbitMQ[("RabbitMQ 4<br/>examcraft-rabbitmq.internal:5672<br/>Management Alpine")]
            Celery["Celery Worker<br/>examcraft-celery.internal<br/>Background Tasks"]
        end
    end

    subgraph External["Externe APIs"]
        Claude["Claude API<br/>(Anthropic)"]
        Google["Google OAuth"]
        Microsoft["Microsoft OAuth"]
    end

    User -->|HTTPS| LB_Web
    User -->|HTTPS| LB_API
    LB_Web --> Web
    LB_API --> API

    Web -->|"API Calls<br/>REACT_APP_API_URL"| LB_API

    API -->|"SQL<br/>DATABASE_URL"| DB
    API -->|"Sessions/Cache<br/>REDIS_URL"| Redis
    API -->|"Vector Search<br/>QDRANT_URL"| Qdrant
    API -->|"Task Queue<br/>CELERY_BROKER_URL"| RabbitMQ
    API -->|"LLM Requests"| Claude
    API -->|"OAuth"| Google
    API -->|"OAuth"| Microsoft

    Celery -->|"Consume Tasks"| RabbitMQ
    Celery -->|"Database"| DB
    Celery -->|"Vector Storage"| Qdrant

    style Web fill:#4ade80,stroke:#166534
    style API fill:#60a5fa,stroke:#1d4ed8
    style DB fill:#fbbf24,stroke:#b45309
    style Redis fill:#f87171,stroke:#b91c1c
    style Qdrant fill:#a78bfa,stroke:#6d28d9
    style RabbitMQ fill:#fb923c,stroke:#c2410c
    style Celery fill:#2dd4bf,stroke:#0d9488
```

## Services Übersicht

| Service | App Name | Hostname | Status | Letzte Deployment |
|---------|----------|----------|--------|-------------------|
| Frontend | examcraft-web | examcraft-web.fly.dev | deployed | vor 4h |
| Backend | examcraft-api | examcraft-api.fly.dev | deployed | vor 5h |
| PostgreSQL | examcraft-db | examcraft-db.internal | deployed | Managed |
| Redis | examcraft-redis | Upstash | deployed | Pay-as-you-go |
| Qdrant | examcraft-qdrant | examcraft-qdrant.fly.dev | deployed | vor 10h |
| RabbitMQ | examcraft-rabbitmq | examcraft-rabbitmq.internal | deployed | 10.02.2026 |
| Celery | examcraft-celery | examcraft-celery.internal | deployed | vor 10h |

## IP-Adressen

### Öffentliche IPs (Public Ingress)

| Service | IPv4 (Shared) | IPv6 (Dedicated) |
|---------|---------------|------------------|
| examcraft-api | 66.241.125.207 | 2a09:8280:1::d2:6c0:0 |
| examcraft-web | 66.241.125.175 | 2a09:8280:1::d2:6c4:0 |
| examcraft-qdrant | 66.241.125.191 | 2a09:8280:1::d2:6c5:0 |

### Private IPs (Internal Network)

| Service | IPv6 (Private) | DNS |
|---------|----------------|-----|
| examcraft-db | fdaa:45:8931:0:1::4 | examcraft-db.internal |
| examcraft-qdrant | fdaa:45:8931:0:1::6 | examcraft-qdrant.internal |
| examcraft-rabbitmq | - | examcraft-rabbitmq.internal |
| examcraft-celery | - | examcraft-celery.internal |

## Machine Details

### examcraft-api (Backend)

```
Image:    examcraft-api:deployment-01KH6N7FV0CPACH88D00VQH732
Region:   fra (Frankfurt)
Memory:   512MB
CPU:      shared, 1 vCPU
Port:     8000
```

| Machine ID | Version | State | Health Check |
|------------|---------|-------|--------------|
| e82227efd35d58 | 22 | started | 1 critical |
| 68395d1bd02738 | 22 | stopped | 1 warning |

**Konfiguration (fly.toml):**
- `DEPLOYMENT_MODE=full`
- `auto_stop_machines=stop`
- `auto_start_machines=true`
- `min_machines_running=1`
- Health Check: `/api/v1/health` (15s interval)

### examcraft-web (Frontend)

```
Image:    examcraft-web:deployment-01KH6QX84TX0GYEFTPHJ7KCKWV
Region:   fra (Frankfurt)
Memory:   256MB
CPU:      shared, 1 vCPU
Port:     80 (Nginx)
```

| Machine ID | Version | State | Health Check |
|------------|---------|-------|--------------|
| 185526dc424608 | 10 | started | passing |
| 7810192b9ee628 | 10 | stopped | warning |

**Build Args:**
- `REACT_APP_API_URL=https://examcraft-api.fly.dev`

### examcraft-db (PostgreSQL)

```
Image:    flyio/postgres-flex:17.2 (v0.1.0)
Region:   fra (Frankfurt)
Type:     Managed Postgres (Fly Postgres)
```

| Machine ID | Role | State | Health |
|------------|------|-------|--------|
| 080467db6d1228 | primary | started | 2/3 passing |

### examcraft-qdrant (Vector Database)

```
Image:    qdrant/qdrant:latest
Region:   fra (Frankfurt)
Memory:   1GB
CPU:      shared, 1 vCPU
Ports:    6333 (HTTP), 6334 (gRPC)
Volume:   qdrant_data (persistent)
```

| Machine ID | Version | State | Health Check |
|------------|---------|-------|--------------|
| 6839144c610378 | 4 | started | passing |

**Konfiguration:**
- `auto_stop_machines=suspend` (schnellerer Neustart)
- Health Check: `/healthz` (30s interval)

### examcraft-rabbitmq (Message Broker)

```
Image:    library/rabbitmq:4-management-alpine
Region:   fra (Frankfurt)
Ports:    5672 (AMQP), 15672 (Management)
```

| Machine ID | Version | State | Health Check |
|------------|---------|-------|--------------|
| 2873e01f6e1798 | 2 | started | passing |

### examcraft-celery (Background Worker)

```
Image:    examcraft-celery:deployment-01KH64AZJZ0RHM5PTRNF0ZCJ0N
Region:   fra (Frankfurt)
Process:  worker
```

| Machine ID | Version | State | Role |
|------------|---------|-------|------|
| d896e22b2e3978 | 12 | started | active |
| 287d510a05de68 | 12 | stopped | standby† |

† Standby-Machine übernimmt bei Hardware-Ausfall

## Netzwerk-Kommunikation

```mermaid
sequenceDiagram
    participant U as User Browser
    participant W as examcraft-web<br/>(Frontend)
    participant A as examcraft-api<br/>(Backend)
    participant D as examcraft-db<br/>(PostgreSQL)
    participant R as Redis<br/>(Sessions)
    participant Q as examcraft-qdrant<br/>(Vectors)
    participant C as Claude API

    U->>W: HTTPS Request
    W->>U: React SPA (HTML/JS/CSS)

    U->>A: API Request (HTTPS)
    A->>R: Session Validation
    R-->>A: Session Valid

    A->>D: SQL Query
    D-->>A: Data

    alt RAG Query
        A->>Q: Vector Search
        Q-->>A: Similar Documents
        A->>C: Generate with Context
        C-->>A: Generated Response
    end

    A-->>U: JSON Response
```

## Interne URLs (Private Network)

Die Services kommunizieren über das Fly.io Private Network mit `.internal` Domains:

```bash
# PostgreSQL (Fly Postgres)
DATABASE_URL=postgres://examcraft:***@examcraft-db.internal:5432/examcraft

# Redis (Upstash)
REDIS_URL=redis://default:***@fly-examcraft-redis.upstash.io:6379

# Qdrant Vector Database
QDRANT_URL=http://examcraft-qdrant.internal:6333

# RabbitMQ Message Broker
CELERY_BROKER_URL=amqp://examcraft:***@examcraft-rabbitmq.internal:5672
```

## Deployment Workflow

```mermaid
flowchart LR
    subgraph Development
        Code["Code Push"]
        PR["Pull Request"]
        Main["Merge to main"]
    end

    subgraph CI["GitHub Actions"]
        Test["Tests"]
        Build["Build Images"]
        Deploy["fly deploy"]
    end

    subgraph Fly["Fly.io"]
        Backend["Backend"]
        Frontend["Frontend"]
    end

    Code --> PR
    PR --> Main
    Main --> Test
    Test --> Build
    Build --> Deploy
    Deploy --> Backend
    Deploy --> Frontend
```

### Deployment-Befehle

```bash
# Alle Services deployen
make deploy-all

# Nur Backend + Frontend
make deploy

# Einzelne Services
fly deploy -c fly.toml           # Backend
fly deploy -c fly.frontend.toml  # Frontend
fly deploy -c fly.qdrant.toml    # Qdrant
fly deploy -c fly.rabbitmq.toml  # RabbitMQ
fly deploy -c fly.celery.toml    # Celery
```

## Monitoring

```bash
# Logs anzeigen
fly logs --app examcraft-api
fly logs --app examcraft-web

# Status prüfen
fly status --app examcraft-api

# SSH in Container
fly ssh console --app examcraft-api

# Postgres CLI
fly postgres connect -a examcraft-db
```

## Secrets (Konfigurierte Umgebungsvariablen)

Die folgenden Secrets sind im Backend konfiguriert:

| Secret | Beschreibung |
|--------|--------------|
| `DATABASE_URL` | Auto-attached von Fly Postgres |
| `REDIS_URL` | Upstash Redis Connection String |
| `JWT_SECRET_KEY` | JWT Token Signing Key |
| `ANTHROPIC_API_KEY` | Claude API Key |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Secret |
| `MICROSOFT_CLIENT_ID` | Microsoft OAuth Client ID |
| `MICROSOFT_CLIENT_SECRET` | Microsoft OAuth Secret |
| `CORS_ORIGINS` | Erlaubte CORS Origins |
| `FRONTEND_URL` | Frontend URL für Redirects |

## Kosten (Geschätzt)

| Service | Typ | Geschätzte Kosten/Monat |
|---------|-----|-------------------------|
| examcraft-db | Fly Postgres | ~$7 |
| examcraft-redis | Upstash Pay-as-you-go | ~$0-5 |
| examcraft-api | Fly Machine (512MB) | ~$3 |
| examcraft-web | Fly Machine (256MB) | ~$2 |
| examcraft-qdrant | Fly Machine (1GB) + Volume | ~$7 |
| examcraft-rabbitmq | Fly Machine + Volume | ~$3 |
| examcraft-celery | Fly Machine | ~$3 |
| **Total** | | **~$25-30** |

## Troubleshooting

### Backend Health Check Failed

```bash
# Logs prüfen
fly logs --app examcraft-api

# Machine neustarten
fly machines restart <machine-id> --app examcraft-api

# SSH für Debugging
fly ssh console --app examcraft-api
```

### Qdrant nicht erreichbar

```bash
# Status prüfen
fly status --app examcraft-qdrant

# Qdrant Health Check
curl https://examcraft-qdrant.fly.dev/healthz

# Wenn suspended, wird automatisch gestartet bei nächstem Request
```

### Database Connection Issues

```bash
# Postgres Status
fly status --app examcraft-db

# Direkte Verbindung testen
fly postgres connect -a examcraft-db

# Connection String prüfen
fly secrets list --app examcraft-api | grep DATABASE
```
