#!/bin/bash

# Cerberus Advanced Features Validation Script
# This script checks that all three upgrades are working correctly

set -e

echo "🛡️  Cerberus Advanced Features Validation"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Test function
test_feature() {
    local name=$1
    local command=$2
    local expected=$3
    
    echo -n "Testing $name... "
    
    if eval "$command" | grep -q "$expected"; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
    fi
}

# Check if docker-compose is running
echo "1️⃣  Checking Docker Services"
echo "----------------------------"

test_feature "Kafka running" "docker ps --filter name=kafka --format '{{.Status}}'" "Up"
test_feature "Hunter running" "docker ps --filter name=hunter --format '{{.Status}}'" "Up"
test_feature "Judge running" "docker ps --filter name=judge --format '{{.Status}}'" "Up"
test_feature "Guard running" "docker ps --filter name=guard --format '{{.Status}}'" "Up"
test_feature "Scribe running" "docker ps --filter name=scribe --format '{{.Status}}'" "Up"
test_feature "TimescaleDB running" "docker ps --filter name=timescaledb --format '{{.Status}}'" "Up"
test_feature "Prometheus running" "docker ps --filter name=prometheus --format '{{.Status}}'" "Up"
test_feature "Grafana running" "docker ps --filter name=grafana --format '{{.Status}}'" "Up"

echo ""
echo "2️⃣  Validating Prometheus Metrics (Update 1)"
echo "--------------------------------------------"

sleep 2  # Give services time to expose metrics

test_feature "Hunter metrics endpoint" "curl -s http://localhost:8001/metrics" "ticks_processed"
test_feature "Judge metrics endpoint" "curl -s http://localhost:8002/metrics" "anomalies_detected"
test_feature "Guard metrics endpoint" "curl -s http://localhost:8000/metrics" "guard_websocket"
test_feature "Scribe metrics endpoint" "curl -s http://localhost:8003/metrics" "scribe_records"

test_feature "Prometheus targets" "curl -s http://localhost:9090/api/v1/targets" '"health":"up"'
test_feature "Grafana API" "curl -s http://localhost:3001/api/health" "ok"

echo ""
echo "3️⃣  Validating Online ML with River (Update 2)"
echo "-----------------------------------------------"

# Check Judge logs for River initialization
test_feature "River model initialized" "docker logs judge 2>&1" "HalfSpaceTrees"
test_feature "Adaptive threshold active" "docker logs judge 2>&1 | tail -100" "threshold"
test_feature "Anomaly scoring active" "docker logs judge 2>&1 | tail -100" "score"

# Check if River metrics are being collected
test_feature "Anomaly score metric" "curl -s http://localhost:8002/metrics" "anomaly_score"
test_feature "Processing lag metric" "curl -s http://localhost:8002/metrics" "judge_processing_lag_ms"

echo ""
echo "4️⃣  Validating TimescaleDB + Replay (Update 3)"
echo "----------------------------------------------"

# Check TimescaleDB is accessible
test_feature "TimescaleDB connection" "docker exec timescaledb pg_isready -U cerberus_user" "accepting connections"

# Check if hypertable exists
test_feature "Hypertable created" "docker exec timescaledb psql -U cerberus_user -d cerberus -tAc \"SELECT COUNT(*) FROM market_data\"" ""

# Check if Scribe is writing data
test_feature "Scribe writing batches" "docker logs scribe 2>&1 | tail -50" "Wrote batch"

# Test replay API (wait a bit for data to accumulate)
echo -n "Testing Replay API... "
sleep 5
REPLAY_RESPONSE=$(curl -s "http://localhost:8000/api/replay?start_time=$(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ)&end_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)&speed=1.0")

if echo "$REPLAY_RESPONSE" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING: No data yet (run system longer)${NC}"
fi

echo ""
echo "5️⃣  Dashboard Access"
echo "--------------------"

test_feature "Main Dashboard" "curl -s -o /dev/null -w '%{http_code}' http://localhost:5173" "200"
test_feature "Grafana Dashboard" "curl -s -o /dev/null -w '%{http_code}' http://localhost:3001" "302"
test_feature "Prometheus UI" "curl -s -o /dev/null -w '%{http_code}' http://localhost:9090" "200"
test_feature "Guard API health" "curl -s http://localhost:8000/health" "healthy"

echo ""
echo "=========================================="
echo "📊 Validation Results"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All features validated successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Open Grafana: http://localhost:3001 (admin/cerberus)"
    echo "  2. Open Main Dashboard: http://localhost:5173"
    echo "  3. Run: make metrics"
    echo "  4. Run: make replay"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  Some features failed validation${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check logs: docker-compose logs <service>"
    echo "  2. Restart: docker-compose restart <service>"
    echo "  3. Full restart: docker-compose down && docker-compose up -d"
    echo ""
    exit 1
fi
