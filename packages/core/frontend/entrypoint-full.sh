#!/bin/sh

# ExamCraft AI - Frontend Entrypoint (Full Deployment)
# Merges Premium/Enterprise packages into Core at runtime for development hot-reload

echo "🚀 ExamCraft AI - Frontend (Full Mode) Starting..."
echo "=================================================="

# Check if we're in development mode
if [ "$REACT_APP_ENVIRONMENT" = "development" ]; then
    echo "📦 Merging Premium/Enterprise packages for hot-reload..."

    # Create premium and enterprise directories if they don't exist
    mkdir -p /app/src/premium
    mkdir -p /app/src/enterprise

    # Copy Premium package if mounted (for hot-reload support)
    if [ -d "/premium-src" ] && [ "$(ls -A /premium-src 2>/dev/null)" ]; then
        echo "  ✅ Copying Premium package..."
        cp -r /premium-src/* /app/src/premium/ 2>/dev/null || true
    else
        echo "  ℹ️  Premium package not found (running Core-only)"
    fi

    # Copy Enterprise package if mounted (for hot-reload support)
    if [ -d "/enterprise-src" ] && [ "$(ls -A /enterprise-src 2>/dev/null)" ]; then
        echo "  ✅ Copying Enterprise package..."
        cp -r /enterprise-src/* /app/src/enterprise/ 2>/dev/null || true
    else
        echo "  ℹ️  Enterprise package not found"
    fi

    echo "  ✅ Package merging complete!"
    echo ""
fi

# Fix any missing module exports (isolatedModules compatibility)
echo "🔧 Fixing TypeScript isolatedModules issues..."
for file in /app/src/premium/api/index.ts \
            /app/src/premium/components/index.ts \
            /app/src/premium/services/index.ts \
            /app/src/services/ChatService.ts \
            /app/src/services/RAGService.ts; do
    if [ -f "$file" ]; then
        # Check if file has any export
        if ! grep -q "export" "$file" 2>/dev/null; then
            echo "export {};" >> "$file"
            echo "  ✅ Fixed: $file"
        fi
    fi
done

echo ""
echo "✅ Frontend ready to start!"
echo "=================================================="
echo ""

# Start the development server
exec npm start
