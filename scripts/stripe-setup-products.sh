#!/bin/bash
set -e

echo "=========================================="
echo "ExamCraft AI - Stripe Products Setup"
echo "=========================================="
echo ""

# Check if Stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo "❌ Error: Stripe CLI is not installed"
    echo "Install: https://stripe.com/docs/stripe-cli"
    exit 1
fi

# Check if logged in
if ! stripe config --list &> /dev/null; then
    echo "❌ Error: Not logged in to Stripe CLI"
    echo "Run: stripe login"
    exit 1
fi

echo "✅ Stripe CLI detected and logged in"
echo ""

# Function to create a product and price
create_product() {
    local name=$1
    local description=$2
    local price=$3

    echo "Creating product: $name..."

    # Create product
    PRODUCT_JSON=$(stripe products create \
        --name="$name" \
        --description="$description" \
        --format=json)

    PRODUCT_ID=$(echo "$PRODUCT_JSON" | grep -o '"id": *"[^"]*"' | head -1 | sed 's/"id": *"\(.*\)"/\1/')

    # Create price
    PRICE_JSON=$(stripe prices create \
        --product="$PRODUCT_ID" \
        --unit-amount="$price" \
        --currency=eur \
        --recurring='{"interval":"month"}' \
        --format=json)

    PRICE_ID=$(echo "$PRICE_JSON" | grep -o '"id": *"[^"]*"' | head -1 | sed 's/"id": *"\(.*\)"/\1/')

    echo "  Product ID: $PRODUCT_ID"
    echo "  Price ID: $PRICE_ID"
    echo ""

    echo "$PRICE_ID"
}

echo "=========================================="
echo "Creating Stripe Products..."
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
echo "✅ Products Created Successfully!"
echo "=========================================="
echo ""
echo "Starter Price ID:      $STARTER_PRICE_ID"
echo "Professional Price ID: $PROFESSIONAL_PRICE_ID"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Add these to your .env file:"
echo ""
echo "   REACT_APP_STRIPE_PRICE_STARTER=$STARTER_PRICE_ID"
echo "   REACT_APP_STRIPE_PRICE_PROFESSIONAL=$PROFESSIONAL_PRICE_ID"
echo ""
echo "2. Or run this command to auto-update .env:"
echo ""
echo "   ./scripts/stripe-update-env.sh \"$STARTER_PRICE_ID\" \"$PROFESSIONAL_PRICE_ID\""
echo ""
echo "3. Restart your backend and frontend"
echo ""
