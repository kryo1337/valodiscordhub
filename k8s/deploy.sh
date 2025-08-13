#!/bin/bash

# ValoDiscordHub Kubernetes Deployment Script
set -e

echo "🚀 Starting ValoDiscordHub Kubernetes deployment..."

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if we have a cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Please check your cluster connection."
    exit 1
fi

echo "✅ Kubernetes cluster connection verified"

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f namespace.yaml

# Create secrets (you need to update secrets.yaml with your actual values)
echo "🔐 Creating secrets..."
echo "⚠️  Make sure to update k8s/secrets.yaml with your actual base64-encoded values!"
kubectl apply -f secrets.yaml

# Create configmaps
echo "⚙️  Creating configmaps..."
echo "⚠️  Make sure to update k8s/configmaps.yaml with your actual values!"
kubectl apply -f configmaps.yaml

# Deploy MongoDB
echo "🗄️  Deploying MongoDB..."
kubectl apply -f mongodb.yaml

# Wait for MongoDB to be ready
echo "⏳ Waiting for MongoDB to be ready..."
kubectl wait --for=condition=ready pod -l app=mongodb -n valodiscordhub --timeout=300s

# Deploy API
echo "🌐 Deploying API..."
kubectl apply -f api-deployment.yaml

# Deploy Bot
echo "🤖 Deploying Bot..."
kubectl apply -f bot-deployment.yaml

# Deploy Ingress
echo "🌍 Deploying Ingress..."
kubectl apply -f ingress.yaml

echo "✅ Deployment completed!"

# Show status
echo "📊 Current status:"
kubectl get pods -n valodiscordhub
kubectl get services -n valodiscordhub
kubectl get ingress -n valodiscordhub

echo ""
echo "🔍 To check logs:"
echo "  kubectl logs -f deployment/api-deployment -n valodiscordhub"
echo "  kubectl logs -f deployment/bot-deployment -n valodiscordhub"
echo ""
echo "🌐 To access the API:"
echo "  kubectl port-forward service/api-service 8000:8000 -n valodiscordhub"
echo ""
echo "📝 To scale the API:"
echo "  kubectl scale deployment api-deployment --replicas=3 -n valodiscordhub" 