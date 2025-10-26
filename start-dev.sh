#!/bin/bash

# ExamCraft AI - Development Environment
# Intelligente Erkennung: Core / Premium / Enterprise

set -e

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funktion: Prüfe ob Package existiert
package_exists() {
    [ -d "packages/$1" ] && [ -f "packages/$1/.git" ]
}

# Funktion: Prüfe ob Submodule initialisiert ist
submodule_initialized() {
    [ -d "packages/$1" ] && [ "$(ls -A packages/$1)" ]
}

# Erkenne verfügbare Packages
AVAILABLE_PACKAGES=("core")
COMPOSE_FILES=("-f docker-compose.yml")

if package_exists "premium" || submodule_initialized "premium"; then
    AVAILABLE_PACKAGES+=("premium")
    COMPOSE_FILES+=("-f docker-compose.premium.yml")
fi

if package_exists "enterprise" || submodule_initialized "enterprise"; then
    AVAILABLE_PACKAGES+=("enterprise")
    COMPOSE_FILES+=("-f docker-compose.enterprise.yml")
fi

# Bestimme Tier basierend auf verfügbaren Packages
if [[ " ${AVAILABLE_PACKAGES[@]} " =~ " enterprise " ]]; then
    TIER="Enterprise"
    TIER_EMOJI="🏢"
    TIER_COLOR=$BLUE
elif [[ " ${AVAILABLE_PACKAGES[@]} " =~ " premium " ]]; then
    TIER="Premium"
    TIER_EMOJI="🌟"
    TIER_COLOR=$GREEN
else
    TIER="Core (Open Source)"
    TIER_EMOJI="🚀"
    TIER_COLOR=$YELLOW
fi

# Header
echo -e "${TIER_COLOR}${TIER_EMOJI} Starting ExamCraft AI - ${TIER} Edition${NC}"
echo "=============================================="
echo ""
echo -e "${BLUE}📦 Packages:${NC} ${AVAILABLE_PACKAGES[*]}"
echo ""

# Feature-Liste basierend auf Tier
if [[ "$TIER" == "Enterprise" ]]; then
    echo -e "${GREEN}✅ All Features Enabled:${NC}"
    echo "   - Document Upload & Processing"
    echo "   - RAG Question Generation"
    echo "   - Document ChatBot"
    echo "   - Advanced Prompt Management"
    echo "   - Semantic Search (Qdrant)"
    echo "   - SSO/SAML Integration"
    echo "   - OAuth (Google, Microsoft)"
    echo "   - Custom Branding"
    echo "   - API Access Management"
    echo "   - Advanced Analytics"
elif [[ "$TIER" == "Premium" ]]; then
    echo -e "${GREEN}✅ Premium Features:${NC}"
    echo "   - Document Upload & Processing"
    echo "   - RAG Question Generation"
    echo "   - Document ChatBot"
    echo "   - Advanced Prompt Management"
    echo "   - Semantic Search (Qdrant)"
    echo ""
    echo -e "${YELLOW}❌ Enterprise Features (Disabled):${NC}"
    echo "   - SSO/SAML Integration"
    echo "   - Custom Branding"
    echo "   - API Access Management"
else
    echo -e "${GREEN}✅ Core Features:${NC}"
    echo "   - Document Upload (max 5)"
    echo "   - Basic Question Generation (20/month)"
    echo "   - Document Library"
    echo "   - Question Review"
    echo ""
    echo -e "${YELLOW}❌ Premium/Enterprise Features (Disabled):${NC}"
    echo "   - RAG Generation"
    echo "   - Document ChatBot"
    echo "   - Advanced Prompt Management"
    echo "   - SSO/SAML"
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

# Check for required API keys (Premium/Enterprise)
if [[ "$TIER" != "Core (Open Source)" ]]; then
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Warning: ANTHROPIC_API_KEY not set${NC}"
        echo "Premium/Enterprise features require Claude API access."
        echo "Please set ANTHROPIC_API_KEY in .env file."
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Initialize Git Submodules (falls noch nicht geschehen)
if [[ "$TIER" != "Core (Open Source)" ]]; then
    echo ""
    echo -e "${BLUE}📦 Initializing Git Submodules...${NC}"

    if [[ " ${AVAILABLE_PACKAGES[@]} " =~ " premium " ]] && ! submodule_initialized "premium"; then
        git submodule update --init --recursive packages/premium
    fi

    if [[ " ${AVAILABLE_PACKAGES[@]} " =~ " enterprise " ]] && ! submodule_initialized "enterprise"; then
        git submodule update --init --recursive packages/enterprise
    fi
fi

# Docker Cleanup (falls Container crashed sind)
echo ""
echo -e "${BLUE}🧹 Cleaning up crashed containers...${NC}"
docker compose --env-file .env ${COMPOSE_FILES[@]} rm -f -s -v 2>/dev/null || true

# Start Docker containers
echo ""
echo -e "${BLUE}🐳 Starting Docker containers...${NC}"

# For Premium/Enterprise: Rebuild frontend to ensure volume mounts work
if [[ "$TIER" != "Core (Open Source)" ]]; then
    echo -e "${YELLOW}🔨 Rebuilding frontend container (Premium/Enterprise component overrides)...${NC}"
    docker compose --env-file .env ${COMPOSE_FILES[@]} up -d --build frontend
    docker compose --env-file .env ${COMPOSE_FILES[@]} up -d
else
    docker compose --env-file .env ${COMPOSE_FILES[@]} up -d
fi

# Wait for backend to be ready
echo ""
echo -e "${BLUE}⏳ Waiting for backend to be ready...${NC}"
sleep 5

# Seed development data (only in development)
if [[ "$TIER" != "Core (Open Source)" ]]; then
    echo ""
    echo -e "${BLUE}🌱 Seeding development data...${NC}"
    docker compose --env-file .env ${COMPOSE_FILES[@]} exec -T backend python scripts/seed_dev_data.py 2>/dev/null || echo -e "${YELLOW}⚠️  Seeding skipped (backend not ready or already seeded)${NC}"
fi

echo ""
echo -e "${GREEN}✅ ExamCraft AI ${TIER} is starting!${NC}"
echo ""
echo -e "${BLUE}📍 Access Points:${NC}"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6380 (external) / 6379 (internal)"

if [[ "$TIER" != "Core (Open Source)" ]]; then
    echo "   - Qdrant: http://localhost:6333"
fi

echo ""
echo -e "${BLUE}📊 View logs:${NC}"
echo "   docker compose --env-file .env ${COMPOSE_FILES[@]} logs -f"
echo ""
echo -e "${BLUE}🛑 Stop services:${NC}"
echo "   docker compose --env-file .env ${COMPOSE_FILES[@]} down"
echo ""
echo -e "${BLUE}💡 Tip:${NC} Features are controlled by user roles and institution settings."
echo "   Login and configure your subscription tier in the admin panel."
echo ""
