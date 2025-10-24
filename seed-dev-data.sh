#!/bin/bash

# ExamCraft AI - Seed Development Data
# Führt seed_dev_data.py im Backend-Container aus

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

# Erkenne verfügbare Compose Files
COMPOSE_FILES=("-f docker-compose.yml")

if [ -d "packages/premium" ] && [ "$(ls -A packages/premium)" ]; then
    COMPOSE_FILES+=("-f docker-compose.premium.yml")
fi

if [ -d "packages/enterprise" ] && [ "$(ls -A packages/enterprise)" ]; then
    COMPOSE_FILES+=("-f docker-compose.enterprise.yml")
fi

# Führe Seed-Script im Backend-Container aus
docker compose ${COMPOSE_FILES[@]} exec backend python scripts/seed_dev_data.py

echo ""
echo -e "${GREEN}✅ Development data seeded successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Login Credentials:${NC}"
echo "   Email: admin@talent-factory.ch"
echo "   Password: admin123"
echo ""
echo -e "${BLUE}💡 Tip:${NC} Any user with @talent-factory.ch email will be auto-assigned to Talent Factory institution"
echo ""

