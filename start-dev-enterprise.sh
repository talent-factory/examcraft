#!/bin/bash

# ExamCraft AI - Enterprise Development Environment
# Core + Premium + Enterprise Features (Enterprise Tier)

set -e

echo "🏢 Starting ExamCraft AI - Enterprise Edition"
echo "=============================================="
echo ""
echo "📦 Packages: Core + Premium + Enterprise"
echo "💼 Tier: Enterprise"
echo "✅ Features:"
echo "   - All Core Features"
echo "   - All Premium Features"
echo "   - SSO/SAML Integration"
echo "   - OAuth (Google, Microsoft)"
echo "   - Custom Branding"
echo "   - API Access Management"
echo "   - Advanced Analytics"
echo "   - LDAP Integration (Optional)"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env created. Please configure your environment variables."
    else
        echo "❌ .env.example not found. Please create .env manually."
    fi
fi

# Check for required API keys
MISSING_KEYS=()

if [ -z "$ANTHROPIC_API_KEY" ]; then
    MISSING_KEYS+=("ANTHROPIC_API_KEY")
fi

if [ -z "$API_KEY_ENCRYPTION_KEY" ]; then
    MISSING_KEYS+=("API_KEY_ENCRYPTION_KEY")
fi

if [ ${#MISSING_KEYS[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  Warning: Missing required environment variables:"
    for key in "${MISSING_KEYS[@]}"; do
        echo "   - $key"
    done
    echo ""
    echo "Please set these variables in .env file."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Initialize Git Submodules
echo ""
echo "📦 Initializing Git Submodules..."
git submodule update --init --recursive packages/premium packages/enterprise

# Start All services
echo ""
echo "🐳 Starting Docker containers..."
docker-compose \
    -f docker-compose.yml \
    -f docker-compose.premium.yml \
    -f docker-compose.enterprise.yml \
    up -d

echo ""
echo "✅ ExamCraft AI Enterprise is starting!"
echo ""
echo "📍 Access Points:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo "   - ChromaDB: http://localhost:8001"
echo "   - Qdrant: http://localhost:6333"
echo ""
echo "📊 View logs:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.premium.yml -f docker-compose.enterprise.yml logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.premium.yml -f docker-compose.enterprise.yml down"
echo ""
