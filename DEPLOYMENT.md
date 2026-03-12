# ExamCraft AI - Deployment Guide

## Overview

ExamCraft AI supports two deployment modes:

- **Core (OpenSource)**: Community Edition with limited features
- **Full (Premium + Enterprise)**: Complete version with all features, access controlled via RBAC

## Deployment Modes

### Core Deployment (OpenSource)

**Features:**
- Document Upload (limited)
- Basic Question Generation (limited)
- Document Library
- Question Review
- OAuth (Google, Microsoft)

**Docker Compose:**
```bash
docker compose --env-file .env -f docker-compose.yml up -d
```

**Or use the startup script:**
```bash
./start-dev.sh --core
```

### Full Deployment (Premium + Enterprise)

**Features:**

- All Core features (unlimited)
- RAG Question Generation (Qdrant)
- Document ChatBot
- Advanced Prompt Management
- Semantic Search & Vector Storage
- SSO/SAML Integration (Enterprise)
- Custom Branding (Enterprise)
- API Access Management (Enterprise)
- Advanced Analytics (Enterprise)

**Access Control:** All features available, controlled by RBAC & Subscription Tiers

**Docker Compose:**

```bash
docker compose --env-file .env -f docker-compose.full.yml up -d
```

**Or use the startup script:**

```bash
./start-dev.sh --full
```

## Auto-Detection

The startup script automatically detects the deployment mode based on available packages:

```bash
./start-dev.sh
```

- If `packages/premium` or `packages/enterprise` exists → **Full deployment**
- Otherwise → **Core deployment**

## Environment Variables

### Required for All Deployments

```bash
# Database
DATABASE_URL=postgresql://examcraft:examcraft_dev@postgres:5432/examcraft  # pragma: allowlist secret

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET_KEY=your_secret_key_here  # pragma: allowlist secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth (optional but recommended)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret
```

### Required for Full Deployment

```bash
# Deployment Mode
DEPLOYMENT_MODE=full

# Qdrant Vector Database
QDRANT_URL=http://qdrant:6333
VECTOR_SERVICE_TYPE=qdrant

# Claude API (for RAG and ChatBot)
ANTHROPIC_API_KEY=your_anthropic_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

### Optional

```bash
# Sentry Error Tracking
SENTRY_DSN=your_sentry_dsn
ENABLE_SENTRY=false

# Environment
ENVIRONMENT=development
DEBUG=true
```

## Feature Access Control

### RBAC System

All feature access is controlled by the RBAC (Role-Based Access Control) system:

1. **Subscription Tiers**:
   - Free: Limited document uploads (5), limited questions (20/month)
   - Starter: More documents (50), more questions (200/month)
   - Professional: Unlimited documents, RAG generation, Prompt management
   - Enterprise: All features including SSO, Custom branding, API access

2. **User Roles**:
   - Student: View and answer questions
   - Assistant: Create and review questions
   - Dozent: Full question management
   - Admin: User and institution management

3. **Features**:
   - Each feature is tied to specific subscription tiers and roles
   - Access is checked at runtime via RBAC middleware
   - No environment variables needed for feature flags

### Frontend Component Loading

The frontend uses **Docker volume mounts** to merge Premium/Enterprise packages into the Core structure:

**Development (docker-compose.full.yml):**
```yaml
frontend:
  volumes:
    # Core Frontend Source
    - ./packages/core/frontend/src:/app/src

    # Premium Frontend (mounted into Core structure)
    - ./packages/premium/frontend/src:/app/src/premium

    # Enterprise Frontend (mounted into Core structure)
    - ./packages/enterprise/frontend/src:/app/src/enterprise
```

**How it works:**
1. Core frontend is mounted at `/app/src`
2. Premium components are mounted at `/app/src/premium`
3. Enterprise components are mounted at `/app/src/enterprise`
4. All relative imports work correctly
5. Hot-reload works seamlessly for all packages

## Production Deployment (Fly.io) - Recommended

ExamCraft AI is deployed on [Fly.io](https://fly.io) for production. This enables
self-hosting all services including Qdrant Vector Database without external
cloud dependencies.

### Architecture

| Service | Fly.io Solution | Estimated Cost |
|---------|-----------------|----------------|
| PostgreSQL | Fly Postgres (Managed) | ~$7/Mo |
| Redis | Fly Upstash Redis | ~$0-5/Mo |
| RabbitMQ | Fly Machine + Volume | ~$3/Mo |
| Qdrant | Fly Machine + Volume | ~$7/Mo |
| Backend | Fly Machine (Auto-Scale) | ~$3/Mo |
| Celery Worker | Fly Machine | ~$3/Mo |
| Frontend | Fly Machine (Nginx) | ~$2/Mo |

**Total Estimated Cost:** ~$25-30/month

### Configuration Files

```
ExamCraft/
├── fly.toml              # Backend (API Server)
├── fly.frontend.toml     # Frontend (Nginx)
├── fly.qdrant.toml       # Qdrant Vector Database
├── fly.rabbitmq.toml     # RabbitMQ Message Broker
├── fly.celery.toml       # Celery Worker
└── packages/core/
    ├── backend/
    │   ├── Dockerfile.fly
    │   └── docker-entrypoint.sh
    └── frontend/
        └── Dockerfile.fly
```

### Deployment Steps

#### 1. Install Fly CLI

```bash
# macOS
brew install flyctl

# or via curl
curl -L https://fly.io/install.sh | sh
```

#### 2. Create Fly.io Apps

```bash
# Login to Fly.io
fly auth login

# Create apps (Frankfurt region)
fly apps create examcraft-api --org personal
fly apps create examcraft-web --org personal
fly apps create examcraft-qdrant --org personal
fly apps create examcraft-rabbitmq --org personal
fly apps create examcraft-celery --org personal
```

#### 3. Provision Databases

```bash
# PostgreSQL (Managed)
fly postgres create --name examcraft-db --region fra

# Attach to backend
fly postgres attach examcraft-db --app examcraft-api

# Redis (Upstash)
fly redis create --name examcraft-redis --region fra
```

#### 4. Create Persistent Volumes

```bash
# Qdrant volume (1GB)
fly volumes create qdrant_data --size 1 --region fra --app examcraft-qdrant

# RabbitMQ volume (1GB)
fly volumes create rabbitmq_data --size 1 --region fra --app examcraft-rabbitmq
```

#### 5. Set Secrets

```bash
# Backend secrets (replace with real values)
fly secrets set \
  JWT_SECRET_KEY="<your-jwt-secret>" \
  ANTHROPIC_API_KEY="<your-anthropic-key>" \
  GOOGLE_CLIENT_ID="<your-google-id>" \
  GOOGLE_CLIENT_SECRET="<your-google-secret>" \
  --app examcraft-api

# RabbitMQ password
fly secrets set RABBITMQ_DEFAULT_PASS="<your-rabbitmq-password>" --app examcraft-rabbitmq

# Celery broker URL (use actual password from above)
fly secrets set CELERY_BROKER_URL="amqp://examcraft:<password>@examcraft-rabbitmq.internal:5672" --app examcraft-celery
```

#### 6. Deploy Services

```bash
# Deploy in order (dependencies first)
fly deploy -c fly.qdrant.toml
fly deploy -c fly.rabbitmq.toml
fly deploy -c fly.toml           # Backend
fly deploy -c fly.celery.toml
fly deploy -c fly.frontend.toml
```

### Private Networking

All services communicate via Fly's private network using `.internal` domains:

- `examcraft-db.internal` - PostgreSQL
- `examcraft-redis.internal` - Redis
- `examcraft-qdrant.internal:6333` - Qdrant
- `examcraft-rabbitmq.internal:5672` - RabbitMQ

### Monitoring

```bash
# View logs
fly logs --app examcraft-api

# Check status
fly status --app examcraft-api

# SSH into container
fly ssh console --app examcraft-api
```

### Custom Domain

```bash
# Add custom domain
fly certs create examcraft.ai --app examcraft-web

# Verify DNS
fly certs show examcraft.ai --app examcraft-web
```

### GitHub Actions CI/CD

ExamCraft uses GitHub Actions for automated deployment on PR merge to main.

#### Required Secrets

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

| Secret | Description | How to Get |
|--------|-------------|------------|
| `FLY_API_TOKEN` | Fly.io API token for deployment | `fly tokens create deploy -x 999999h` |
| `SUBMODULE_TOKEN` | GitHub PAT for Premium submodules | GitHub Settings → Developer settings → PATs |

#### Create Fly.io Deploy Token

```bash
# Create a long-lived deployment token
fly tokens create deploy -x 999999h

# Copy the token and add it as FLY_API_TOKEN in GitHub Secrets
```

#### Workflow Overview

**Automatic Deployment (on push to main):**
1. CI/CD pipeline runs tests
2. `deploy.yml` deploys Backend then Frontend
3. Health checks verify deployment success
4. Summary shows deployment status

**Manual Deployment:**
1. Go to Actions → "Deploy to Fly.io"
2. Click "Run workflow"
3. Select services to deploy
4. Infrastructure services (Qdrant, RabbitMQ, Celery) only via manual trigger

#### Makefile Commands

```bash
# Deploy Backend + Frontend
make deploy

# Deploy all services (including infrastructure)
make deploy-all

# Deploy individual services
make deploy-backend
make deploy-frontend
make deploy-qdrant
make deploy-rabbitmq
make deploy-celery

# Monitor deployments
make deploy-status
make deploy-logs
```

### OAuth Configuration (Google)

When deploying to Fly.io, Google OAuth requires specific configuration:

#### Google Cloud Console Settings

Navigate to [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and configure:

**Authorized JavaScript Origins:**
```
https://examcraft-web.fly.dev
http://localhost:3000
```

**Authorized Redirect URIs:**
```
https://examcraft-api.fly.dev/api/auth/oauth/google/callback
http://localhost:8000/api/auth/oauth/google/callback
```

> **Important:** The redirect URI path must be `/api/auth/oauth/{provider}/callback` - this is
> the format used by the backend OAuth endpoints.

#### Required Environment Variables

The backend requires these secrets for OAuth:

```bash
fly secrets set \
  GOOGLE_CLIENT_ID="<your-google-client-id>" \
  GOOGLE_CLIENT_SECRET="<your-google-client-secret>" \
  CORS_ORIGINS="http://localhost:3000,http://localhost:8000,https://examcraft-web.fly.dev" \
  FRONTEND_URL="https://examcraft-web.fly.dev" \
  --app examcraft-api
```

#### Troubleshooting OAuth

| Error | Cause | Solution |
|-------|-------|----------|
| `redirect_uri_mismatch` | Callback URL doesn't match Google config | Verify the exact path: `/api/auth/oauth/google/callback` |
| `Failed to fetch` | CORS not configured | Add frontend domain to `CORS_ORIGINS` |
| HTTP vs HTTPS mismatch | Fly.io terminates SSL at proxy | Backend handles `X-Forwarded-Proto` header automatically |

---

## Migration from Old Setup

If you're migrating from the old 3-file Docker Compose setup:

**Old:**
```bash
docker compose -f docker-compose.yml \
               -f docker-compose.premium.yml \
               -f docker-compose.enterprise.yml \
               up -d
```

**New:**
```bash
./start-dev.sh --full
# OR
docker compose --env-file .env -f docker-compose.full.yml up -d
```

### Breaking Changes

1. **Environment Variables:**
   - ❌ `ENABLE_PREMIUM_FEATURES` → ✅ `DEPLOYMENT_MODE=full`
   - ❌ `ENABLE_ENTERPRISE_FEATURES` → ✅ `DEPLOYMENT_MODE=full`
   - ❌ `ENABLE_RAG_GENERATION` → Removed (always available in Full mode)
   - ❌ `ENABLE_CHATBOT` → Removed (always available in Full mode)

2. **Frontend Environment Variables:**
   - ❌ `REACT_APP_ENABLE_PREMIUM_FEATURES` → ✅ `REACT_APP_DEPLOYMENT_MODE=full`
   - ❌ `REACT_APP_ENABLE_ENTERPRISE_FEATURES` → ✅ `REACT_APP_DEPLOYMENT_MODE=full`

3. **Docker Volumes:**
   - Frontend now uses direct volume mounts for Premium/Enterprise packages
   - Simpler than previous approach, preserves directory structure
   - Hot-reload works correctly for all packages

## Development Workflow

### OpenSource Contributors (Core)

```bash
# Clone repository
git clone https://github.com/examcraft/examcraft.git
cd examcraft

# Start Core deployment
./start-dev.sh
```

### Private Development (Full)

```bash
# Clone private repository
git clone https://github.com/talentfactory/examcraft-private.git
cd examcraft-private

# Initialize submodules
git submodule update --init --recursive

# Start Full deployment
./start-dev.sh
```

**Note:** The `start-dev.sh` script automatically runs `scripts/setup-premium-symlinks.sh` to create symlinks for Premium/Enterprise components. This enables:
- Native Node.js development (without Docker)
- IDE autocomplete for Premium components
- Local testing with `npm start`

If developing inside Docker containers, symlinks are not needed as volume mounts handle component loading.

## Troubleshooting

### Seed Scripts Not Running

**Problem:** Premium prompts not seeded

**Solution:**
1. Check `DEPLOYMENT_MODE=full` in `.env`
2. Verify `packages/premium/backend` exists and is mounted
3. Check backend logs: `docker compose logs backend`

### Premium Components Not Loading

**Problem:** "RAG Exam Creator - Premium Feature" or "Feature Not Available" message shown despite Full deployment

**Solution:**

**For Docker Development:**
1. Check `REACT_APP_DEPLOYMENT_MODE=full` in frontend environment
2. Verify `packages/premium/frontend/src` is mounted at `/app/src/premium` in `docker-compose.full.yml`
3. Rebuild frontend container: `docker compose -f docker-compose.full.yml up -d --build frontend`
4. Clear browser cache (Cmd+Shift+R / Ctrl+Shift+R)

**For Native Development (npm start):**
1. Ensure symlinks are created: `bash scripts/setup-premium-symlinks.sh`
2. Verify symlinks exist:
   ```bash
   ls -la packages/core/frontend/src/premium/components/
   # Should show symlinks to Premium components
   ```
3. Check `REACT_APP_DEPLOYMENT_MODE=full` in `.env`
4. Restart dev server: `npm start` (in packages/core/frontend)

**Common Issue - Missing RAGExamCreator Symlink:**
If only DocumentChat works but RAG Exam Creator shows upgrade prompt:
```bash
# Run symlink setup (fixed in TF-177)
bash scripts/setup-premium-symlinks.sh
```

### Qdrant Connection Failed

**Problem:** Backend can't connect to Qdrant

**Solution:**
1. Ensure Qdrant container is running: `docker compose ps`
2. Check Qdrant health: `curl http://localhost:6333/health`
3. Verify `QDRANT_URL=http://qdrant:6333` (internal Docker network name)

### RBAC Features Not Working

**Problem:** User can't access features despite subscription

**Solution:**
1. Check RBAC seed data: Backend logs should show "✅ RBAC data seeded"
2. Verify user's institution subscription tier in database
3. Check user roles: `docker compose exec backend python scripts/seed_dev_data.py`

## Support

- **Issues:** https://github.com/examcraft/examcraft/issues
- **Documentation:** https://docs.examcraft.ai
- **Discord:** https://discord.gg/examcraft

## License

- **Core:** MIT License (OpenSource)
- **Premium/Enterprise:** Proprietary License
