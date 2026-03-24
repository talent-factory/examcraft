#!/bin/bash

# Stripe Test Events Trigger Script
# This script triggers test events to verify webhook handling

set -e

echo "========================================="
echo "Stripe Test Events Trigger"
echo "========================================="
echo ""

# Check if stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI is not installed."
    exit 1
fi

echo "This script will trigger test Stripe events to verify your webhook handling."
echo ""
echo "Available test events:"
echo "  1) checkout.session.completed (Successful subscription purchase)"
echo "  2) customer.subscription.updated (Subscription status change)"
echo "  3) customer.subscription.deleted (Subscription cancellation)"
echo "  4) All of the above"
echo ""

read -p "Select test event to trigger (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Triggering: checkout.session.completed"
        stripe trigger checkout.session.completed
        ;;
    2)
        echo ""
        echo "🚀 Triggering: customer.subscription.updated"
        stripe trigger customer.subscription.updated
        ;;
    3)
        echo ""
        echo "🚀 Triggering: customer.subscription.deleted"
        stripe trigger customer.subscription.deleted
        ;;
    4)
        echo ""
        echo "🚀 Triggering all test events..."
        echo ""
        echo "1/3: checkout.session.completed"
        stripe trigger checkout.session.completed
        sleep 2
        echo ""
        echo "2/3: customer.subscription.updated"
        stripe trigger customer.subscription.updated
        sleep 2
        echo ""
        echo "3/3: customer.subscription.deleted"
        stripe trigger customer.subscription.deleted
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Test events triggered successfully!"
echo ""
echo "Check your terminal running 'stripe listen' for webhook delivery status."
echo "Check your database to verify the subscription records were created/updated."
echo ""
echo "To view subscriptions in database:"
echo "  docker exec -it examcraft-postgres-1 psql -U examcraft -d examcraft -c 'SELECT * FROM subscriptions;'"
echo ""
