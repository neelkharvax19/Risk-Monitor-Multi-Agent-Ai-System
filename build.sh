#!/bin/bash
echo "🧹 Cleaning old containers..."
docker rm -f risk-monitor-prod 2>/dev/null

echo "🏗️ Building Docker image..."
docker build -f Dockerfile.prod -t risk-monitor:prod .

echo "🚀 Running container locally..."
docker run -d --name risk-monitor-prod --env-file .env risk-monitor:prod

echo "✅ Container running. Logs:"
docker logs -f risk-monitor-prod
