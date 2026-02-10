#!/bin/bash

# ============================================================================
# ExamCraft AI - GUI Modernization Deployment Script
# ============================================================================
# This script deploys the GUI modernization feature (TF-148) to Docker
# for testing and development.
#
# Usage:
#   ./scripts/deploy-gui-modernization.sh [options]
#
# Options:
#   --port-frontend PORT    Frontend port (default: 3000)
#   --port-backend PORT     Backend port (default: 8000)
#   --build                 Force rebuild of Docker images
#   --logs                  Show logs after startup
#   --help                  Show this help message
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
FRONTEND_PORT=3000
BACKEND_PORT=8000
BUILD=false
SHOW_LOGS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port-frontend)
      FRONTEND_PORT="$2"
      shift 2
      ;;
    --port-backend)
      BACKEND_PORT="$2"
      shift 2
      ;;
    --build)
      BUILD=true
      shift
      ;;
    --logs)
      SHOW_LOGS=true
      shift
      ;;
    --help)
      grep "^#" "$0" | grep -v "^#!/bin/bash"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Print header
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ExamCraft AI - GUI Modernization Deployment (TF-148)     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
  echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
  cp .env.example .env
  echo -e "${GREEN}✅ .env file created. Please update with your API keys if needed.${NC}"
  echo ""
fi

# Set environment variables
export FRONTEND_PORT=$FRONTEND_PORT
export BACKEND_PORT=$BACKEND_PORT

echo -e "${BLUE}📋 Configuration:${NC}"
echo "   Frontend Port: $FRONTEND_PORT"
echo "   Backend Port:  $BACKEND_PORT"
echo "   Build Images:  $([ "$BUILD" = true ] && echo 'Yes' || echo 'No')"
echo ""

# Build images if requested
if [ "$BUILD" = true ]; then
  echo -e "${BLUE}🔨 Building Docker images...${NC}"
  docker-compose build --no-cache
  echo -e "${GREEN}✅ Docker images built successfully${NC}"
  echo ""
fi

# Start containers
echo -e "${BLUE}🚀 Starting Docker containers...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 5

# Check if services are running
echo -e "${BLUE}🔍 Checking service status...${NC}"

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U examcraft > /dev/null 2>&1; then
  echo -e "${GREEN}✅ PostgreSQL is running${NC}"
else
  echo -e "${RED}❌ PostgreSQL failed to start${NC}"
  exit 1
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Redis is running${NC}"
else
  echo -e "${RED}❌ Redis failed to start${NC}"
  exit 1
fi

# Check Qdrant
if curl -s http://localhost:6333/health > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Qdrant is running${NC}"
else
  echo -e "${RED}❌ Qdrant failed to start${NC}"
  exit 1
fi

# Check Backend
if curl -s http://localhost:$BACKEND_PORT/docs > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Backend is running${NC}"
else
  echo -e "${YELLOW}⏳ Backend is starting... (this may take a moment)${NC}"
  sleep 10
fi

# Check Frontend
if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Frontend is running${NC}"
else
  echo -e "${YELLOW}⏳ Frontend is starting... (this may take a moment)${NC}"
  sleep 10
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🎉 Deployment successful!                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📱 Access the application:${NC}"
echo "   Frontend:  ${YELLOW}http://localhost:$FRONTEND_PORT${NC}"
echo "   Backend:   ${YELLOW}http://localhost:$BACKEND_PORT${NC}"
echo "   API Docs:  ${YELLOW}http://localhost:$BACKEND_PORT/docs${NC}"
echo "   Qdrant:    ${YELLOW}http://localhost:6333/dashboard${NC}"
echo ""

echo -e "${BLUE}📊 Useful commands:${NC}"
echo "   View logs:     ${YELLOW}docker-compose logs -f${NC}"
echo "   Stop services: ${YELLOW}docker-compose down${NC}"
echo "   Restart:       ${YELLOW}docker-compose restart${NC}"
echo ""

# Show logs if requested
if [ "$SHOW_LOGS" = true ]; then
  echo -e "${BLUE}📋 Showing logs (Ctrl+C to exit)...${NC}"
  docker-compose logs -f
fi
