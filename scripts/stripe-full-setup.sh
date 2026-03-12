#!/bin/bash
set -e

echo "=========================================="
echo "🚀 ExamCraft AI - Complete Stripe Setup"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo -e "${RED}❌ Error: Stripe CLI is not installed${NC}"
    echo "Install: https://stripe.com/docs/stripe-cli"
    exit 1
fi

# Check if logged in
if ! stripe config --list &> /dev/null; then
    echo -e "${RED}❌ Error: Not logged in to Stripe CLI${NC}"
    echo "Run: stripe login"
    exit 1
fi

echo -e "${GREEN}✅ Stripe CLI detected and logged in${NC}"
echo ""

ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    exit 1
fi

# Step 1: Check and add STRIPE_SECRET_KEY
echo "=========================================="
echo "Step 1: Stripe Secret Key"
echo "=========================================="
echo ""

if grep -q "^STRIPE_SECRET_KEY=" "$ENV_FILE"; then
    EXISTING_KEY=$(grep "^STRIPE_SECRET_KEY=" "$ENV_FILE" | cut -d= -f2)
    if [[ "$EXISTING_KEY" == sk_test_* ]]; then
        echo -e "${GREEN}✅ STRIPE_SECRET_KEY already configured${NC}"
        STRIPE_SECRET_KEY="$EXISTING_KEY"
    else
        echo -e "${YELLOW}⚠️  STRIPE_SECRET_KEY found but invalid format${NC}"
        read -p "Enter your Stripe Secret Key (sk_test_...): " STRIPE_SECRET_KEY
        sed -i.bak "s|^STRIPE_SECRET_KEY=.*|STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY|" "$ENV_FILE"
        echo -e "${GREEN}✅ Updated STRIPE_SECRET_KEY${NC}"
    fi
else
    echo "STRIPE_SECRET_KEY not found in .env"
    read -p "Enter your Stripe Secret Key (sk_test_...): " STRIPE_SECRET_KEY
    echo "" >> "$ENV_FILE"
    echo "# Stripe Configuration" >> "$ENV_FILE"
    echo "STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY" >> "$ENV_FILE"
    echo -e "${GREEN}✅ Added STRIPE_SECRET_KEY${NC}"
fi

echo ""

# Step 2: Create Products and Prices
echo "=========================================="
echo "Step 2: Creating Stripe Products"
echo "=========================================="
echo ""

create_product() {
    local name=$1
    local description=$2
    local price=$3

    echo "Creating: $name (€$(($price / 100))/month)..."

    # Create product
    PRODUCT_JSON=$(stripe products create \
        --name="$name" \
        --description="$description" \
        --format=json 2>&1)

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to create product${NC}"
        echo "$PRODUCT_JSON"
        exit 1
    fi

    PRODUCT_ID=$(echo "$PRODUCT_JSON" | grep -o '"id": *"[^"]*"' | head -1 | sed 's/"id": *"\(.*\)"/\1/')

    # Create price
    PRICE_JSON=$(stripe prices create \
        --product="$PRODUCT_ID" \
        --unit-amount="$price" \
        --currency=eur \
        --recurring='{"interval":"month"}' \
        --format=json 2>&1)

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to create price${NC}"
        echo "$PRICE_JSON"
        exit 1
    fi

    PRICE_ID=$(echo "$PRICE_JSON" | grep -o '"id": *"[^"]*"' | head -1 | sed 's/"id": *"\(.*\)"/\1/')

    echo -e "  ${GREEN}✅ Price ID: $PRICE_ID${NC}"
    echo ""

    echo "$PRICE_ID"
}

# Create Starter Plan (€19/month)
STARTER_PRICE_ID=$(create_product \
    "ExamCraft Starter" \
    "For serious exam creators" \
    "1900")

# Create Professional Plan (€149/month)
PROFESSIONAL_PRICE_ID=$(create_product \
    "ExamCraft Professional" \
    "Unlimited power for professional exam creation" \
    "14900")

# Step 3: Update .env with Price IDs
echo "=========================================="
echo "Step 3: Updating .env with Price IDs"
echo "=========================================="
echo ""

if grep -q "REACT_APP_STRIPE_PRICE_STARTER=" "$ENV_FILE"; then
    sed -i.bak "s|REACT_APP_STRIPE_PRICE_STARTER=.*|REACT_APP_STRIPE_PRICE_STARTER=$STARTER_PRICE_ID|" "$ENV_FILE"
    echo -e "${GREEN}✅ Updated REACT_APP_STRIPE_PRICE_STARTER${NC}"
else
    echo "REACT_APP_STRIPE_PRICE_STARTER=$STARTER_PRICE_ID" >> "$ENV_FILE"
    echo -e "${GREEN}✅ Added REACT_APP_STRIPE_PRICE_STARTER${NC}"
fi

if grep -q "REACT_APP_STRIPE_PRICE_PROFESSIONAL=" "$ENV_FILE"; then
    sed -i.bak "s|REACT_APP_STRIPE_PRICE_PROFESSIONAL=.*|REACT_APP_STRIPE_PRICE_PROFESSIONAL=$PROFESSIONAL_PRICE_ID|" "$ENV_FILE"
    echo -e "${GREEN}✅ Updated REACT_APP_STRIPE_PRICE_PROFESSIONAL${NC}"
else
    echo "REACT_APP_STRIPE_PRICE_PROFESSIONAL=$PROFESSIONAL_PRICE_ID" >> "$ENV_FILE"
    echo -e "${GREEN}✅ Added REACT_APP_STRIPE_PRICE_PROFESSIONAL${NC}"
fi

# Clean up backup
rm -f "$ENV_FILE.bak"

echo ""

# Step 4: Setup Webhook Secret
echo "=========================================="
echo "Step 4: Webhook Secret Setup"
echo "=========================================="
echo ""

if grep -q "^STRIPE_WEBHOOK_SECRET=" "$ENV_FILE"; then
    EXISTING_WEBHOOK=$(grep "^STRIPE_WEBHOOK_SECRET=" "$ENV_FILE" | cut -d= -f2)
    if [[ "$EXISTING_WEBHOOK" == whsec_* ]]; then
        echo -e "${GREEN}✅ STRIPE_WEBHOOK_SECRET already configured${NC}"
    else
        echo -e "${YELLOW}⚠️  STRIPE_WEBHOOK_SECRET found but invalid format${NC}"
        read -p "Enter your Stripe Webhook Secret (whsec_...): " WEBHOOK_SECRET
        sed -i.bak "s|^STRIPE_WEBHOOK_SECRET=.*|STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET|" "$ENV_FILE"
        echo -e "${GREEN}✅ Updated STRIPE_WEBHOOK_SECRET${NC}"
        rm -f "$ENV_FILE.bak"
    fi
else
    echo "STRIPE_WEBHOOK_SECRET not found in .env"
    read -p "Enter your Stripe Webhook Secret (whsec_...): " WEBHOOK_SECRET
    echo "STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET" >> "$ENV_FILE"
    echo -e "${GREEN}✅ Added STRIPE_WEBHOOK_SECRET${NC}"
fi

echo ""

# Summary
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Configuration Summary:"
echo "  • Starter Plan:      $STARTER_PRICE_ID (€19/month)"
echo "  • Professional Plan: $PROFESSIONAL_PRICE_ID (€149/month)"
echo ""
echo "Next Steps:"
echo "  1. Restart backend:  docker compose --env-file .env -f docker-compose.full.yml restart backend"
echo "  2. Restart frontend: cd packages/core/frontend && npm start"
echo "  3. Test at:          http://localhost:3000/billing"
echo ""
echo "To forward webhooks locally, run:"
echo "  ./scripts/stripe-webhook-test.sh"
echo ""
