#!/bin/bash

# ExamCraft AI - Frontend Cache Cleaner
# Clears Webpack/React build cache to fix stale module issues
# Use this when you encounter "Module not found" errors after git pull/branch switch

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🧹 ExamCraft AI - Frontend Cache Cleaner              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Parse arguments
CLEAN_ALL=false
REINSTALL=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --all)
      CLEAN_ALL=true
      shift
      ;;
    --reinstall)
      REINSTALL=true
      shift
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --all         Clean all packages (core, premium, enterprise)"
      echo "  --reinstall   Also reinstall node_modules"
      echo "  --help        Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                    # Clean core frontend cache only"
      echo "  $0 --all              # Clean all frontend caches"
      echo "  $0 --all --reinstall  # Clean everything and reinstall"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Function to clean a package
clean_package() {
    local package_path=$1
    local package_name=$2

    if [ ! -d "$package_path" ]; then
        echo -e "${YELLOW}⚠️  Skipping $package_name (not found)${NC}"
        return
    fi

    echo -e "${BLUE}🧹 Cleaning $package_name...${NC}"

    # Remove Webpack cache
    if [ -d "$package_path/node_modules/.cache" ]; then
        rm -rf "$package_path/node_modules/.cache"
        echo "  ✅ Removed Webpack cache"
    fi

    # Remove build artifacts
    if [ -d "$package_path/build" ]; then
        rm -rf "$package_path/build"
        echo "  ✅ Removed build directory"
    fi

    # Remove TypeScript cache
    if [ -f "$package_path/tsconfig.tsbuildinfo" ]; then
        rm -f "$package_path/tsconfig.tsbuildinfo"
        echo "  ✅ Removed TypeScript cache"
    fi

    # Remove node_modules if --reinstall
    if [ "$REINSTALL" = true ] && [ -d "$package_path/node_modules" ]; then
        rm -rf "$package_path/node_modules"
        echo "  ✅ Removed node_modules"
    fi

    echo ""
}

# Clean Core package (always)
clean_package "packages/core/frontend" "Core Frontend"

# Clean Premium/Enterprise if --all
if [ "$CLEAN_ALL" = true ]; then
    clean_package "packages/premium/frontend" "Premium Frontend"
    clean_package "packages/enterprise/frontend" "Enterprise Frontend"
fi

# Clean root node_modules if --reinstall
if [ "$REINSTALL" = true ]; then
    echo -e "${BLUE}🧹 Cleaning root workspace...${NC}"
    if [ -d "node_modules" ]; then
        rm -rf node_modules
        echo "  ✅ Removed root node_modules"
    fi
    echo ""
fi

# Reinstall if requested
if [ "$REINSTALL" = true ]; then
    echo -e "${BLUE}📦 Reinstalling dependencies...${NC}"

    # Check if bun is available
    if command -v bun &> /dev/null; then
        echo "  Using Bun..."
        bun install
    else
        echo "  Using npm..."
        npm install
    fi

    echo ""
fi

echo -e "${GREEN}$(printf '=%.0s' {1..60})${NC}"
echo -e "${GREEN}✅ Frontend cache cleaned successfully!${NC}"
echo -e "${GREEN}$(printf '=%.0s' {1..60})${NC}"
echo ""
echo -e "${BLUE}💡 Next steps:${NC}"
echo "   1. Restart your frontend dev server"
echo "   2. If using Docker: docker compose restart frontend"
echo ""

if [ "$REINSTALL" = false ]; then
    echo -e "${YELLOW}ℹ️  Tip: Use --reinstall to also reinstall node_modules${NC}"
    echo ""
fi
