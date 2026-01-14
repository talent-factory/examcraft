#!/bin/bash

# Stripe Webhook Testing Script
# This script helps you test Stripe webhooks locally using Stripe CLI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "========================================="
echo "Stripe Webhook Local Testing"
echo "========================================="
echo ""

# Check if stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI is not installed."
    echo ""
    echo "Please install Stripe CLI first:"
    echo "  macOS:   brew install stripe/stripe-cli/stripe"
    echo "  Linux:   Download from https://github.com/stripe/stripe-cli/releases"
    echo "  Windows: Download from https://github.com/stripe/stripe-cli/releases"
    echo ""
    exit 1
fi

echo "✅ Stripe CLI is installed"
echo ""

# Check if user is logged in to Stripe
if ! stripe config --list &> /dev/null; then
    echo "⚠️  You need to login to Stripe CLI first"
    echo "Run: stripe login"
    echo ""
    exit 1
fi

echo "✅ Stripe CLI is authenticated"
echo ""

# Get backend URL from .env or use default
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
WEBHOOK_ENDPOINT="${BACKEND_URL}/api/v1/webhooks/stripe"

echo "📡 Webhook Endpoint: ${WEBHOOK_ENDPOINT}"
echo ""

# Check if backend is running
if ! curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/docs" | grep -q "200"; then
    echo "⚠️  Backend is not running at ${BACKEND_URL}"
    echo "Please start the backend first:"
    echo "  ./start-dev.sh --full"
    echo ""
    exit 1
fi

echo "✅ Backend is running"
echo ""

echo "========================================="
echo "Starting Stripe Webhook Forwarding"
echo "========================================="
echo ""
echo "This will forward Stripe webhook events to your local backend."
echo "Events will be forwarded to: ${WEBHOOK_ENDPOINT}"
echo ""
echo "⚠️  IMPORTANT: Copy the webhook signing secret from the output below"
echo "    and add it to your .env file as STRIPE_WEBHOOK_SECRET"
echo ""
echo "Events being forwarded:"
echo "  - checkout.session.completed"
echo "  - customer.subscription.updated"
echo "  - customer.subscription.deleted"
echo ""
echo "Press Ctrl+C to stop..."
echo ""

# Forward webhooks to local backend
stripe listen \
    --forward-to "${WEBHOOK_ENDPOINT}" \
    --events checkout.session.completed,customer.subscription.updated,customer.subscription.deleted
