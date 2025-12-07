import os
import json
import logging
import psycopg2
from psycopg2.extras import execute_batch
from kafka import KafkaConsumer
from datetime import datetime
from prometheus_client import Counter, Gauge, start_http_server
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - [Scribe] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_DB = os.getenv("POSTGRES_DB", "cerberus")
POSTGRES_USER = os.getenv("POSTGRES_USER", "cerberus_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "cerberus_pass")
KAFKA_TOPIC = "market_data"

# Prometheus Metrics
RECORDS_WRITTEN = Counter('scribe_records_written_total', 'Total records written to TimescaleDB')
BATCH_SIZE_METRIC = Gauge('scribe_batch_size', 'Current batch size')
WRITE_LATENCY = Gauge('scribe_write_latency_ms', 'Write latency to database')

# Batch configuration
BATCH_SIZE = 100
BATCH_TIMEOUT = 5  # seconds

def init_database():
    """Initialize TimescaleDB with hypertable."""
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Create extension if not exists
    cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    
    # Create market_data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            time TIMESTAMPTZ NOT NULL,
            symbol TEXT NOT NULL,
            price DOUBLE PRECISION NOT NULL,
            volume DOUBLE PRECISION,
            exchange TEXT,
            conditions TEXT[],
            tape TEXT
        );
    """)
    
    # Convert to hypertable (if not already)
    try:
        cursor.execute("""
            SELECT create_hypertable('market_data', 'time', 
                                      if_not_exists => TRUE);
        """)
        logger.info(" Hypertable 'market_data' created successfully")
    except Exception as e:
        logger.warning(f"Hypertable might already exist: {e}")
    
    # Create index for better query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_symbol_time 
        ON market_data (symbol, time DESC);
    """)
    
    cursor.close()
    conn.close()
    logger.info("  Database initialized successfully")


def insert_batch(conn, batch):
    """Insert a batch of records into TimescaleDB."""
    if not batch:
        return
    
    start_time = time.time()
    cursor = conn.cursor()
    
    insert_query = """
        INSERT INTO market_data (time, symbol, price, volume, exchange, conditions, tape)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        execute_batch(cursor, insert_query, batch)
        conn.commit()
        
        # Track metrics
        RECORDS_WRITTEN.inc(len(batch))
        write_time = (time.time() - start_time) * 1000
        WRITE_LATENCY.set(write_time)
        
        logger.info(f" Wrote batch of {len(batch)} records in {write_time:.2f}ms")
    except Exception as e:
        logger.error(f"Error inserting batch: {e}")
        conn.rollback()
    finally:
        cursor.close()


def main():
    """Main consumer loop."""
    # Start Prometheus metrics server
    start_http_server(8003)
    logger.info(" Prometheus metrics server started on port 8003")
    
    # Initialize database
    init_database()
    
    # Connect to database
    db_conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    
    # Create Kafka consumer
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER_URL,
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id='scribe-recorder'
    )
    
    logger.info(f" Scribe started - Recording from '{KAFKA_TOPIC}' to TimescaleDB")
    
    batch = []
    last_batch_time = time.time()
    
    try:
        for message in consumer:
            tick = message.value
            
            # Parse timestamp
            try:
                if isinstance(tick.get('timestamp'), str):
                    ts = datetime.fromisoformat(tick['timestamp'].replace('Z', '+00:00'))
                else:
                    ts = datetime.fromtimestamp(tick.get('timestamp', time.time()))
            except:
                ts = datetime.now()
            
            # Prepare record
            record = (
                ts,
                tick.get('symbol', 'UNKNOWN'),
                float(tick.get('price', 0)),
                float(tick.get('size', 0)),
                tick.get('exchange'),
                tick.get('conditions', []),
                tick.get('tape')
            )
            
            batch.append(record)
            BATCH_SIZE_METRIC.set(len(batch))
            
            # Insert batch if size or timeout reached
            if len(batch) >= BATCH_SIZE or (time.time() - last_batch_time) >= BATCH_TIMEOUT:
                insert_batch(db_conn, batch)
                batch = []
                last_batch_time = time.time()
    
    except KeyboardInterrupt:
        logger.info("Shutting down Scribe service...")
        # Write remaining batch
        if batch:
            insert_batch(db_conn, batch)
    
    finally:
        consumer.close()
        db_conn.close()


if __name__ == "__main__":
    main()
