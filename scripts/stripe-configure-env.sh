#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "🔧 ExamCraft AI - Stripe Configuration"
echo "=========================================="
echo ""

ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    exit 1
fi

echo -e "${BLUE}This script will update your .env with Stripe configuration.${NC}"
echo ""
echo -e "${YELLOW}You need:${NC}"
echo "  1. Stripe Secret Key (sk_test_...)"
echo "     → https://dashboard.stripe.com/test/apikeys"
echo ""
echo "  2. Stripe Webhook Secret (whsec_...)"
echo "     → You mentioned you already have this"
echo ""
echo "  3. Starter Plan Price ID (price_...)"
echo "     → https://dashboard.stripe.com/test/products"
echo ""
echo "  4. Professional Plan Price ID (price_...)"
echo "     → https://dashboard.stripe.com/test/products"
echo ""
read -p "Press Enter to continue..."
echo ""

# 1. Stripe Secret Key
echo "=========================================="
echo "1. Stripe Secret Key"
echo "=========================================="
echo ""
echo -e "${YELLOW}Go to: https://dashboard.stripe.com/test/apikeys${NC}"
echo "Click 'Reveal test key' next to 'Secret key'"
echo ""
read -p "Enter your Stripe Secret Key (sk_test_...): " STRIPE_SECRET_KEY

if [[ ! "$STRIPE_SECRET_KEY" =~ ^sk_test_ ]]; then
    echo -e "${RED}⚠️  Warning: Key should start with 'sk_test_'${NC}"
    read -p "Continue anyway? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
fi

# 2. Webhook Secret
echo ""
echo "=========================================="
echo "2. Stripe Webhook Secret"
echo "=========================================="
echo ""
echo -e "${YELLOW}You mentioned you already have this (whsec_...)${NC}"
echo ""
read -p "Enter your Stripe Webhook Secret (whsec_...): " STRIPE_WEBHOOK_SECRET

if [[ ! "$STRIPE_WEBHOOK_SECRET" =~ ^whsec_ ]]; then
    echo -e "${RED}⚠️  Warning: Secret should start with 'whsec_'${NC}"
    read -p "Continue anyway? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
fi

# 3. Starter Price ID
echo ""
echo "=========================================="
echo "3. Starter Plan Price ID"
echo "=========================================="
echo ""
echo -e "${YELLOW}Go to: https://dashboard.stripe.com/test/products${NC}"
echo "Click on your 'Starter' or '€19/month' product"
echo "Copy the Price ID (starts with 'price_')"
echo ""
read -p "Enter Starter Price ID (price_...): " STARTER_PRICE_ID

if [[ ! "$STARTER_PRICE_ID" =~ ^price_ ]]; then
    echo -e "${RED}⚠️  Warning: Price ID should start with 'price_'${NC}"
    read -p "Continue anyway? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
fi

# 4. Professional Price ID
echo ""
echo "=========================================="
echo "4. Professional Plan Price ID"
echo "=========================================="
echo ""
echo -e "${YELLOW}Go to: https://dashboard.stripe.com/test/products${NC}"
echo "Click on your 'Professional' or '€149/month' product"
echo "Copy the Price ID (starts with 'price_')"
echo ""
read -p "Enter Professional Price ID (price_...): " PROFESSIONAL_PRICE_ID

if [[ ! "$PROFESSIONAL_PRICE_ID" =~ ^price_ ]]; then
    echo -e "${RED}⚠️  Warning: Price ID should start with 'price_'${NC}"
    read -p "Continue anyway? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
fi

# Update .env
echo ""
echo "=========================================="
echo "Updating .env..."
echo "=========================================="
echo ""

# Backup .env
cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}✅ Created backup of .env${NC}"

# Update STRIPE_SECRET_KEY
sed -i.tmp "s|STRIPE_SECRET_KEY=.*|STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY|" "$ENV_FILE"
echo -e "${GREEN}✅ Updated STRIPE_SECRET_KEY${NC}"

# Update STRIPE_WEBHOOK_SECRET
sed -i.tmp "s|STRIPE_WEBHOOK_SECRET=.*|STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET|" "$ENV_FILE"
echo -e "${GREEN}✅ Updated STRIPE_WEBHOOK_SECRET${NC}"

# Update Price IDs
sed -i.tmp "s|REACT_APP_STRIPE_PRICE_STARTER=.*|REACT_APP_STRIPE_PRICE_STARTER=$STARTER_PRICE_ID|" "$ENV_FILE"
echo -e "${GREEN}✅ Updated REACT_APP_STRIPE_PRICE_STARTER${NC}"

sed -i.tmp "s|REACT_APP_STRIPE_PRICE_PROFESSIONAL=.*|REACT_APP_STRIPE_PRICE_PROFESSIONAL=$PROFESSIONAL_PRICE_ID|" "$ENV_FILE"
echo -e "${GREEN}✅ Updated REACT_APP_STRIPE_PRICE_PROFESSIONAL${NC}"

# Clean up temp files
rm -f "$ENV_FILE.tmp"

echo ""
echo "=========================================="
echo "✅ Configuration Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}Your Stripe configuration:${NC}"
echo "  • Secret Key:     ${STRIPE_SECRET_KEY:0:15}..."
echo "  • Webhook Secret: ${STRIPE_WEBHOOK_SECRET:0:15}..."
echo "  • Starter Plan:   $STARTER_PRICE_ID"
echo "  • Professional:   $PROFESSIONAL_PRICE_ID"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Restart Backend:"
echo "   docker compose --env-file .env -f docker-compose.full.yml restart backend"
echo ""
echo "2. Restart Frontend:"
echo "   cd packages/core/frontend && bun start"
echo ""
echo "3. Test at:"
echo "   http://localhost:3000/billing"
echo ""
echo -e "${YELLOW}Note: The webhook secret will only work if you run:${NC}"
echo "   stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe"
echo ""
