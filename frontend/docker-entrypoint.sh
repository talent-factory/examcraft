#!/bin/sh
# Docker Entrypoint Script for Frontend Container
# Removes problematic symlinks before starting the development server

set -e

echo "🧹 Cleaning up symlinks..."

# Remove premium/enterprise symlinks if they exist
rm -rf /workspace/packages/core/frontend/src/premium
rm -rf /workspace/packages/core/frontend/src/enterprise

echo "✅ Symlinks removed"

# Start the development server
echo "🚀 Starting development server..."
exec "$@"
