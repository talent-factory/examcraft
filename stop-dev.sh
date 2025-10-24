#!/bin/bash

# ExamCraft AI - Stop Development Environment
# Stoppt alle laufenden Container (Core / Premium / Enterprise)

set -e

# Farben für Output
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}🛑 Stopping ExamCraft AI Development Environment${NC}"
echo "=============================================="
echo ""

# Funktion: Prüfe ob Package existiert
package_exists() {
    [ -d "packages/$1" ] && [ -f "packages/$1/.git" ]
}

# Funktion: Prüfe ob Submodule initialisiert ist
submodule_initialized() {
    [ -d "packages/$1" ] && [ "$(ls -A packages/$1)" ]
}

# Erkenne verfügbare Packages
COMPOSE_FILES=("-f docker-compose.yml")

if package_exists "premium" || submodule_initialized "premium"; then
    COMPOSE_FILES+=("-f docker-compose.premium.yml")
fi

if package_exists "enterprise" || submodule_initialized "enterprise"; then
    COMPOSE_FILES+=("-f docker-compose.enterprise.yml")
fi

echo -e "${BLUE}📦 Detected compose files:${NC} ${COMPOSE_FILES[*]}"
echo ""

# Stop containers
echo -e "${BLUE}🐳 Stopping Docker containers...${NC}"
docker compose ${COMPOSE_FILES[@]} down

echo ""
echo -e "${RED}✅ All containers stopped!${NC}"
echo ""
