#!/bin/bash
# Import Path Validation Script
# Validates that Premium/Enterprise packages use correct import paths

set -e

echo "🔍 Validating import paths in Premium/Enterprise packages..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# Check for invalid import patterns in Premium
echo "Checking Premium package..."
PREMIUM_INVALID=$(grep -r "from '\.\./\.\./types" packages/premium/frontend/src --include="*.ts" --include="*.tsx" 2>/dev/null || true)

if [ -n "$PREMIUM_INVALID" ]; then
  echo -e "${RED}❌ Found invalid imports in Premium package:${NC}"
  echo "$PREMIUM_INVALID"
  echo -e "${YELLOW}Should use: import { X } from '../core/types/Y'${NC}"
  ERRORS=$((ERRORS + 1))
fi

# Check for invalid import patterns in Enterprise
echo "Checking Enterprise package..."
ENTERPRISE_INVALID=$(grep -r "from '\.\./\.\./types" packages/enterprise/frontend/src --include="*.ts" --include="*.tsx" 2>/dev/null || true)

if [ -n "$ENTERPRISE_INVALID" ]; then
  echo -e "${RED}❌ Found invalid imports in Enterprise package:${NC}"
  echo "$ENTERPRISE_INVALID"
  echo -e "${YELLOW}Should use: import { X } from '../core/types/Y'${NC}"
  ERRORS=$((ERRORS + 1))
fi

# Check for direct Core imports (should use @core alias if needed)
echo "Checking for direct Core imports..."
DIRECT_CORE=$(grep -r "from '\.\./\.\./\.\./\.\./core" packages/premium/frontend/src packages/enterprise/frontend/src --include="*.ts" --include="*.tsx" 2>/dev/null || true)

if [ -n "$DIRECT_CORE" ]; then
  echo -e "${RED}❌ Found direct Core imports (should use @core alias):${NC}"
  echo "$DIRECT_CORE"
  echo -e "${YELLOW}Should use: import { X } from '@core/types/Y'${NC}"
  ERRORS=$((ERRORS + 1))
fi

# Summary
if [ $ERRORS -eq 0 ]; then
  echo -e "${GREEN}✅ All import paths are valid!${NC}"
  exit 0
else
  echo -e "${RED}❌ Found $ERRORS import path issue(s)${NC}"
  echo ""
  echo "To fix automatically, run:"
  echo "  ./scripts/fix-imports.sh"
  exit 1
fi
