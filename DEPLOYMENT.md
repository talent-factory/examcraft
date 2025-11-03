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
DATABASE_URL=postgresql://examcraft:examcraft_dev_password@postgres:5432/examcraft  # pragma: allowlist secret

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

## Production Deployment (Render.com)

### Recommended Setup

**Deployment Mode:** Always use `full` for production

**Environment Variables:**
```yaml
# render.yaml
services:
  - type: web
    name: examcraft-backend
    env: docker
    dockerfilePath: ./packages/core/backend/Dockerfile
    envVars:
      - key: DEPLOYMENT_MODE
        value: full
      - key: DEFAULT_SUBSCRIPTION_TIER
        value: professional
      - key: DATABASE_URL
        fromDatabase:
          name: examcraft-db
          property: connectionString
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: QDRANT_URL
        value: http://qdrant:6333
```

**Why Full Deployment for Production:**
- All features available
- Access controlled via RBAC
- Users can upgrade subscriptions without redeployment
- Admins can assign different tiers to different institutions

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

## Troubleshooting

### Seed Scripts Not Running

**Problem:** Premium prompts not seeded

**Solution:**
1. Check `DEPLOYMENT_MODE=full` in `.env`
2. Verify `packages/premium/backend` exists and is mounted
3. Check backend logs: `docker compose logs backend`

### Premium Components Not Loading

**Problem:** "Feature Not Available" message shown

**Solution:**
1. Check `REACT_APP_DEPLOYMENT_MODE=full` in frontend environment
2. Verify `packages/premium/frontend/src` is mounted at `/app/src/premium`
3. Clear browser cache and rebuild: `docker compose up -d --build frontend`

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
