#!/bin/bash

# ExamCraft AI - Development Environment
# Simplified 2-Tier Deployment: Core (OpenSource) or Full (Premium + Enterprise)
# All feature access controlled via RBAC

set -e

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse command-line arguments
FORCE_MODE=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --core)
      FORCE_MODE="core"
      shift
      ;;
    --full)
      FORCE_MODE="full"
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Usage: $0 [--core|--full]"
      exit 1
      ;;
  esac
done

# Funktion: Prüfe ob Submodule initialisiert ist
submodule_initialized() {
    [ -d "packages/$1" ] && [ "$(ls -A packages/$1)" ]
}

# Auto-detect deployment mode (unless forced)
if [ -n "$FORCE_MODE" ]; then
    DEPLOYMENT_MODE="$FORCE_MODE"
    echo -e "${YELLOW}🔧 Forced deployment mode: ${DEPLOYMENT_MODE}${NC}"
else
    if submodule_initialized "premium" || submodule_initialized "enterprise"; then
        DEPLOYMENT_MODE="full"
        echo -e "${GREEN}✅ Auto-detected: Full deployment (Premium + Enterprise available)${NC}"
    else
        DEPLOYMENT_MODE="core"
        echo -e "${BLUE}ℹ️  Auto-detected: Core deployment (OpenSource)${NC}"
    fi
fi

# Set deployment variables
if [ "$DEPLOYMENT_MODE" = "full" ]; then
    COMPOSE_FILE="docker-compose.full.yml"
    TIER="Full (Premium + Enterprise)"
    TIER_EMOJI="🌟"
    TIER_COLOR=$GREEN
else
    COMPOSE_FILE="docker-compose.yml"
    TIER="Core (OpenSource)"
    TIER_EMOJI="🚀"
    TIER_COLOR=$BLUE
fi

# Header
echo ""
echo -e "${TIER_COLOR}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${TIER_COLOR}║  ${TIER_EMOJI} ExamCraft AI - ${TIER} Edition  ${TIER_EMOJI} ║${NC}"
echo -e "${TIER_COLOR}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📦 Deployment Mode:${NC} ${DEPLOYMENT_MODE}"
echo -e "${BLUE}📄 Compose File:${NC} ${COMPOSE_FILE}"
echo ""

# Feature-Info basierend auf Deployment-Mode
if [ "$DEPLOYMENT_MODE" = "full" ]; then
    echo -e "${GREEN}✅ Available Features (Access via RBAC):${NC}"
    echo "   - Document Upload & Processing"
    echo "   - RAG Question Generation (Qdrant)"
    echo "   - Document ChatBot"
    echo "   - Advanced Prompt Management"
    echo "   - Semantic Search & Vector Storage"
    echo "   - OAuth (Google, Microsoft)"
    echo "   - SSO/SAML Integration (Enterprise)"
    echo "   - Custom Branding (Enterprise)"
    echo "   - API Access Management (Enterprise)"
    echo "   - Advanced Analytics (Enterprise)"
    echo ""
    echo -e "${BLUE}💡 Access Control:${NC} All features available, controlled by RBAC & Subscription Tiers"
else
    echo -e "${GREEN}✅ Core Features:${NC}"
    echo "   - Document Upload (limited)"
    echo "   - Basic Question Generation (limited)"
    echo "   - Document Library"
    echo "   - Question Review"
    echo "   - OAuth (Google, Microsoft)"
    echo ""
    echo -e "${YELLOW}ℹ️  Premium/Enterprise Features:${NC}"
    echo "   Not available in Core deployment"
    echo "   To enable: Clone premium/enterprise packages and run with --full"
fi

echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env created. Please configure your environment variables.${NC}"
    else
        echo -e "${RED}❌ .env.example not found. Please create .env manually.${NC}"
        exit 1
    fi
fi

# Validate environment variables
echo ""
echo -e "${BLUE}🔍 Validating environment variables...${NC}"
if [ -f scripts/validate-env.sh ]; then
    bash scripts/validate-env.sh || exit 1
else
    echo -e "${YELLOW}⚠️  Warning: scripts/validate-env.sh not found, skipping validation${NC}"
fi

# Load .env file to check variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Check for required API keys (Full mode)
if [ "$DEPLOYMENT_MODE" = "full" ]; then
    if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$CLAUDE_API_KEY" ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Warning: ANTHROPIC_API_KEY not set${NC}"
        echo "Full deployment requires Claude API access for Premium features."
        echo "Please set ANTHROPIC_API_KEY or CLAUDE_API_KEY in .env file."
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Initialize Git Submodules (Full mode)
if [ "$DEPLOYMENT_MODE" = "full" ]; then
    echo ""
    echo -e "${BLUE}📦 Initializing Git Submodules...${NC}"

    if ! submodule_initialized "premium"; then
        echo "Initializing premium package..."
        git submodule update --init --recursive packages/premium
    else
        echo "✅ Premium package already initialized"
    fi

    if ! submodule_initialized "enterprise"; then
        echo "Initializing enterprise package..."
        git submodule update --init --recursive packages/enterprise
    else
        echo "✅ Enterprise package already initialized"
    fi

    # Setup Premium component symlinks for CRA imports
    echo ""
    echo -e "${BLUE}🔗 Setting up Premium component symlinks...${NC}"
    if [ -f scripts/setup-premium-symlinks.sh ]; then
        bash scripts/setup-premium-symlinks.sh
    else
        echo -e "${YELLOW}⚠️  Warning: scripts/setup-premium-symlinks.sh not found${NC}"
    fi
fi

# Docker Cleanup
echo ""
echo -e "${BLUE}🧹 Cleaning up existing containers...${NC}"
docker compose --env-file .env -f "$COMPOSE_FILE" down 2>/dev/null || true

# Pre-pull images
echo ""
echo -e "${BLUE}🐳 Pre-pulling Docker images...${NC}"
docker pull redis:7-alpine 2>/dev/null || echo "  ⚠️  Redis image pull skipped"
docker pull postgres:16-alpine 2>/dev/null || echo "  ⚠️  PostgreSQL image pull skipped"

if [ "$DEPLOYMENT_MODE" = "full" ]; then
    docker pull qdrant/qdrant:latest 2>/dev/null || echo "  ⚠️  Qdrant image pull skipped"
fi

echo ""

# Start Docker containers
echo -e "${BLUE}🚀 Starting Docker containers...${NC}"
echo ""

if [ "$DEPLOYMENT_MODE" = "full" ]; then
    # Full mode: Rebuild to ensure volume mounts work correctly
    docker compose --env-file .env -f "$COMPOSE_FILE" up -d --build --pull=never
else
    # Core mode: Simple startup
    docker compose --env-file .env -f "$COMPOSE_FILE" up -d --pull=never
fi

# Wait for backend to be ready
echo ""
echo -e "${BLUE}⏳ Waiting for backend to be ready...${NC}"
sleep 5

# Seed development data (Full mode only)
if [ "$DEPLOYMENT_MODE" = "full" ]; then
    echo ""
    echo -e "${BLUE}🌱 Seeding development data...${NC}"
    docker compose --env-file .env -f "$COMPOSE_FILE" exec -T backend python scripts/seed_dev_data.py 2>/dev/null || echo -e "${YELLOW}⚠️  Seeding skipped (backend not ready or already seeded)${NC}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅  ExamCraft AI ${TIER} is running!  ✅  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📍 Access Points:${NC}"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6380 (external) / 6379 (internal)"

if [ "$DEPLOYMENT_MODE" = "full" ]; then
    echo "   - Qdrant: http://localhost:6333"
fi

echo ""
echo -e "${BLUE}📊 View logs:${NC}"
echo "   docker compose --env-file .env -f ${COMPOSE_FILE} logs -f"
echo ""
echo -e "${BLUE}🛑 Stop services:${NC}"
echo "   docker compose --env-file .env -f ${COMPOSE_FILE} down"
echo ""
echo -e "${BLUE}💡 Important:${NC}"
echo "   - Feature access is controlled by RBAC & Subscription Tiers"
echo "   - Login and configure user roles/subscriptions in the admin panel"

if [ "$DEPLOYMENT_MODE" = "core" ]; then
    echo ""
    echo -e "${YELLOW}ℹ️  To enable Premium/Enterprise features:${NC}"
    echo "   1. Clone premium/enterprise packages as git submodules"
    echo "   2. Run: ./start-dev.sh --full"
fi

echo ""
