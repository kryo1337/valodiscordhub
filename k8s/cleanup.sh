#!/bin/bash

# Cleanup script for ValoDiscordHub Kubernetes deployment
echo "🧹 Cleaning up ValoDiscordHub Kubernetes deployment..."

# Confirm deletion
echo "⚠️  This will delete the entire valodiscordhub namespace and all data!"
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

# Delete the namespace (this will delete everything)
echo "🗑️  Deleting valodiscordhub namespace..."
kubectl delete namespace valodiscordhub

echo "✅ Cleanup completed!"
echo "📝 Note: If you're using minikube, persistent volumes may still exist."
echo "   To completely clean up, run: minikube delete" 