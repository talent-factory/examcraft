#!/bin/bash

# ExamCraft AI - Stop Development Environment
# Stoppt alle laufenden Container (Core oder Full)

set -e

# Farben für Output
RED='\033[0;31m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}🛑 Stopping ExamCraft AI Development Environment${NC}"
echo "=================================================="
echo ""

# Parse command line arguments
DEPLOYMENT_MODE="auto"
REMOVE_VOLUMES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --core)
            DEPLOYMENT_MODE="core"
            shift
            ;;
        --full)
            DEPLOYMENT_MODE="full"
            shift
            ;;
        -v|--volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Usage: ./stop-dev.sh [--core|--full] [-v|--volumes]"
            exit 1
            ;;
    esac
done

# Auto-detect deployment mode
if [ "$DEPLOYMENT_MODE" = "auto" ]; then
    if [ -f "docker-compose.full.yml" ]; then
        # Check if full stack is running
        if docker compose -f docker-compose.full.yml ps 2>/dev/null | grep -q "examcraft"; then
            DEPLOYMENT_MODE="full"
        else
            DEPLOYMENT_MODE="core"
        fi
    else
        DEPLOYMENT_MODE="core"
    fi
fi

DEPLOYMENT_MODE_UPPER=$(echo "$DEPLOYMENT_MODE" | tr '[:lower:]' '[:upper:]')
echo -e "${BLUE}📦 Deployment Mode:${NC} ${YELLOW}${DEPLOYMENT_MODE_UPPER}${NC}"
echo ""

# Stop containers based on deployment mode
echo -e "${BLUE}🐳 Stopping Docker containers...${NC}"

if [ "$DEPLOYMENT_MODE" = "full" ]; then
    if [ "$REMOVE_VOLUMES" = true ]; then
        docker compose --env-file .env -f docker-compose.full.yml down -v
        echo -e "${GREEN}✅ Full stack stopped and volumes removed!${NC}"
    else
        docker compose --env-file .env -f docker-compose.full.yml down
        echo -e "${GREEN}✅ Full stack stopped!${NC}"
    fi
else
    if [ "$REMOVE_VOLUMES" = true ]; then
        docker compose --env-file .env -f docker-compose.yml down -v
        echo -e "${GREEN}✅ Core stack stopped and volumes removed!${NC}"
    else
        docker compose --env-file .env -f docker-compose.yml down
        echo -e "${GREEN}✅ Core stack stopped!${NC}"
    fi
fi

echo ""
