#!/bin/bash
# Import Migration Script for Option 5
# Migrates imports from relative paths to @examcraft/core

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

if [ -z "$1" ]; then
  echo -e "${RED}Usage: $0 <directory>${NC}"
  echo "Example: $0 packages/premium/frontend/src"
  exit 1
fi

TARGET_DIR="$1"

if [ ! -d "$TARGET_DIR" ]; then
  echo -e "${RED}Error: Directory $TARGET_DIR does not exist${NC}"
  exit 1
fi

echo -e "${GREEN}🔄 Migrating imports in $TARGET_DIR${NC}"
echo ""

# Counter
TOTAL_FILES=0
MODIFIED_FILES=0

# Find all TypeScript files
while IFS= read -r file; do
  TOTAL_FILES=$((TOTAL_FILES + 1))
  MODIFIED=false

  # Create backup
  cp "$file" "$file.bak"

  # Migrate imports
  # Pattern 1: ../core/types/X → @examcraft/core/types/X
  if sed -i '' "s|from ['\"]\\.\\.\/core\/types\/\([^'\"]*\)['\"]|from '@examcraft/core/types/\1'|g" "$file"; then
    MODIFIED=true
  fi

  # Pattern 2: ../core/services/X → @examcraft/core/services/X
  if sed -i '' "s|from ['\"]\\.\\.\/core\/services\/\([^'\"]*\)['\"]|from '@examcraft/core/services/\1'|g" "$file"; then
    MODIFIED=true
  fi

  # Pattern 3: ../core/components/X → @examcraft/core/components/X
  if sed -i '' "s|from ['\"]\\.\\.\/core\/components\/\([^'\"]*\)['\"]|from '@examcraft/core/components/\1'|g" "$file"; then
    MODIFIED=true
  fi

  # Pattern 4: ../core/contexts/X → @examcraft/core/contexts/X
  if sed -i '' "s|from ['\"]\\.\\.\/core\/contexts\/\([^'\"]*\)['\"]|from '@examcraft/core/contexts/\1'|g" "$file"; then
    MODIFIED=true
  fi

  # Pattern 5: ../core/utils/X → @examcraft/core/utils/X
  if sed -i '' "s|from ['\"]\\.\\.\/core\/utils\/\([^'\"]*\)['\"]|from '@examcraft/core/utils/\1'|g" "$file"; then
    MODIFIED=true
  fi

  # Check if file was modified
  if ! cmp -s "$file" "$file.bak"; then
    MODIFIED_FILES=$((MODIFIED_FILES + 1))
    echo -e "${YELLOW}✏️  Modified: $file${NC}"
  fi

  # Remove backup
  rm "$file.bak"

done < <(find "$TARGET_DIR" -type f \( -name "*.ts" -o -name "*.tsx" \) ! -path "*/node_modules/*")

echo ""
echo -e "${GREEN}✅ Migration complete!${NC}"
echo "Total files scanned: $TOTAL_FILES"
echo "Files modified: $MODIFIED_FILES"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review changes: git diff"
echo "2. Run TypeScript: npm run build"
echo "3. Run tests: npm test"
echo "4. Remove core/ directory: rm -rf $TARGET_DIR/core"
