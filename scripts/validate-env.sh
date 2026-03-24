#!/bin/bash

# ExamCraft AI - Environment Validation Script
# Prüft, ob alle erforderlichen Umgebungsvariablen gesetzt sind

set -e

# Farben für Output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 ExamCraft AI - Environment Validation${NC}"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ ERROR: .env file not found${NC}"
    echo ""
    echo "Please create .env file from .env.example:"
    echo "  cp .env.example .env"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ .env file found${NC}"
echo ""

# Load .env
source .env

# Required variables for all tiers (can be set in docker-compose.yml)
REQUIRED_CORE_VARS=()

# Required variables for Premium/Enterprise
REQUIRED_PREMIUM_VARS=(
    "ANTHROPIC_API_KEY"
    "OPENAI_API_KEY"
    "CLAUDE_MODEL"
)

# Optional but recommended variables
RECOMMENDED_VARS=(
    "GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET"
    "MICROSOFT_CLIENT_ID"
    "MICROSOFT_CLIENT_SECRET"
)

# Check Core variables
echo -e "${BLUE}📦 Core Variables:${NC}"
CORE_MISSING=0
for var in "${REQUIRED_CORE_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "   ${RED}❌ $var${NC} - NOT SET"
        CORE_MISSING=$((CORE_MISSING + 1))
    else
        echo -e "   ${GREEN}✅ $var${NC} - SET"
    fi
done
echo ""

# Detect tier based on available packages
TIER="core"
if [ -d "packages/premium" ] && [ "$(ls -A packages/premium)" ]; then
    TIER="premium"
fi
if [ -d "packages/enterprise" ] && [ "$(ls -A packages/enterprise)" ]; then
    TIER="enterprise"
fi

# Check Premium/Enterprise variables
if [[ "$TIER" != "core" ]]; then
    echo -e "${BLUE}🌟 Premium/Enterprise Variables:${NC}"
    PREMIUM_MISSING=0
    for var in "${REQUIRED_PREMIUM_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "   ${RED}❌ $var${NC} - NOT SET"
            PREMIUM_MISSING=$((PREMIUM_MISSING + 1))
        else
            # Show first 20 chars for API keys
            if [[ "$var" == *"API_KEY"* ]]; then
                echo -e "   ${GREEN}✅ $var${NC} - SET (${!var:0:20}...)"
            else
                echo -e "   ${GREEN}✅ $var${NC} - SET (${!var})"
            fi
        fi
    done
    echo ""
fi

# Check recommended variables
echo -e "${BLUE}💡 Recommended Variables (OAuth):${NC}"
RECOMMENDED_MISSING=0
for var in "${RECOMMENDED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "   ${YELLOW}⚠️  $var${NC} - NOT SET (OAuth will not work)"
        RECOMMENDED_MISSING=$((RECOMMENDED_MISSING + 1))
    else
        echo -e "   ${GREEN}✅ $var${NC} - SET"
    fi
done
echo ""

# Summary
echo "=========================================="
if [ $CORE_MISSING -gt 0 ]; then
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo ""
    echo "Missing $CORE_MISSING required core variable(s)."
    echo "Please configure them in .env file."
    exit 1
fi

if [[ "$TIER" != "core" ]] && [ $PREMIUM_MISSING -gt 0 ]; then
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo ""
    echo "Missing $PREMIUM_MISSING required Premium/Enterprise variable(s)."
    echo "Please configure them in .env file."
    echo ""
    echo "Hint: Make sure ANTHROPIC_API_KEY is set with your Anthropic API key."
    exit 1
fi

echo -e "${GREEN}✅ VALIDATION PASSED${NC}"
echo ""
if [ $RECOMMENDED_MISSING -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: $RECOMMENDED_MISSING recommended variable(s) not set.${NC}"
    echo "OAuth authentication will not work without these variables."
    echo ""
fi

echo "All required environment variables are configured correctly!"
echo ""
