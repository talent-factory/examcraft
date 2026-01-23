#!/bin/bash

# ExamCraft AI - Seed Development Data
# Führt seed_dev_data.py im Backend-Container aus
# Verwendet 2-Tier-Architektur: Core oder Full

set -e

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}🌱 Seeding Development Data...${NC}"
echo ""

# Auto-detect deployment mode (same logic as start-dev.sh)
submodule_initialized() {
    [ -d "packages/$1" ] && [ "$(ls -A packages/$1 2>/dev/null)" ]
}

if submodule_initialized "premium" || submodule_initialized "enterprise"; then
    COMPOSE_FILE="docker-compose.full.yml"
    echo -e "${GREEN}✅ Detected: Full deployment${NC}"
else
    COMPOSE_FILE="docker-compose.yml"
    echo -e "${BLUE}ℹ️  Detected: Core deployment${NC}"
fi

echo ""

# Führe Seed-Script im Backend-Container aus
docker compose --env-file .env -f "$COMPOSE_FILE" exec backend python scripts/seed_dev_data.py

echo ""
echo -e "${GREEN}✅ Development data seeded successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Login Credentials:${NC}"
echo "   Email: admin@talent-factory.ch"
echo "   Password: admin123"
echo ""
echo -e "${BLUE}💡 Tip:${NC} Any user with @talent-factory.ch email will be auto-assigned to Talent Factory institution"
echo ""
