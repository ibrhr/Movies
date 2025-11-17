#!/bin/bash
# Deployment script for Digital Ocean

set -e

echo "=========================================="
echo "Movies Recommender - Deployment Script"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "   Copy .env.example and fill in your values"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)
echo ""
echo "Step 1: Building Docker image..."
docker-compose -f docker-compose.yml build

echo ""
echo "Step 2: Stopping old containers..."
docker-compose -f docker-compose.yml down

echo ""
echo "Step 3: Starting new containers..."
docker-compose -f docker-compose.yml up -d

echo ""
echo "Step 4: Waiting for app to be healthy..."
sleep 10

# Check health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Application is running!"
else
    echo "⚠️  Health check failed, checking logs..."
    docker-compose -f docker-compose.yml logs --tail=50
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Deployment complete!"
echo "=========================================="
echo ""
echo "View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "Stop app:  docker-compose -f docker-compose.prod.yml down"
echo "Restart:   docker-compose -f docker-compose.prod.yml restart"
