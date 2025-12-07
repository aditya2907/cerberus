#  Sentinel - Distributed Fraud Detection System

A high-performance, fault-tolerant fraud detection system demonstrating distributed systems patterns including Circuit Breaker, gRPC microservices, and container orchestration.

##  Architecture

```

   Frontend      
 (Next.js/React) 

         
         
      
   Gateway          MongoDB    
   (FastAPI)              (Ledger)   
  Circuit Breaker      

          gRPC
         

     Brain       
 (ML Inference)  
   gRPC Server   

```

##  Tech Stack

### Backend
- **Gateway**: Python FastAPI (REST API)
- **Brain**: Python gRPC (ML Inference Service)
- **Database**: MongoDB 7.0 (Transaction Ledger)
- **Patterns**: Circuit Breaker (pybreaker), Fail-Open Strategy

### Frontend
- **Framework**: Next.js 14 (React)
- **Dashboard**: Real-time monitoring

### Infrastructure
- **Local Dev**: Docker Compose
- **Production**: Kubernetes (with HPA)
- **Protocol**: gRPC for service-to-service communication

##  Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- kubectl (for Kubernetes deployment)
- grpcio-tools

##  Quick Start

### 1. Setup Project Structure

```bash
# Run setup script to create folder structure
./setup.sh

# Compile proto files
./compile_protos.sh
```

### 2. Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services will be available at:
- **Gateway API**: http://localhost:8000
- **Gateway Docs**: http://localhost:8000/docs
- **Brain gRPC**: localhost:50051
- **MongoDB**: localhost:27017

### 3. Test the System

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Health check
curl http://localhost:8000/health

# Circuit breaker status
curl http://localhost:8000/circuit/status

# Submit a transaction
curl -X POST http://localhost:8000/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_001",
    "amount": 150.50,
    "currency": "USD",
    "user_id": "user_123"
  }'
```

### 4. Chaos Testing (Circuit Breaker Demo)

```bash
# Start chaos test
python test_chaos.py

# While it's running, kill the brain service to see circuit breaker in action:
docker-compose stop brain

# Watch the requests transition from "Success" to "Circuit Open"!
```

##  Key Features

### Circuit Breaker Pattern
- **Fail-Open Strategy**: When ML service is down, system defaults to "safe" (not fraud)
- **Automatic Recovery**: Circuit attempts to close after 30 seconds
- **Configurable Thresholds**: Opens after 3 consecutive failures

### Fault Tolerance
- 10% of brain service requests simulate 2-second latency
- Gateway handles timeouts gracefully
- System remains available even when brain service fails

### Observability
- Structured logging throughout
- Health check endpoints
- Circuit breaker status monitoring
- Real-time metrics

##  Project Structure

```
sentinel-fraud-engine/
 backend/
    gateway/              # FastAPI REST gateway
       main.py          # API endpoints + circuit breaker
       requirements.txt
       Dockerfile
       __init__.py
    brain/               # gRPC ML inference service
       main.py          # gRPC server + dummy ML
       requirements.txt
       Dockerfile
       __init__.py
    protos/
        fraud.proto      # gRPC service definition
 frontend/
    dashboard/           # Next.js dashboard (to be implemented)
 infra/
    docker/              # Dockerfile templates
       Dockerfile.brain
       Dockerfile.gateway
    k8s/                 # Kubernetes manifests
        brain-deployment.yaml
        brain-service.yaml
        gateway-deployment.yaml
        gateway-service.yaml
        db-statefulset.yaml
        db-service.yaml
        hpa.yaml         # Horizontal Pod Autoscaler
        README.md        # K8s deployment guide
 docker-compose.yml       # Local development setup
 setup.sh                 # Project scaffolding script
 compile_protos.sh        # Proto compilation script
 test_chaos.py           # Chaos testing tool
 requirements-test.txt    # Test dependencies
```

##  Docker Compose Services

### Gateway
- **Port**: 8000
- **Dependencies**: brain, db
- **Environment**: 
  - `BRAIN_SERVICE_HOST=brain`
  - `BRAIN_SERVICE_PORT=50051`
  - `MONGODB_URL=mongodb://...`

### Brain
- **Port**: 50051
- **Purpose**: ML inference via gRPC
- **Features**: Random latency injection for testing

### Database (MongoDB)
- **Port**: 27017
- **Database**: fraud_ledger
- **Credentials**: sentinel/sentinel_password

##  Kubernetes Deployment

See [infra/k8s/README.md](infra/k8s/README.md) for detailed Kubernetes deployment instructions.

Quick deploy:
```bash
# Deploy all resources
kubectl apply -f infra/k8s/

# Or deploy step-by-step
kubectl apply -f infra/k8s/db-statefulset.yaml
kubectl apply -f infra/k8s/db-service.yaml
kubectl apply -f infra/k8s/brain-deployment.yaml
kubectl apply -f infra/k8s/brain-service.yaml
kubectl apply -f infra/k8s/gateway-deployment.yaml
kubectl apply -f infra/k8s/gateway-service.yaml
kubectl apply -f infra/k8s/hpa.yaml
```

##  Testing

### Manual Testing
```bash
# Test successful transaction
curl -X POST http://localhost:8000/transaction \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": "txn_001", "amount": 100, "currency": "USD", "user_id": "user_1"}'
```

### Chaos Testing
```bash
# Run 100 concurrent requests
python test_chaos.py --requests 100 --workers 20

# Custom endpoint
python test_chaos.py --url http://your-gateway-ip:8000 --requests 200
```

### Circuit Breaker Testing
1. Start chaos test: `python test_chaos.py`
2. Kill brain service: `docker-compose stop brain`
3. Observe circuit opening and fail-open behavior
4. Restart brain: `docker-compose start brain`
5. Observe circuit closing and normal operation resuming

##  Monitoring

### Health Endpoints
- `GET /health` - Service health status
- `GET /circuit/status` - Circuit breaker state

### Docker Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f gateway
docker-compose logs -f brain
```

### Kubernetes Logs
```bash
kubectl logs -f deployment/sentinel-gateway
kubectl logs -f deployment/sentinel-brain
```

##  Development

### Adding New Features

1. **Update Proto Definition** (if needed)
   ```bash
   # Edit backend/protos/fraud.proto
   ./compile_protos.sh
   ```

2. **Modify Services**
   - Gateway: `backend/gateway/main.py`
   - Brain: `backend/brain/main.py`

3. **Rebuild & Test**
   ```bash
   docker-compose up --build
   ```

### Environment Variables

**Gateway**:
- `BRAIN_SERVICE_HOST` - Brain service hostname (default: localhost)
- `BRAIN_SERVICE_PORT` - Brain service port (default: 50051)
- `MONGODB_URL` - MongoDB connection string

##  Troubleshooting

### Proto Compilation Issues
```bash
# Reinstall grpcio-tools
pip install --upgrade grpcio-tools

# Recompile
./compile_protos.sh
```

### Docker Build Issues
```bash
# Clean build
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Import Errors
Make sure proto files are compiled:
```bash
./compile_protos.sh
```

### Circuit Breaker Not Opening
- Check brain service is actually failing/slow
- Verify timeout settings in gateway/main.py
- Increase failure threshold for testing

##  Learn More

### Distributed Systems Patterns
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [gRPC Best Practices](https://grpc.io/docs/guides/performance/)
- [Kubernetes Patterns](https://kubernetes.io/docs/concepts/)

### Technologies Used
- [FastAPI](https://fastapi.tiangolo.com/)
- [gRPC Python](https://grpc.io/docs/languages/python/)
- [pybreaker](https://github.com/danielfm/pybreaker)
- [Next.js](https://nextjs.org/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Kubernetes](https://kubernetes.io/)

##  License

MIT License - Feel free to use this project for learning and development.

##  Contributing

This is an educational project demonstrating distributed systems patterns. Feel free to:
- Add new features (e.g., actual ML models)
- Improve observability (metrics, tracing)
- Enhance the frontend dashboard
- Add more tests

##  Authors

Built as a Distributed Systems project demonstrating:
- Microservices architecture
- Circuit breaker pattern
- gRPC communication
- Container orchestration
- Fault tolerance and resilience

---

**Note**: This is a demonstration project. In production, you would:
- Use actual ML models instead of random scores
- Implement proper authentication/authorization
- Add distributed tracing (Jaeger, Zipkin)
- Use proper secrets management
- Add comprehensive monitoring (Prometheus, Grafana)
- Implement proper database migrations
- Add integration and load tests
