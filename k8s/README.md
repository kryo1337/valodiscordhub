# ValoDiscordHub Kubernetes Setup

This directory contains all the Kubernetes manifests for deploying ValoDiscordHub to a Kubernetes cluster.

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes Cluster**: You need a running Kubernetes cluster (minikube, kind, or cloud provider)
2. **kubectl**: Install kubectl to interact with your cluster
3. **Docker Images**: Build and push your Docker images to a registry

### 1. Build and Push Docker Images

```bash
# Build API image
docker build -t valodiscordhub/api:latest ./api
docker push valodiscordhub/api:latest

# Build Bot image
docker build -t valodiscordhub/bot:latest ./bot
docker push valodiscordhub/bot:latest
```

### 2. Configure Secrets

Run the secret encoder script to get your base64-encoded secrets:

```bash
./k8s/encode-secrets.sh
```

Update `k8s/secrets.yaml` with the encoded values.

### 3. Update Configuration

Edit `k8s/configmaps.yaml` with your actual values:
- `DISCORD_GUILD_ID`: Your Discord server ID
- `API_BASE_URL`: Your API base URL
- `DISCORD_REDIRECT_URI`: Your Discord OAuth redirect URI

### 4. Deploy

```bash
cd k8s
./deploy.sh
```

## 📁 File Structure

```
k8s/
├── namespace.yaml          # Namespace definition
├── secrets.yaml           # Kubernetes secrets (update with your values)
├── configmaps.yaml        # Environment configuration
├── mongodb.yaml           # MongoDB StatefulSet and Service
├── api-deployment.yaml    # API deployment, service, and HPA
├── bot-deployment.yaml    # Bot deployment and service
├── ingress.yaml           # Ingress configuration for external access
├── deploy.sh              # Deployment automation script
├── encode-secrets.sh      # Secret encoding helper
└── README.md              # This file
```

## 🔧 Configuration

### Secrets

The following secrets need to be configured in `secrets.yaml`:

**Discord Secrets:**
- `DISCORD_TOKEN`: Your Discord bot token
- `DISCORD_CLIENT_ID`: Your Discord application client ID
- `DISCORD_CLIENT_SECRET`: Your Discord application client secret
- `BOT_API_TOKEN`: Token for bot-API communication
- `JWT_SECRET`: Secret for JWT token signing

**MongoDB Secrets:**
- `MONGO_INITDB_ROOT_USERNAME`: MongoDB admin username
- `MONGO_INITDB_ROOT_PASSWORD`: MongoDB admin password

### ConfigMaps

Update `configmaps.yaml` with your environment-specific values:

- `DISCORD_GUILD_ID`: Your Discord server ID
- `API_BASE_URL`: Your API base URL
- `DISCORD_REDIRECT_URI`: Discord OAuth redirect URI

## 🌐 Accessing the Application

### Local Development

```bash
# Port forward to access API locally
kubectl port-forward service/api-service 8000:8000 -n valodiscordhub

# Access API at http://localhost:8000
```

### Production

Configure your DNS to point `api.valodiscordhub.com` to your cluster's ingress controller.

## 📊 Monitoring

### Check Pod Status

```bash
kubectl get pods -n valodiscordhub
```

### View Logs

```bash
# API logs
kubectl logs -f deployment/api-deployment -n valodiscordhub

# Bot logs
kubectl logs -f deployment/bot-deployment -n valodiscordhub

# MongoDB logs
kubectl logs -f statefulset/mongodb -n valodiscordhub
```

### Scale Services

```bash
# Scale API
kubectl scale deployment api-deployment --replicas=3 -n valodiscordhub

# Scale Bot (usually keep at 1)
kubectl scale deployment bot-deployment --replicas=1 -n valodiscordhub
```

## 🔒 Security

### Network Policies

The current setup includes basic network isolation. For production, consider adding:

- Network policies to restrict pod-to-pod communication
- RBAC for service accounts
- Pod security policies

### SSL/TLS

To enable HTTPS:

1. Install cert-manager
2. Uncomment TLS configuration in `ingress.yaml`
3. Configure your domain and certificates

## 🗄️ Database

### MongoDB

- Uses StatefulSet for persistent storage
- 10GB persistent volume per replica
- Authentication enabled
- Health checks configured

### Backup

Consider setting up automated backups:

```bash
# Manual backup
kubectl exec -it mongodb-0 -n valodiscordhub -- mongodump --archive=/backup/backup.archive
```

## 🚨 Troubleshooting

### Common Issues

1. **Pods not starting**: Check resource limits and requests
2. **API not accessible**: Verify ingress controller is installed
3. **Bot not connecting**: Check Discord token and permissions
4. **Database connection issues**: Verify MongoDB credentials

### Debug Commands

```bash
# Describe pod for detailed status
kubectl describe pod <pod-name> -n valodiscordhub

# Check events
kubectl get events -n valodiscordhub

# Check service endpoints
kubectl get endpoints -n valodiscordhub
```

## 📈 Scaling

### Horizontal Pod Autoscaler

The API deployment includes an HPA that scales based on:
- CPU utilization (70% threshold)
- Memory utilization (80% threshold)
- Min: 2 replicas, Max: 10 replicas

### Manual Scaling

```bash
# Scale API
kubectl scale deployment api-deployment --replicas=5 -n valodiscordhub

# Scale MongoDB (be careful with StatefulSets)
kubectl scale statefulset mongodb --replicas=3 -n valodiscordhub
```

## 🔄 Updates

### Rolling Updates

```bash
# Update API image
kubectl set image deployment/api-deployment api=valodiscordhub/api:v2.0.0 -n valodiscordhub

# Update Bot image
kubectl set image deployment/bot-deployment bot=valodiscordhub/bot:v2.0.0 -n valodiscordhub
```

### Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/api-deployment -n valodiscordhub
```

## 🧹 Cleanup

To remove the entire deployment:

```bash
kubectl delete namespace valodiscordhub
```

**Warning**: This will delete all data, including the MongoDB persistent volumes! 