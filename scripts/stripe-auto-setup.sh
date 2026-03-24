#!/bin/bash
set -e

echo "=========================================="
echo "🚀 ExamCraft AI - Automated Stripe Setup"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Function to create a product and price
create_product() {
    local name=$1
    local description=$2
    local price=$3

    echo -e "${BLUE}Creating: $name (€$(($price / 100))/month)...${NC}"

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

echo "=========================================="
echo "Step 1: Creating Stripe Products"
echo "=========================================="
echo ""

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

echo "=========================================="
echo "Step 2: Updating .env with Price IDs"
echo "=========================================="
echo ""

# Update .env with Price IDs
if grep -q "REACT_APP_STRIPE_PRICE_STARTER=" "$ENV_FILE"; then
    # Update existing (use | as delimiter to avoid conflicts with /)
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
echo "=========================================="
echo "✅ Stripe Products Setup Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}Products Created:${NC}"
echo "  • ExamCraft Starter:      €19/month  → $STARTER_PRICE_ID"
echo "  • ExamCraft Professional: €149/month → $PROFESSIONAL_PRICE_ID"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: You still need to configure your API keys!${NC}"
echo ""
echo -e "${BLUE}Edit .env and replace:${NC}"
echo "  1. STRIPE_SECRET_KEY=YOUR_STRIPE_SECRET_KEY_HERE"
echo "     → Get from: https://dashboard.stripe.com/test/apikeys"
echo ""
echo "  2. STRIPE_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET_HERE"
echo "     → Run: ./scripts/stripe-webhook-test.sh"
echo "     → Copy the webhook secret from the output"
echo ""
echo -e "${BLUE}Then restart services:${NC}"
echo "  ./start-dev.sh --full"
echo ""
echo -e "${BLUE}Finally, test at:${NC}"
echo "  http://localhost:3000/billing"
echo ""
