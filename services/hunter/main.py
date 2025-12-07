import os
import json
import logging
from dotenv import load_dotenv
from kafka import KafkaProducer
from alpaca.data.live.stock import StockDataStream
from prometheus_client import Counter, start_http_server
import threading

# --- Configuration ---
# Load environment variables from .env file (assuming it's in the project root)
load_dotenv(dotenv_path='../../.env')

# Alpaca API Configuration
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Kafka Configuration
KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")
KAFKA_TOPIC = "market_data"

# Trading Symbol to Watch
SYMBOL = "SPY"

# Prometheus Metrics
TICKS_PROCESSED = Counter('ticks_processed_total', 'Total market ticks processed', ['service'])

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - [Hunter] - %(levelname)s - %(message)s')

# --- Kafka Producer Initialization ---
try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER_URL,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8')
    )
    logging.info(f"Successfully connected to Kafka Broker at {KAFKA_BROKER_URL}")
except Exception as e:
    logging.error(f"Failed to connect to Kafka Broker: {e}")
    # Exit if we can't connect to Kafka, as it's essential for the service
    exit()

# --- Alpaca WebSocket Client ---
# The websocket client is designed to run in an async environment
wss_client = StockDataStream(ALPACA_API_KEY, ALPACA_SECRET_KEY)

async def on_trade(trade):
    """
    This function is called for every trade event received from the WebSocket.
    It processes the trade data and sends it to a Kafka topic.
    """
    try:
        # Convert trade data to a dictionary
        trade_data = {
            "symbol": trade.symbol,
            "price": trade.price,
            "size": trade.size,
            "timestamp": trade.timestamp.isoformat(),
            "exchange": trade.exchange,
            "conditions": trade.conditions,
            "tape": trade.tape
        }
        
        # Log the received trade
        logging.info(f"Received trade for {trade.symbol}: Price=${trade.price:.2f}, Size={trade.size}")

        # Send the trade data to the Kafka topic
        # The symbol is used as the key for partitioning
        producer.send(KAFKA_TOPIC, key=trade.symbol, value=trade_data)
        
        # Track metrics
        TICKS_PROCESSED.labels(service='hunter').inc()
        
        # The flush() is important to ensure messages are sent immediately,
        # especially in a low-volume environment.
        producer.flush()

    except Exception as e:
        logging.error(f"Error processing trade: {e}")
        logging.error(f"Problematic trade data: {trade}")

# --- Main Execution ---
if __name__ == "__main__":
    # Start Prometheus metrics server in a separate thread
    def start_metrics_server():
        start_http_server(8001)
        logging.info("📊 Prometheus metrics server started on port 8001")
    
    metrics_thread = threading.Thread(target=start_metrics_server, daemon=True)
    metrics_thread.start()
    
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        logging.error("Alpaca API Key or Secret Key not found. Please set them in the .env file.")
    else:
        logging.info(f"🎯 Hunter service starting. Subscribing to trades for symbol: {SYMBOL}")
        # Subscribe to the trade handler
        wss_client.subscribe_trades(on_trade, SYMBOL)
        # Start the WebSocket client
        wss_client.run()
