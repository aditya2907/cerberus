import json
import logging
import os
from kafka import KafkaConsumer, KafkaProducer
from river import anomaly
from datetime import datetime
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - [Judge] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Kafka Configuration
KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")
INPUT_TOPIC = "market_data"
OUTPUT_TOPIC = "anomaly_alerts"

# Prometheus Metrics
TICKS_PROCESSED = Counter('ticks_processed_total', 'Total market ticks processed', ['service'])
ANOMALIES_DETECTED = Counter('anomalies_detected_total', 'Total anomalies detected')
PROCESSING_LAG = Gauge('judge_processing_lag_ms', 'Processing lag in milliseconds')
ANOMALY_SCORE = Histogram('anomaly_score', 'Distribution of anomaly scores')
PROCESSING_TIME = Histogram('judge_processing_time_seconds', 'Time to process each tick')

# Initialize River Online Learning Model
# Half-Space Trees - Great for streaming anomaly detection
model = anomaly.HalfSpaceTrees(
    n_trees=25,
    height=15,
    window_size=250,
    seed=42
)

logger.info("🤖 Online Learning Model (River HalfSpaceTrees) initialized")

# Kafka Consumer
consumer = KafkaConsumer(
    INPUT_TOPIC,
    bootstrap_servers=KAFKA_BROKER_URL,
    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
    auto_offset_reset='latest',
    enable_auto_commit=True,
    group_id='judge-anomaly-detector'
)

# Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER_URL,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

logger.info(f"Judge connected to Kafka at {KAFKA_BROKER_URL}")
logger.info(f"Consuming from: {INPUT_TOPIC}, Publishing to: {OUTPUT_TOPIC}")

# Adaptive threshold that learns from the data
anomaly_threshold = 0.8
tick_count = 0
scores_history = []


def calculate_features(tick):
    """Extract features from market tick for anomaly detection."""
    features = {
        'price': float(tick.get('price', 0)),
        'volume': float(tick.get('volume', 0)),
        'timestamp': float(tick.get('timestamp', time.time()))
    }
    return features


def adaptive_threshold(scores_history, percentile=95):
    """Dynamically adjust threshold based on score history."""
    if len(scores_history) < 50:
        return 0.8  # Default threshold
    
    import numpy as np
    return np.percentile(scores_history, percentile)


def publish_alert(tick, score, reason):
    """Publish anomaly alert to Kafka."""
    alert = {
        'type': 'AI_ANOMALY',
        'symbol': tick.get('symbol', 'UNKNOWN'),
        'price': tick.get('price'),
        'volume': tick.get('volume'),
        'score': float(score),
        'severity': 'HIGH' if score > 0.9 else 'MEDIUM',
        'details': reason,
        'timestamp': tick.get('timestamp', datetime.utcnow().isoformat()),
        'model': 'River_HalfSpaceTrees'
    }
    
    producer.send(OUTPUT_TOPIC, value=alert)
    logger.info(f"🚨 ANOMALY DETECTED: {alert['symbol']} - Score: {score:.4f}")
    ANOMALIES_DETECTED.inc()


def process_tick(tick):
    """Process a single market tick with online learning."""
    global tick_count, anomaly_threshold, scores_history
    
    start_time = time.time()
    tick_timestamp = float(tick.get('timestamp', time.time()))
    
    try:
        # Extract features
        features = calculate_features(tick)
        
        # Calculate anomaly score BEFORE learning (important!)
        score = model.score_one(features)
        
        # Track metrics
        ANOMALY_SCORE.observe(score)
        TICKS_PROCESSED.labels(service='judge').inc()
        tick_count += 1
        
        # Store score for adaptive thresholding
        scores_history.append(score)
        if len(scores_history) > 1000:
            scores_history = scores_history[-1000:]  # Keep last 1000 scores
        
        # Update adaptive threshold every 100 ticks
        if tick_count % 100 == 0:
            anomaly_threshold = adaptive_threshold(scores_history)
            logger.info(f"📊 Adaptive threshold updated: {anomaly_threshold:.4f}")
        
        # Check for anomaly
        if score > anomaly_threshold:
            reason = f"Online ML Model detected anomaly (confidence: {score:.2%}, threshold: {anomaly_threshold:.2%})"
            publish_alert(tick, score, reason)
        
        # Learn from this tick (model adapts in real-time!)
        model.learn_one(features)
        
        # Calculate processing lag
        current_time = time.time()
        lag_ms = (current_time - tick_timestamp) * 1000
        PROCESSING_LAG.set(lag_ms)
        
        # Track processing time
        processing_time = time.time() - start_time
        PROCESSING_TIME.observe(processing_time)
        
        if tick_count % 100 == 0:
            logger.info(f"✅ Processed {tick_count} ticks | Last score: {score:.4f} | Lag: {lag_ms:.2f}ms")
    
    except Exception as e:
        logger.error(f"Error processing tick: {e}", exc_info=True)


def main():
    """Main consumer loop."""
    # Start Prometheus metrics server
    start_http_server(8002)
    logger.info("📊 Prometheus metrics server started on port 8002")
    
    logger.info("🎯 Judge service started - Online Learning Mode Active")
    logger.info("🧠 Model will adapt to market conditions in real-time")
    
    try:
        for message in consumer:
            tick = message.value
            process_tick(tick)
    
    except KeyboardInterrupt:
        logger.info("Shutting down Judge service...")
    
    finally:
        consumer.close()
        producer.close()


if __name__ == "__main__":
    main()
