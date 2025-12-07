# Sentinel Fraud Detection System - Kubernetes Deployment Guide

## Prerequisites
- Kubernetes cluster (minikube, kind, or cloud provider)
- kubectl configured
- Docker images built and pushed to registry

## Build and Push Images (if using remote cluster)
```bash
# Build images
docker build -t sentinel-brain:latest -f infra/docker/Dockerfile.brain backend/brain
docker build -t sentinel-gateway:latest -f infra/docker/Dockerfile.gateway backend/gateway

# Tag for your registry
docker tag sentinel-brain:latest <your-registry>/sentinel-brain:latest
docker tag sentinel-gateway:latest <your-registry>/sentinel-gateway:latest

# Push to registry
docker push <your-registry>/sentinel-brain:latest
docker push <your-registry>/sentinel-gateway:latest
```

## Deploy to Kubernetes

### Option 1: Deploy all at once
```bash
kubectl apply -f infra/k8s/
```

### Option 2: Deploy in order (recommended for first deployment)
```bash
# 1. Deploy database
kubectl apply -f infra/k8s/db-statefulset.yaml
kubectl apply -f infra/k8s/db-service.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=sentinel-db --timeout=120s

# 2. Deploy ML inference service
kubectl apply -f infra/k8s/brain-deployment.yaml
kubectl apply -f infra/k8s/brain-service.yaml

# Wait for brain service to be ready
kubectl wait --for=condition=ready pod -l app=sentinel-brain --timeout=120s

# 3. Deploy API gateway
kubectl apply -f infra/k8s/gateway-deployment.yaml
kubectl apply -f infra/k8s/gateway-service.yaml

# Wait for gateway to be ready
kubectl wait --for=condition=ready pod -l app=sentinel-gateway --timeout=120s

# 4. Deploy autoscalers (optional)
kubectl apply -f infra/k8s/hpa.yaml
```

## Verify Deployment
```bash
# Check all pods
kubectl get pods

# Check services
kubectl get services

# Check HPAs
kubectl get hpa

# Get gateway external IP (for LoadBalancer)
kubectl get service sentinel-gateway
```

## Access the Application

### For LoadBalancer (cloud environments)
```bash
# Get external IP
GATEWAY_IP=$(kubectl get service sentinel-gateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Gateway URL: http://$GATEWAY_IP"
```

### For local/minikube
```bash
# Use port-forward
kubectl port-forward service/sentinel-gateway 8000:80

# Access at http://localhost:8000
```

## Test the API
```bash
# Health check
curl http://localhost:8000/health

# Circuit breaker status
curl http://localhost:8000/circuit/status

# Check a transaction
curl -X POST http://localhost:8000/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_001",
    "amount": 150.50,
    "currency": "USD",
    "user_id": "user_123"
  }'
```

## Monitor Circuit Breaker
```bash
# Watch circuit breaker state
watch -n 1 'curl -s http://localhost:8000/circuit/status | jq'
```

## Scaling
```bash
# Manual scaling
kubectl scale deployment sentinel-brain --replicas=5
kubectl scale deployment sentinel-gateway --replicas=3

# Check HPA status
kubectl get hpa
kubectl describe hpa sentinel-brain-hpa
```

## Logs
```bash
# Gateway logs
kubectl logs -f deployment/sentinel-gateway

# Brain logs
kubectl logs -f deployment/sentinel-brain

# Database logs
kubectl logs -f statefulset/sentinel-db
```

## Cleanup
```bash
# Delete all resources
kubectl delete -f infra/k8s/

# Or delete individually
kubectl delete hpa --all
kubectl delete deployment --all
kubectl delete statefulset --all
kubectl delete service --all
kubectl delete pvc --all
```

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Service connectivity issues
```bash
# Test internal DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup sentinel-brain

# Test connection to brain service
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- nc -zv sentinel-brain 50051
```

### HPA not scaling
```bash
# Check metrics server
kubectl top nodes
kubectl top pods

# If metrics server not installed
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```
