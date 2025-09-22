#!/bin/bash

# ExamCraft AI - Development Startup Script
echo "🚀 Starting ExamCraft AI Development Environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and add your Claude API key!"
fi

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running at http://localhost:8000"
    echo "📚 API Documentation: http://localhost:8000/docs"
else
    echo "❌ Backend health check failed"
fi

# Check frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is running at http://localhost:3000"
else
    echo "⏳ Frontend is still starting up..."
fi

# Check database
if docker exec examcraft_postgres pg_isready -U examcraft > /dev/null 2>&1; then
    echo "✅ PostgreSQL database is ready"
else
    echo "❌ Database connection failed"
fi

# Check Redis
if docker exec examcraft_redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis cache is ready"
else
    echo "❌ Redis connection failed"
fi

echo ""
echo "🎉 ExamCraft AI Development Environment is ready!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🗄️  Database: localhost:5432 (examcraft/examcraft_dev)"
echo "🔴 Redis: localhost:6379"
echo ""
echo "📋 Useful commands:"
echo "  docker-compose logs -f          # View all logs"
echo "  docker-compose logs -f backend  # View backend logs"
echo "  docker-compose logs -f frontend # View frontend logs"
echo "  docker-compose down             # Stop all services"
echo "  docker-compose restart          # Restart all services"
echo ""
