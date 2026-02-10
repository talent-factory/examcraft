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

# 3. Frontend: package-lock.json Sync Check
echo ""
echo "🔗 Checking package-lock.json sync..."
cd packages/core/frontend

# Temporarily hide root package.json to avoid workspace conflicts
if [ -f ../../../package.json ]; then
    mv ../../../package.json ../../../package.json.tmp
fi

# Check if package-lock.json is in sync
npm install --package-lock-only --legacy-peer-deps 2>/dev/null
LOCK_CHANGES=$(git diff --name-only package-lock.json 2>/dev/null || true)

# Restore root package.json
if [ -f ../../../package.json.tmp ]; then
    mv ../../../package.json.tmp ../../../package.json
fi

if [ -z "$LOCK_CHANGES" ]; then
    echo -e "${GREEN}✅ package-lock.json: IN SYNC${NC}"
else
    echo -e "${RED}❌ package-lock.json: OUT OF SYNC${NC}"
    echo -e "${YELLOW}💡 Fix: Run the following commands:${NC}"
    echo -e "${YELLOW}   mv package.json package.json.bak${NC}"
    echo -e "${YELLOW}   cd packages/core/frontend && npm install --legacy-peer-deps${NC}"
    echo -e "${YELLOW}   cd ../../.. && mv package.json.bak package.json${NC}"
    echo -e "${YELLOW}   git add packages/core/frontend/package-lock.json && git commit --amend --no-edit${NC}"
    git checkout package-lock.json 2>/dev/null || true
    ERRORS=$((ERRORS + 1))
fi

cd ../../..

# 4. Frontend: ESLint (optional, da oft Warnings)
echo ""
echo "🎨 Checking Frontend (ESLint)..."
cd packages/core/frontend

if npm run lint --silent 2>/dev/null; then
    echo -e "${GREEN}✅ ESLint: PASSED${NC}"
else
    echo -e "${YELLOW}⚠️  ESLint: WARNINGS (continuing)${NC}"
    echo -e "${YELLOW}💡 Fix with: cd packages/core/frontend && npm run lint:fix${NC}"
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
    echo "   cd packages/core/frontend && npm run lint:fix"
    echo "   pre-commit run --all-files"
    echo ""
    echo "Then commit and push again."
    exit 1
fi
