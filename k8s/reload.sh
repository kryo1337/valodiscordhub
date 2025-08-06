#!/bin/bash

# Quick reload script for ValoDiscordHub development

echo "🔄 Quick reload for ValoDiscordHub development..."

# Check if we're in the right directory
if [ ! -f "../api/main.py" ] || [ ! -f "../bot/bot.py" ]; then
    echo "❌ Please run this script from the k8s directory"
    exit 1
fi

# Set docker environment to minikube
eval $(minikube docker-env 2>/dev/null || minikube docker-env)

# Build images
echo "🐳 Building Docker images..."
cd ..
docker build -t valodiscordhub/api:latest ./api
docker build -t valodiscordhub/bot:latest ./bot
cd k8s

# Restart deployments
echo "🔄 Restarting deployments..."
kubectl rollout restart deployment/api-deployment -n valodiscordhub
kubectl rollout restart deployment/bot-deployment -n valodiscordhub

# Wait for rollouts to complete
echo "⏳ Waiting for rollouts to complete..."
kubectl rollout status deployment/api-deployment -n valodiscordhub
kubectl rollout status deployment/bot-deployment -n valodiscordhub

echo "✅ Reload completed!"
echo "📊 Current status:"
kubectl get pods -n valodiscordhub 