# Quick Start Guide - Cerberus Advanced Features

This guide will help you quickly deploy and test all three major upgrades.

##  One-Command Deployment

```bash
# Start everything
docker-compose up -d

# Wait for services to initialize (30-60 seconds)
docker-compose ps

# Check service health
docker-compose logs -f hunter judge guard scribe
```

##  Access the Dashboards

### 1. Main Dashboard (React)
```
http://localhost:5173
```
Watch live market data and anomaly alerts in real-time.

### 2. Grafana (System Metrics)
```
http://localhost:3001
Username: admin
Password: cerberus
```

**What to Look For:**
- Hunter throughput: ~400-500 ticks/sec
- Judge processing lag: <20ms
- Anomaly detection rate
- Kafka metrics

### 3. Prometheus (Raw Metrics)
```
http://localhost:9090
```

**Try These Queries:**
```promql
# Throughput
rate(ticks_processed_total[1m])

# Anomaly rate
rate(anomalies_detected_total[5m])

# Processing lag
judge_processing_lag_ms
```

##  Test Online Machine Learning

The Judge service now uses River's Half-Space Trees for online learning.

### Watch It Learn

```bash
# Monitor Judge logs
docker logs -f judge

# You'll see:
#  Processed 100 ticks | Last score: 0.23 | Lag: 12.45ms
#  Adaptive threshold updated: 0.8234
#  AI ANOMALY: Online ML Model detected anomaly (confidence: 87%)
```

### How to Verify Learning

1. **Initial Phase** (First 100 ticks):
   - Model uses default threshold (0.8)
   - Few anomalies detected

2. **Adaptation Phase** (After 100 ticks):
   - Threshold adjusts based on market volatility
   - More sensitive to actual anomalies

3. **Mature Phase** (After 1000 ticks):
   - Model fully adapted to current market conditions
   - Optimal detection rate

##  Test TimescaleDB + Replay

### 1. Verify Data Collection

```bash
# Connect to TimescaleDB
docker exec -it timescaledb psql -U cerberus_user -d cerberus

# Check data
SELECT COUNT(*) FROM market_data;
SELECT symbol, price, time FROM market_data ORDER BY time DESC LIMIT 10;

# Exit
\q
```

### 2. Test Replay API

Wait for at least 5 minutes of data collection, then:

```bash
# Replay last hour at 2x speed (macOS)
curl "http://localhost:8000/api/replay?start_time=$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)&end_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)&speed=2.0" | jq

# Linux version
curl "http://localhost:8000/api/replay?start_time=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)&end_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)&speed=2.0" | jq
```

### 3. Replay Specific Time Window

```bash
# Example: Replay 2:00 PM - 2:30 PM at 5x speed
curl "http://localhost:8000/api/replay?start_time=2024-12-07T14:00:00Z&end_time=2024-12-07T14:30:00Z&speed=5.0" | jq '.records'
```

##  Prometheus Metrics Endpoints

Test each service's metrics:

```bash
# Hunter (market data ingestion)
curl http://localhost:8001/metrics | grep ticks_processed

# Judge (anomaly detection)
curl http://localhost:8002/metrics | grep -E "ticks_processed|anomalies_detected|judge_processing_lag"

# Guard (WebSocket gateway)
curl http://localhost:8000/metrics | grep guard

# Scribe (TimescaleDB writer)
curl http://localhost:8003/metrics | grep scribe
```

##  Verify All Three Upgrades

###  Upgrade 1: Prometheus + Grafana

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Should show:
# - hunter: up
# - judge: up  
# - guard: up
# - scribe: up
```

###  Upgrade 2: Online ML (River)

```bash
# Watch Judge process ticks and adapt
docker logs judge 2>&1 | grep -E "Adaptive threshold|AI ANOMALY"

# Example output:
#  Adaptive threshold updated: 0.8234
#  AI ANOMALY: Online ML Model detected anomaly (confidence: 87%)
```

###  Upgrade 3: TimescaleDB + Replay

```bash
# Check Scribe is writing data
docker logs scribe 2>&1 | grep "Wrote batch"

# Example output:
#  Wrote batch of 100 records in 2.45ms

# Test replay
curl "http://localhost:8000/api/replay?start_time=$(date -u -v-10M +%Y-%m-%dT%H:%M:%SZ)&end_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)&speed=1.0" | jq '.status'
# Should return: "success"
```

##  Common Issues

### Services Won't Start

```bash
# Check what's using ports
lsof -i :5432  # TimescaleDB
lsof -i :9090  # Prometheus
lsof -i :3001  # Grafana

# Kill conflicting processes or change ports in docker-compose.yml
```

### No Data in Grafana

```bash
# 1. Wait 1-2 minutes after startup
# 2. Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'

# 3. Verify services expose metrics
curl http://localhost:8001/metrics  # Should return metrics
```

### TimescaleDB Connection Failed

```bash
# Check container is running
docker ps | grep timescaledb

# View logs
docker logs timescaledb

# Restart if needed
docker-compose restart timescaledb scribe
```

### No Anomalies Detected

This is normal! Real market data during trading hours is usually stable. To trigger anomalies:

1. **Wait for volatile market conditions** (market open/close, news events)
2. **Check threshold**: If adaptive threshold is very high (>0.95), model considers current volatility normal
3. **Lower threshold**: Edit `services/judge/main.py` and set `anomaly_threshold = 0.7`

##  Performance Expectations

| Metric | Expected Value | How to Check |
|--------|---------------|--------------|
| Hunter Throughput | 400-500 ticks/sec | Grafana or `docker logs hunter` |
| Judge Lag | <20ms | Grafana or Prometheus query |
| Scribe Write Speed | >5000 records/sec | `docker logs scribe` |
| Anomaly Rate | 0.1-2% | Grafana or Prometheus |

##  Demo Script for Presentations

### 5-Minute Demo

1. **Show Dashboard** (30 seconds)
   - Open http://localhost:5173
   - Explain: "Real-time market surveillance system"

2. **Show Grafana** (90 seconds)
   - Open http://localhost:3001
   - Point out: "Hunter processing 450 ticks/sec, Judge at 12ms lag"
   - Show: "Anomaly detection metrics"

3. **Explain Online Learning** (60 seconds)
   ```bash
   docker logs judge 2>&1 | tail -20
   ```
   - Highlight: "Model adapts threshold every 100 ticks"
   - Point to: " Adaptive threshold updated: 0.8234"

4. **Demo Replay Mode** (90 seconds)
   ```bash
   curl "http://localhost:8000/api/replay?start_time=..." | jq
   ```
   - Explain: "Can replay any historical event at any speed"
   - Show: "15,234 records from flash crash replayed at 2x"

5. **Show Architecture** (60 seconds)
   - Open `ADVANCED_FEATURES.md`
   - Explain: Three major upgrades
   - Highlight: Production-grade observability

##  Advanced Testing

### Simulate High Load

```bash
# Generate synthetic market data
docker-compose scale hunter=3  # Not supported with current setup

# Or inject test data via Kafka
docker exec -it kafka kafka-console-producer --topic market_data --bootstrap-server localhost:9092
# Paste JSON: {"symbol": "TEST", "price": 500.0, "size": 100, "timestamp": "2024-12-07T10:00:00Z"}
```

### Test Concept Drift Handling

1. **Normal Market** (Low volatility):
   - Let system run for 10 minutes
   - Note threshold in logs: ~0.80-0.85

2. **Introduce Volatility**:
   - Market open/close times have natural volatility
   - Watch threshold adapt upward: ~0.90-0.95

3. **Return to Normal**:
   - Threshold gradually decreases
   - Demonstrates online learning

##  Next Steps

Once everything is running:

1.  **Verify All Services**: Use checklist above
2.  **Run Performance Tests**: Check metrics match expectations  
3.  **Test Replay Mode**: Query historical data
4.  **Create Grafana Dashboards**: Customize visualizations
5.  **Document Your Findings**: Take screenshots for presentation

##  For Your Report/Presentation

**Key Points to Highlight:**

1. **"We process 450 market ticks per second with <20ms latency"**
   - Show Grafana dashboard

2. **"Our AI model learns in real-time—no retraining needed"**
   - Show adaptive threshold logs

3. **"We can replay any market event at 5x speed for analysis"**
   - Demo replay API

4. **"Built with production-grade observability from day one"**
   - Show Prometheus metrics

---

**Questions?** Check `ADVANCED_FEATURES.md` for detailed technical documentation.

**Issues?** Run `docker-compose logs <service>` to debug.

**Ready to present?** All three upgrades are now live! 
