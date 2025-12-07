#!/bin/bash
# quickstart.sh: One-command setup and run

set -e

echo "🛡️  Sentinel Fraud Detection System - Quick Start"
echo "=================================================="
echo ""

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Compile protos if not already done
if [ ! -f "backend/brain/fraud_pb2.py" ]; then
    echo "📦 Compiling proto files..."
    ./compile_protos.sh
    echo ""
fi

echo "🐳 Building and starting services with Docker Compose..."
echo ""

docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

echo ""
echo "✅ Sentinel is running!"
echo ""
echo "📍 Services:"
echo "   Gateway API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/health"
echo "   Circuit Status: http://localhost:8000/circuit/status"
echo ""
echo "🧪 Test Commands:"
echo "   # Health check"
echo "   curl http://localhost:8000/health"
echo ""
echo "   # Submit transaction"
echo "   curl -X POST http://localhost:8000/transaction \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"transaction_id\":\"txn_001\",\"amount\":150.50,\"currency\":\"USD\",\"user_id\":\"user_123\"}'"
echo ""
echo "   # Chaos test (install aiohttp first: pip install aiohttp)"
echo "   python test_chaos.py"
echo ""
echo "📊 View Logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop Services:"
echo "   docker-compose down"
echo ""
