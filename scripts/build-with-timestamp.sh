#!/bin/bash
# Build Docker containers with timestamp

# Generate timestamp
export BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "🔨 Building ExamCraft with timestamp: $BUILD_TIMESTAMP"

# Build backend with timestamp
docker-compose build --build-arg BUILD_TIMESTAMP="$BUILD_TIMESTAMP" backend

echo "✅ Build complete!"
echo "📅 Build Timestamp: $BUILD_TIMESTAMP"
