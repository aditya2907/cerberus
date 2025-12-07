import os
import json
import logging
import numpy as np
from collections import deque
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer
from river import anomaly
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time

# --- Configuration ---
# Load environment variables from .env file
load_dotenv(dotenv_path='../../.env')

# Kafka Configuration
KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")
CONSUMER_TOPIC = "market_data"
PRODUCER_TOPIC = "alerts"
GROUP_ID = "judge-group"

# Fraud Detection Configuration
PRICE_WINDOW_SIZE = 100  # Number of recent prices to keep for analysis
VOLATILITY_THRESHOLD = 2.5 # Standard deviation threshold to trigger an alert

# --- Prometheus Metrics ---
TICKS_PROCESSED = Counter('ticks_processed_total', 'Total market ticks processed', ['service'])
ANOMALIES_DETECTED = Counter('anomalies_detected_total', 'Total anomalies detected')
PROCESSING_LAG = Gauge('judge_processing_lag_ms', 'Processing lag in milliseconds')
ANOMALY_SCORE = Histogram('anomaly_score', 'Distribution of anomaly scores')
PROCESSING_TIME = Histogram('judge_processing_time_seconds', 'Time to process each tick')

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - [Judge] - %(levelname)s - %(message)s')

# --- Initialize River Online Learning Model ---
# Half-Space Trees - Great for streaming anomaly detection
online_model = anomaly.HalfSpaceTrees(
    n_trees=25,
    height=15,
    window_size=250,
    seed=42
)

logging.info(" Online Learning Model (River HalfSpaceTrees) initialized")

# --- In-Memory Price Storage ---
# A deque is used for efficient appends and pops from both ends
price_history = deque(maxlen=PRICE_WINDOW_SIZE)
scores_history = []
tick_count = 0
anomaly_threshold = 0.8

# --- Kafka Initialization ---
try:
    # Consumer to read from the 'market_data' topic
    consumer = KafkaConsumer(
        CONSUMER_TOPIC,
        bootstrap_servers=KAFKA_BROKER_URL,
        auto_offset_reset='latest',  # Start reading at the end of the log
        group_id=GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    logging.info(f"Successfully subscribed to Kafka topic '{CONSUMER_TOPIC}'")

    # Producer to send alerts to the 'alerts' topic
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER_URL,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    logging.info(f"Successfully connected to Kafka Broker for producing alerts to '{PRODUCER_TOPIC}'")

except Exception as e:
    logging.error(f"Failed to initialize Kafka clients: {e}")
    exit()

# --- Fraud Detection Logic ---
def adaptive_threshold(scores_history, percentile=95):
    """Dynamically adjust threshold based on score history."""
    if len(scores_history) < 50:
        return 0.8  # Default threshold
    return np.percentile(scores_history, percentile)


def detect_ai_anomaly(trade_data):
    """
    Uses River online learning to detect anomalies in real-time.
    The model learns from every tick and adapts to market conditions.
    """
    global tick_count, anomaly_threshold, scores_history
    
    start_time = time.time()
    
    # Extract features for the model
    features = {
        'price': float(trade_data.get('price', 0)),
        'volume': float(trade_data.get('size', 0))
    }
    
    # Calculate anomaly score BEFORE learning
    score = online_model.score_one(features)
    
    # Track metrics
    ANOMALY_SCORE.observe(score)
    TICKS_PROCESSED.labels(service='judge').inc()
    tick_count += 1
    
    # Store score for adaptive thresholding
    scores_history.append(score)
    if len(scores_history) > 1000:
        scores_history = scores_history[-1000:]
    
    # Update adaptive threshold every 100 ticks
    if tick_count % 100 == 0:
        anomaly_threshold = adaptive_threshold(scores_history)
        logging.info(f" Adaptive threshold updated: {anomaly_threshold:.4f}")
    
    # Learn from this tick (model adapts!)
    online_model.learn_one(features)
    
    # Track processing time
    processing_time = time.time() - start_time
    PROCESSING_TIME.observe(processing_time)
    
    # Check for anomaly
    if score > anomaly_threshold:
        ANOMALIES_DETECTED.inc()
        alert = {
            "type": "AI_ANOMALY",
            "symbol": trade_data.get('symbol'),
            "message": f"Online ML Model detected anomaly (confidence: {score:.2%})",
            "score": float(score),
            "threshold": float(anomaly_threshold),
            "price": trade_data.get('price'),
            "volume": trade_data.get('size'),
            "severity": "HIGH" if score > 0.9 else "MEDIUM",
            "timestamp": trade_data.get('timestamp'),
            "model": "River_HalfSpaceTrees"
        }
        return alert
    
    return None


def detect_spoofing(price_data):
    """
    Analyzes a window of prices to detect spoofing activity (high volatility).
    """
    if len(price_data) < PRICE_WINDOW_SIZE:
        # Not enough data to make a determination
        return None

    # Calculate the standard deviation of the prices
    prices = np.array(list(price_data))
    volatility = np.std(prices)

    if volatility > VOLATILITY_THRESHOLD:
        # If volatility exceeds the threshold, create an alert
        alert = {
            "type": "SPOOFING_DETECTED",
            "message": f"High volatility detected. Standard deviation of {volatility:.2f} exceeds threshold of {VOLATILITY_THRESHOLD}.",
            "volatility": volatility,
            "timestamp": price_data[-1]['timestamp'] # Use the timestamp of the latest trade
        }
        return alert
    
    return None

# --- Main Execution ---
if __name__ == "__main__":
    # Start Prometheus metrics server
    start_http_server(8002)
    logging.info(" Prometheus metrics server started on port 8002")
    
    logging.info(" Judge service starting - Online Learning Mode Active")
    logging.info(" Model will adapt to market conditions in real-time")
    logging.info(f"Consuming from: {CONSUMER_TOPIC}, Publishing to: {PRODUCER_TOPIC}")
    
    for message in consumer:
        try:
            trade_data = message.value
            price = trade_data.get('price')
            timestamp = trade_data.get('timestamp', time.time())

            if price is not None:
                # Calculate processing lag
                current_time = time.time()
                if isinstance(timestamp, str):
                    from datetime import datetime
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()
                    except:
                        timestamp = current_time
                
                lag_ms = (current_time - timestamp) * 1000
                PROCESSING_LAG.set(lag_ms)
                
                # Add the new price to history
                price_history.append({
                    "price": price,
                    "timestamp": timestamp
                })

                # Log progress
                if tick_count % 100 == 0:
                    logging.info(f" Processed {tick_count} ticks | Lag: {lag_ms:.2f}ms | Price: ${price:.2f}")

                # Run AI-based anomaly detection (Online Learning)
                ai_alert = detect_ai_anomaly(trade_data)
                if ai_alert:
                    logging.warning(f" AI ANOMALY: {ai_alert['message']}")
                    producer.send(PRODUCER_TOPIC, value=ai_alert)
                    producer.flush()

                # Run traditional rule-based fraud detection
                rule_alert = detect_spoofing(price_history)
                if rule_alert:
                    logging.warning(f"  RULE-BASED ALERT: {rule_alert['message']}")
                    producer.send(PRODUCER_TOPIC, value=rule_alert)
                    producer.flush()

        except json.JSONDecodeError:
            logging.error(f"Failed to decode message: {message.value}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
