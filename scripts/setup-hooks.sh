#!/bin/bash
# Setup Pre-commit Hooks for ExamCraft AI

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ExamCraft AI - Pre-commit Hooks Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}[ERROR]${NC} uv is not installed!"
    echo -e "${YELLOW}[INFO]${NC} Please install uv first: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo -e "${YELLOW}[INFO]${NC} Installing pre-commit with uv..."
    uv tool install pre-commit
fi

# Install pre-commit hooks
echo -e "${BLUE}[INFO]${NC} Installing pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# Run pre-commit on all files (optional)
echo ""
echo -e "${BLUE}[INFO]${NC} Running pre-commit on all files..."
pre-commit run --all-files || true

echo ""
echo -e "${GREEN}[SUCCESS]${NC} Pre-commit hooks installed successfully!"
echo ""
echo -e "${BLUE}Usage:${NC}"
echo "  - Hooks will run automatically on 'git commit'"
echo "  - To run manually: pre-commit run --all-files"
echo "  - To skip hooks: git commit --no-verify"
echo ""
