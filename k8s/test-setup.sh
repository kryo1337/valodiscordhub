#!/bin/bash

# Test script for ValoDiscordHub Kubernetes deployment
echo "🧪 Testing ValoDiscordHub Kubernetes deployment..."

# Check if namespace exists
if ! kubectl get namespace valodiscordhub &> /dev/null; then
    echo "❌ Namespace 'valodiscordhub' does not exist. Run deploy.sh first."
    exit 1
fi

echo "✅ Namespace exists"

# Check if all pods are running
echo "📊 Checking pod status..."
kubectl get pods -n valodiscordhub

# Wait for all pods to be ready
echo "⏳ Waiting for all pods to be ready..."
kubectl wait --for=condition=ready pod -l app=mongodb -n valodiscordhub --timeout=300s
kubectl wait --for=condition=ready pod -l app=api -n valodiscordhub --timeout=300s
kubectl wait --for=condition=ready pod -l app=bot -n valodiscordhub --timeout=300s
kubectl wait --for=condition=ready pod -l app=frontend -n valodiscordhub --timeout=300s

echo "✅ All pods are ready"

# Check services
echo "🌐 Checking services..."
kubectl get services -n valodiscordhub

# Test API health endpoint
echo "🏥 Testing API health endpoint..."
kubectl port-forward service/api-service 8000:8000 -n valodiscordhub &
PORT_FORWARD_PID=$!

# Wait for port forward to be ready
sleep 5

# Test health endpoint
if curl -f http://localhost:8000/healthz &> /dev/null; then
    echo "✅ API health check passed"
else
    echo "❌ API health check failed"
fi

# Kill port forward
kill $PORT_FORWARD_PID

# Check logs for errors
echo "📝 Checking for errors in logs..."
echo "API logs (last 10 lines):"
kubectl logs deployment/api-deployment -n valodiscordhub --tail=10

echo ""
echo "Bot logs (last 10 lines):"
kubectl logs deployment/bot-deployment -n valodiscordhub --tail=10

echo ""
echo "Frontend logs (last 10 lines):"
kubectl logs deployment/frontend-deployment -n valodiscordhub --tail=10

echo ""
echo "MongoDB logs (last 10 lines):"
kubectl logs statefulset/mongodb -n valodiscordhub --tail=10

echo ""
echo "🎉 Test completed!"
echo "🌐 To access the API: kubectl port-forward service/api-service 8000:8000 -n valodiscordhub"
echo "🎨 To access the Frontend: kubectl port-forward service/frontend-service 3000:80 -n valodiscordhub" 