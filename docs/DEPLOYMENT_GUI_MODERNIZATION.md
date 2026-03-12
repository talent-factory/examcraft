# 🚀 GUI Modernization Deployment Guide (TF-148)

## Overview

This guide explains how to deploy and test the GUI modernization feature (TF-148) using Docker.

## Prerequisites

- Docker and Docker Compose installed
- Git with the `feature/tf-148-gui-modernization` branch checked out
- Optional: Claude API key for full functionality

## Quick Start

### 1. Prepare Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys (optional for testing)
# ANTHROPIC_API_KEY=your_key_here
# GOOGLE_CLIENT_ID=your_id_here
# GOOGLE_CLIENT_SECRET=your_secret_here
```

### 2. Deploy with Script

```bash
# Make script executable
chmod +x scripts/deploy-gui-modernization.sh

# Deploy with default ports (Frontend: 3000, Backend: 8000)
./scripts/deploy-gui-modernization.sh

# Deploy with custom ports (for Git Worktrees)
./scripts/deploy-gui-modernization.sh --port-frontend 3001 --port-backend 8001

# Deploy with image rebuild
./scripts/deploy-gui-modernization.sh --build

# Deploy and show logs
./scripts/deploy-gui-modernization.sh --logs
```

### 3. Manual Docker Compose

```bash
# Set environment variables
export FRONTEND_PORT=3000
export BACKEND_PORT=8000

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:3000 | React Dashboard |
| **Backend API** | http://localhost:8000 | FastAPI Server |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | Vector DB UI |
| **Redis** | localhost:6380 | Cache (CLI: `redis-cli -p 6380`) |
| **PostgreSQL** | localhost:5432 | Database |

## Testing the GUI Modernization

### 1. Login

1. Open http://localhost:3000
2. Click "Sign Up" or use demo credentials
3. Create account or login

### 2. Test New Navigation

- **Sidebar**: Check collapsible sidebar with role-based navigation
- **Dashboard**: Verify hero section, quick actions, and stats cards
- **Feature Pages**:
  - `/documents` - Document upload and library
  - `/questions/generate` - RAG exam creation
  - `/questions/review` - Question review interface
  - `/admin` - Admin panel with user management

### 3. Test Responsive Design

- **Desktop**: Full sidebar visible
- **Tablet**: Sidebar collapses to icons
- **Mobile**: Hamburger menu for sidebar

### 4. Test Features

- Upload documents
- Generate questions with RAG
- Review questions
- Manage users (admin only)
- Manage prompts (admin only)

## Troubleshooting

### Services Won't Start

```bash
# Check Docker status
docker-compose ps

# View detailed logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild images
docker-compose build --no-cache
```

### Port Conflicts

```bash
# Use custom ports
export FRONTEND_PORT=3001
export BACKEND_PORT=8001
docker-compose up -d
```

### Database Issues

```bash
# Reset database
docker-compose down -v
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head
```

### Frontend Not Loading

```bash
# Check frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

## Git Worktrees Setup

For parallel development with multiple worktrees:

```bash
# Main worktree (develop branch)
export FRONTEND_PORT=3000
export BACKEND_PORT=8000
docker-compose up -d

# Feature worktree (feature/tf-148-gui-modernization)
cd ../examcraft-gui-modernization
export FRONTEND_PORT=3001
export BACKEND_PORT=8001
docker-compose up -d
```

Both worktrees share the same PostgreSQL, Redis, and Qdrant databases.

## Performance Monitoring

### Check Container Resource Usage

```bash
docker stats
```

### View Application Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Database Queries

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U examcraft -d examcraft

# Common queries
\dt                    # List tables
SELECT * FROM users;   # View users
\q                     # Exit
```

## Cleanup

```bash
# Stop containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Next Steps

1. ✅ Test the new GUI in browser
2. ✅ Verify all features work correctly
3. ✅ Test responsive design on different devices
4. ✅ Create Pull Request for code review
5. ✅ Merge to develop branch
6. ✅ Deploy to production

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review documentation: `docs/WORKTREE_SETUP.md`
- Check Linear ticket: TF-148
