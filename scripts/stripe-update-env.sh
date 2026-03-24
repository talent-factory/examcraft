#!/bin/bash
set -e

STARTER_PRICE_ID=$1
PROFESSIONAL_PRICE_ID=$2

if [ -z "$STARTER_PRICE_ID" ] || [ -z "$PROFESSIONAL_PRICE_ID" ]; then
    echo "Usage: $0 <starter_price_id> <professional_price_id>"
    echo ""
    echo "Example:"
    echo "  $0 price_1ABC123 price_2DEF456"
    exit 1
fi

ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

echo "=========================================="
echo "Updating .env with Stripe Price IDs"
echo "=========================================="
echo ""

# Check if variables already exist
if grep -q "REACT_APP_STRIPE_PRICE_STARTER=" "$ENV_FILE"; then
    # Update existing
    sed -i.bak "s|REACT_APP_STRIPE_PRICE_STARTER=.*|REACT_APP_STRIPE_PRICE_STARTER=$STARTER_PRICE_ID|" "$ENV_FILE"
    echo "✅ Updated REACT_APP_STRIPE_PRICE_STARTER"
else
    # Append new
    echo "" >> "$ENV_FILE"
    echo "# Stripe Configuration" >> "$ENV_FILE"
    echo "REACT_APP_STRIPE_PRICE_STARTER=$STARTER_PRICE_ID" >> "$ENV_FILE"
    echo "✅ Added REACT_APP_STRIPE_PRICE_STARTER"
fi

if grep -q "REACT_APP_STRIPE_PRICE_PROFESSIONAL=" "$ENV_FILE"; then
    # Update existing
    sed -i.bak "s|REACT_APP_STRIPE_PRICE_PROFESSIONAL=.*|REACT_APP_STRIPE_PRICE_PROFESSIONAL=$PROFESSIONAL_PRICE_ID|" "$ENV_FILE"
    echo "✅ Updated REACT_APP_STRIPE_PRICE_PROFESSIONAL"
else
    # Append new
    echo "REACT_APP_STRIPE_PRICE_PROFESSIONAL=$PROFESSIONAL_PRICE_ID" >> "$ENV_FILE"
    echo "✅ Added REACT_APP_STRIPE_PRICE_PROFESSIONAL"
fi

# Clean up backup file
rm -f "$ENV_FILE.bak"

echo ""
echo "=========================================="
echo "✅ .env Updated Successfully!"
echo "=========================================="
echo ""
echo "Price IDs configured:"
echo "  Starter:      $STARTER_PRICE_ID"
echo "  Professional: $PROFESSIONAL_PRICE_ID"
echo ""
echo "Next: Restart backend and frontend to load new config"
echo ""
