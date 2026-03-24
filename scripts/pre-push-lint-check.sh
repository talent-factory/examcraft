#!/bin/bash
# Pre-Push Lint Check Script
# Führt Lint-Checks aus BEVOR Code gepusht wird

set -e  # Exit on error

echo "🔍 Running Pre-Push Lint Checks..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track errors
ERRORS=0

# 1. Backend: Ruff Linter
echo "📦 Checking Backend (Ruff)..."
cd packages/core/backend

if ruff check . --quiet; then
    echo -e "${GREEN}✅ Ruff Linter: PASSED${NC}"
else
    echo -e "${RED}❌ Ruff Linter: FAILED${NC}"
    echo -e "${YELLOW}💡 Fix with: cd packages/core/backend && ruff check . --fix${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 2. Backend: Ruff Formatter
if ruff format --check . --quiet; then
    echo -e "${GREEN}✅ Ruff Formatter: PASSED${NC}"
else
    echo -e "${RED}❌ Ruff Formatter: FAILED${NC}"
    echo -e "${YELLOW}💡 Fix with: cd packages/core/backend && ruff format .${NC}"
    ERRORS=$((ERRORS + 1))
fi

cd ../../..

# 3. Frontend: ESLint (optional, da oft Warnings)
echo ""
echo "🎨 Checking Frontend (ESLint)..."
cd packages/core/frontend

if bun run lint --silent 2>/dev/null; then
    echo -e "${GREEN}✅ ESLint: PASSED${NC}"
else
    echo -e "${YELLOW}⚠️  ESLint: WARNINGS (continuing)${NC}"
    echo -e "${YELLOW}💡 Fix with: cd packages/core/frontend && bun run lint:fix${NC}"
    # Don't count as error, just warning
fi

cd ../../..

# 4. Pre-Commit-Hooks (alle Dateien)
echo ""
echo "🔧 Running Pre-Commit Hooks..."

if pre-commit run --all-files --show-diff-on-failure; then
    echo -e "${GREEN}✅ Pre-Commit Hooks: PASSED${NC}"
else
    echo -e "${RED}❌ Pre-Commit Hooks: FAILED${NC}"
    echo -e "${YELLOW}💡 Fix with: pre-commit run --all-files${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All Lint Checks PASSED!${NC}"
    echo "================================"
    exit 0
else
    echo -e "${RED}❌ $ERRORS Lint Check(s) FAILED!${NC}"
    echo "================================"
    echo ""
    echo "🛠️  Quick Fix Commands:"
    echo "   cd packages/core/backend && ruff check . --fix && ruff format ."
    echo "   cd packages/core/frontend && bun run lint:fix"
    echo "   pre-commit run --all-files"
    echo ""
    echo "Then commit and push again."
    exit 1
fi
