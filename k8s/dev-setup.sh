#!/bin/bash

# Development setup script for ValoDiscordHub
echo "🔧 Setting up ValoDiscordHub for local development..."

# Check if minikube is installed
if ! command -v minikube &> /dev/null; then
    echo "❌ minikube is not installed. Installing minikube..."
    
    # Install minikube
    curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
    sudo install minikube-linux-amd64 /usr/local/bin/minikube
    rm minikube-linux-amd64
    
    echo "✅ minikube installed"
else
    echo "✅ minikube is already installed"
fi

# Start minikube if not running
if ! minikube status | grep -q "Running"; then
    echo "🚀 Starting minikube..."
    minikube start --cpus=4 --memory=8192 --disk-size=20g
    echo "✅ minikube started"
else
    echo "✅ minikube is already running"
fi

# Enable ingress addon
echo "🌐 Enabling ingress addon..."
minikube addons enable ingress

# Enable metrics server for HPA
echo "📊 Enabling metrics server..."
minikube addons enable metrics-server

# Build and load Docker images
echo "🐳 Building and loading Docker images..."

# Set docker environment to minikube
eval $(minikube docker-env)

# Build API image
echo "Building API image..."
docker build -t valodiscordhub/api:latest ./api

# Build Bot image
echo "Building Bot image..."
docker build -t valodiscordhub/bot:latest ./bot

# Build Frontend image
echo "Building Frontend image..."
docker build -t valodiscordhub/frontend:latest ./frontend

echo "✅ Images built and loaded into minikube"

# Show minikube status
echo ""
echo "📊 Minikube Status:"
minikube status

echo ""
echo "🌐 To access the application:"
echo "  minikube service api-service -n valodiscordhub"
echo ""
echo "🔍 To view logs:"
echo "  kubectl logs -f deployment/api-deployment -n valodiscordhub"
echo ""
echo "🚀 Ready to deploy! Run:"
echo "  cd k8s && ./deploy.sh" 