.PHONY: help setup compile up down logs test chaos clean restart health advanced-up metrics replay

help: ## Show this help message
	@echo "🛡️  Sentinel Fraud Detection System - Make Commands"
	@echo "=================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Setup project structure
	@echo "📁 Setting up project structure..."
	./setup.sh
	@echo "✅ Setup complete!"

compile: ## Compile protobuf files
	@echo "📦 Compiling proto files..."
	./compile_protos.sh
	@echo "✅ Compilation complete!"

up: compile ## Build and start all services
	@echo "🐳 Starting services..."
	docker-compose up --build -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 10
	@echo "✅ Services are running!"
	@echo ""
	@echo "📍 Gateway API: http://localhost:8000"
	@echo "📍 API Docs: http://localhost:8000/docs"

down: ## Stop all services
	@echo "🛑 Stopping services..."
	docker-compose down
	@echo "✅ Services stopped!"

logs: ## View logs from all services
	docker-compose logs -f

logs-gateway: ## View gateway logs only
	docker-compose logs -f gateway

logs-brain: ## View brain logs only
	docker-compose logs -f brain

logs-db: ## View database logs only
	docker-compose logs -f db

test: ## Run a simple test transaction
	@echo "🧪 Testing transaction endpoint..."
	@curl -X POST http://localhost:8000/transaction \
		-H "Content-Type: application/json" \
		-d '{"transaction_id":"txn_test_001","amount":150.50,"currency":"USD","user_id":"user_test"}' \
		| python3 -m json.tool
	@echo ""

health: ## Check health of all services
	@echo "🏥 Checking service health..."
	@echo ""
	@echo "Gateway Health:"
	@curl -s http://localhost:8000/health | python3 -m json.tool
	@echo ""
	@echo "Circuit Breaker Status:"
	@curl -s http://localhost:8000/circuit/status | python3 -m json.tool
	@echo ""

chaos: ## Run chaos testing (requires aiohttp: pip install aiohttp)
	@echo "🔥 Starting chaos test..."
	python3 test_chaos.py

chaos-kill: ## Start chaos test and kill brain service after 5 seconds
	@echo "🔥 Starting chaos test with brain kill..."
	@(sleep 5 && docker-compose stop brain && echo "☠️  Brain service killed!") &
	python3 test_chaos.py

restart: down up ## Restart all services

restart-brain: ## Restart brain service only
	docker-compose restart brain

restart-gateway: ## Restart gateway service only
	docker-compose restart gateway

clean: down ## Stop services and remove volumes
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	@echo "✅ Cleanup complete!"

build: compile ## Build docker images without starting
	docker-compose build

ps: ## Show running services
	docker-compose ps

shell-gateway: ## Open shell in gateway container
	docker-compose exec gateway /bin/bash

shell-brain: ## Open shell in brain container
	docker-compose exec brain /bin/bash

shell-db: ## Open mongosh shell in database
	docker-compose exec db mongosh -u sentinel -p sentinel_password --authenticationDatabase admin fraud_ledger

# Kubernetes commands
k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f infra/k8s/

k8s-delete: ## Delete Kubernetes resources
	kubectl delete -f infra/k8s/

k8s-logs-gateway: ## View gateway logs in Kubernetes
	kubectl logs -f deployment/sentinel-gateway

k8s-logs-brain: ## View brain logs in Kubernetes
	kubectl logs -f deployment/sentinel-brain

k8s-status: ## Check Kubernetes deployment status
	@echo "Pods:"
	@kubectl get pods
	@echo ""
	@echo "Services:"
	@kubectl get services
	@echo ""
	@echo "HPAs:"
	@kubectl get hpa

# Development
dev-install: ## Install development dependencies
	pip install -r backend/gateway/requirements.txt
	pip install -r backend/brain/requirements.txt
	pip install -r requirements-test.txt
	pip install grpcio-tools

dev-run-brain: compile ## Run brain service locally
	cd backend/brain && python3 main.py

dev-run-gateway: compile ## Run gateway service locally
	cd backend/gateway && python3 main.py

advanced-up: ## Start all services with advanced features (Prometheus, Grafana, TimescaleDB)
	@echo "🚀 Starting Cerberus with Advanced Features..."
	@echo "   - Prometheus (metrics collection)"
	@echo "   - Grafana (visualization)"
	@echo "   - TimescaleDB (time-series storage)"
	@echo "   - Online ML (River)"
	@echo ""
	docker-compose up --build -d
	@echo "⏳ Waiting for services to initialize (30 seconds)..."
	@sleep 30
	@echo "✅ All services are running!"
	@echo ""
	@echo "📍 Main Dashboard: http://localhost:5173"
	@echo "📊 Grafana: http://localhost:3001 (admin/cerberus)"
	@echo "📈 Prometheus: http://localhost:9090"
	@echo "🔌 Guard API: http://localhost:8000"
	@echo ""
	@echo "🤖 Online ML: Judge service adapts in real-time"
	@echo "🗄️  TimescaleDB: Historical data storage enabled"
	@echo ""
	@echo "Run 'make metrics' to check system health"
	@echo "Run 'make replay' to test replay mode"

metrics: ## Check Prometheus metrics from all services
	@echo "📊 Checking Prometheus Metrics..."
	@echo ""
	@echo "Hunter (ticks processed):"
	@curl -s http://localhost:8001/metrics | grep ticks_processed_total || echo "  Service not ready"
	@echo ""
	@echo "Judge (anomalies detected):"
	@curl -s http://localhost:8002/metrics | grep anomalies_detected_total || echo "  Service not ready"
	@echo ""
	@echo "Guard (websocket connections):"
	@curl -s http://localhost:8000/metrics | grep guard_websocket_connections || echo "  Service not ready"
	@echo ""
	@echo "Scribe (records written):"
	@curl -s http://localhost:8003/metrics | grep scribe_records_written_total || echo "  Service not ready"
	@echo ""
	@echo "For full metrics, visit: http://localhost:9090"

replay: ## Test TimescaleDB replay mode (requires data collection)
	@echo "🎬 Testing Replay Mode..."
	@echo "Replaying last 10 minutes of market data at 2x speed..."
	@curl -s "http://localhost:8000/api/replay?start_time=$$(date -u -v-10M +%Y-%m-%dT%H:%M:%SZ)&end_time=$$(date -u +%Y-%m-%dT%H:%M:%SZ)&speed=2.0" | python3 -m json.tool
	@echo ""
	@echo "For custom replay, use:"
	@echo "  curl 'http://localhost:8000/api/replay?start_time=YYYY-MM-DDTHH:MM:SSZ&end_time=YYYY-MM-DDTHH:MM:SSZ&speed=2.0'"

health-advanced: ## Check health of all services including advanced features
	@echo "🏥 Advanced Health Check..."
	@echo ""
	@echo "Core Services:"
	@docker-compose ps hunter judge guard scribe
	@echo ""
	@echo "Data Services:"
	@docker-compose ps kafka timescaledb
	@echo ""
	@echo "Monitoring:"
	@docker-compose ps prometheus grafana
	@echo ""
	@echo "Service Endpoints:"
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "  Guard: DOWN"
	@echo ""
	@echo "Grafana: http://localhost:3001 (admin/cerberus)"
	@echo "Prometheus: http://localhost:9090"

logs-judge: ## View Judge (ML) logs
	docker-compose logs -f judge

logs-scribe: ## View Scribe (TimescaleDB writer) logs  
	docker-compose logs -f scribe

logs-advanced: ## View logs from all advanced services
	docker-compose logs -f prometheus grafana timescaledb scribe

db-shell: ## Open psql shell to TimescaleDB
	@echo "🗄️  Connecting to TimescaleDB..."
	@echo "Useful queries:"
	@echo "  SELECT COUNT(*) FROM market_data;"
	@echo "  SELECT * FROM market_data ORDER BY time DESC LIMIT 10;"
	@echo ""
	docker exec -it timescaledb psql -U cerberus_user -d cerberus

dashboard-info: ## Show all dashboard URLs
	@echo "📊 Cerberus Dashboards & Endpoints"
	@echo "=================================="
	@echo ""
	@echo "🎨 Frontend:"
	@echo "  Main Dashboard: http://localhost:5173"
	@echo ""
	@echo "📈 Monitoring:"
	@echo "  Grafana:       http://localhost:3001 (admin/cerberus)"
	@echo "  Prometheus:    http://localhost:9090"
	@echo ""
	@echo "🔌 APIs:"
	@echo "  Guard:         http://localhost:8000"
	@echo "  WebSocket:     ws://localhost:8000/ws"
	@echo "  Replay:        http://localhost:8000/api/replay"
	@echo ""
	@echo "📊 Metrics:"
	@echo "  Hunter:        http://localhost:8001/metrics"
	@echo "  Judge:         http://localhost:8002/metrics"
	@echo "  Guard:         http://localhost:8000/metrics"
	@echo "  Scribe:        http://localhost:8003/metrics"
	@echo ""
	@echo "🗄️  Database:"
	@echo "  TimescaleDB:   localhost:5432"
	@echo "  Database:      cerberus"
	@echo "  User:          cerberus_user"
