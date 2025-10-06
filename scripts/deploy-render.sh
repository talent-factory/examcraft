#!/bin/bash

# ExamCraft AI - Render.com Deployment Script
# Automatisiert Pre-Deployment Checks und Deployment-Vorbereitung

set -e  # Exit on error

echo "🚀 ExamCraft AI - Render.com Deployment Preparation"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Check if we're in the right directory
if [ ! -f "render.yaml" ]; then
    print_error "render.yaml not found. Are you in the project root?"
    exit 1
fi

print_success "Found render.yaml"

# Check Git status
echo ""
print_info "Checking Git status..."
if [ -n "$(git status --porcelain)" ]; then
    print_warning "You have uncommitted changes:"
    git status --short
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "Working directory clean"
fi

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)
print_info "Current branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "develop" ]; then
    print_warning "You're not on main or develop branch"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run tests
echo ""
print_info "Running backend tests..."
cd backend
if pytest tests/ -v --tb=short; then
    print_success "Backend tests passed"
else
    print_error "Backend tests failed"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
cd ..

# Check frontend build
echo ""
print_info "Testing frontend build..."
cd frontend
if npm run build; then
    print_success "Frontend build successful"
else
    print_error "Frontend build failed"
    exit 1
fi
cd ..

# Check environment variables
echo ""
print_info "Checking required environment variables..."

REQUIRED_VARS=(
    "CLAUDE_API_KEY"
    "QDRANT_URL"
)

MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    print_warning "The following environment variables are not set locally:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    print_info "Make sure to set these in Render.com Dashboard!"
else
    print_success "All required environment variables are set"
fi

# Check render.yaml syntax
echo ""
print_info "Validating render.yaml..."
if python3 -c "import yaml; yaml.safe_load(open('render.yaml'))" 2>/dev/null; then
    print_success "render.yaml is valid YAML"
else
    print_error "render.yaml has syntax errors"
    exit 1
fi

# Generate deployment checklist
echo ""
echo "=================================================="
echo "📋 Pre-Deployment Checklist"
echo "=================================================="
echo ""
echo "Before deploying to Render.com, ensure:"
echo ""
echo "1. ✅ Code is committed and pushed to Git"
echo "2. ✅ Tests are passing"
echo "3. ✅ Frontend builds successfully"
echo "4. ✅ render.yaml is valid"
echo ""
echo "In Render.com Dashboard, configure:"
echo ""
echo "Backend Service Environment Variables:"
echo "  - CLAUDE_API_KEY (from Anthropic)"
echo "  - QDRANT_URL (from Qdrant Cloud)"
echo "  - QDRANT_API_KEY (optional, if using Qdrant Cloud)"
echo ""
echo "Frontend Service Environment Variables:"
echo "  - REACT_APP_API_URL (auto-set from backend service)"
echo ""
echo "=================================================="
echo ""

# Ask if user wants to push
read -p "Push current branch to remote? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Pushing to remote..."
    git push origin "$CURRENT_BRANCH"
    print_success "Pushed to origin/$CURRENT_BRANCH"
    echo ""
    print_info "Render.com will automatically deploy if auto-deploy is enabled"
fi

echo ""
print_success "Deployment preparation complete!"
echo ""
print_info "Next steps:"
echo "1. Go to Render.com Dashboard"
echo "2. Create new Blueprint or manual services"
echo "3. Configure environment variables"
echo "4. Monitor deployment logs"
echo ""
print_info "Useful Render.com URLs:"
echo "  - Dashboard: https://dashboard.render.com"
echo "  - Docs: https://render.com/docs"
echo ""

