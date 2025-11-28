#!/bin/bash

# Setup Premium Component Symlinks for Full Deployment
# Creates symlinks from Core frontend to Premium components to allow CRA imports

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

CORE_FRONTEND_SRC="packages/core/frontend/src"
PREMIUM_FRONTEND_SRC="packages/premium/frontend/src"

echo -e "${BLUE}🔗 Setting up Premium component symlinks...${NC}"

# Check if Premium package exists
if [ ! -d "$PREMIUM_FRONTEND_SRC" ]; then
    echo -e "${YELLOW}⚠️  Premium package not found, skipping symlink setup${NC}"
    exit 0
fi

# Create premium stub directory structure if it doesn't exist
mkdir -p "$CORE_FRONTEND_SRC/premium/components/DocumentChat"

# Remove existing file or symlink if it exists (to allow re-linking)
TARGET_FILE="$CORE_FRONTEND_SRC/premium/components/DocumentChat/DocumentChatPage.tsx"
if [ -e "$TARGET_FILE" ] || [ -L "$TARGET_FILE" ]; then
    rm -f "$TARGET_FILE"
    echo "  ↻ Removed existing file/symlink"
fi

# Create symlink to Premium DocumentChat component
if [ -f "$PREMIUM_FRONTEND_SRC/components/DocumentChat/DocumentChatPage.tsx" ]; then
    # Use relative path for symlink
    cd "$CORE_FRONTEND_SRC/premium/components/DocumentChat"
    ln -sf "../../../../../../premium/frontend/src/components/DocumentChat/DocumentChatPage.tsx" "DocumentChatPage.tsx"
    cd - > /dev/null
    echo -e "${GREEN}  ✅ Linked Premium DocumentChatPage${NC}"
else
    echo -e "${YELLOW}  ⚠️  Premium DocumentChatPage not found, keeping stub${NC}"
fi

# TODO: Add more Premium component symlinks here as needed
# Example:
# if [ -f "$PREMIUM_FRONTEND_SRC/components/RAGExamCreator.tsx" ]; then
#     mkdir -p "$CORE_FRONTEND_SRC/premium/components"
#     ln -sf "../../../$PREMIUM_FRONTEND_SRC/components/RAGExamCreator.tsx" \
#            "$CORE_FRONTEND_SRC/premium/components/RAGExamCreator.tsx"
#     echo -e "${GREEN}  ✅ Linked Premium RAGExamCreator${NC}"
# fi

echo -e "${GREEN}✅ Premium symlinks setup complete${NC}"
