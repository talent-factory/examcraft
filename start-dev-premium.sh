#!/bin/bash

# ExamCraft AI - Premium Development Environment
# Core + Premium Features (Starter/Professional Tier)

set -e

echo "🌟 Starting ExamCraft AI - Premium Edition"
echo "=============================================="
echo ""
echo "📦 Packages: Core + Premium"
echo "💎 Tier: Starter / Professional"
echo "✅ Features:"
echo "   - All Core Features"
echo "   - RAG Question Generation (Starter+)"
echo "   - Document ChatBot (Professional+)"
echo "   - Advanced Prompt Management (Professional+)"
echo "   - Semantic Search (Starter+)"
echo "   - Vector Database (ChromaDB/Qdrant)"
echo ""
echo "❌ Disabled Features:"
echo "   - SSO/SAML (Enterprise)"
echo "   - Custom Branding (Enterprise)"
echo "   - API Access (Enterprise)"
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

# Check for ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "⚠️  Warning: ANTHROPIC_API_KEY not set"
    echo "Premium features require Claude API access."
    echo "Please set ANTHROPIC_API_KEY in .env file."
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
git submodule update --init --recursive packages/premium

# Start Core + Premium services
echo ""
echo "🐳 Starting Docker containers..."
docker-compose -f docker-compose.yml -f docker-compose.premium.yml up -d

echo ""
echo "✅ ExamCraft AI Premium is starting!"
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
echo "   docker-compose -f docker-compose.yml -f docker-compose.premium.yml logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.premium.yml down"
echo ""
