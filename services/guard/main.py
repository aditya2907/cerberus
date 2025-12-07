import os
import json
import asyncio
import logging
import threading
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer
from prometheus_client import Counter, Gauge, make_asgi_app
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# --- Configuration ---
# Load environment variables from .env file
load_dotenv(dotenv_path='../../.env')

# Kafka Configuration
KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")
CONSUMER_TOPIC = "alerts"
GROUP_ID = "guard-group"

# PostgreSQL/TimescaleDB Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "timescaledb")
POSTGRES_DB = os.getenv("POSTGRES_DB", "cerberus")
POSTGRES_USER = os.getenv("POSTGRES_USER", "cerberus_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "cerberus_pass")

# Prometheus Metrics
WEBSOCKET_CONNECTIONS = Gauge('guard_websocket_connections', 'Active WebSocket connections')
ALERTS_BROADCAST = Counter('guard_alerts_broadcast_total', 'Total alerts broadcast to clients')
REPLAY_REQUESTS = Counter('guard_replay_requests_total', 'Total replay requests')

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - [Guard] - %(levelname)s - %(message)s')

# --- FastAPI Application ---
app = FastAPI(title="Project Cerberus - Guard Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# --- Connection Manager for WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        WEBSOCKET_CONNECTIONS.set(len(self.active_connections))
        logging.info(f"New client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        WEBSOCKET_CONNECTIONS.set(len(self.active_connections))
        logging.info(f"Client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        # Send a message to all connected clients
        ALERTS_BROADCAST.inc()
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Kafka Consumer in a Background Thread ---
def consume_alerts():
    """
    This function runs in a separate thread to consume Kafka messages
    and broadcast them to WebSocket clients.
    """
    try:
        consumer = KafkaConsumer(
            CONSUMER_TOPIC,
            bootstrap_servers=KAFKA_BROKER_URL,
            auto_offset_reset='latest',
            group_id=GROUP_ID,
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))
        )
        logging.info(f"Successfully subscribed to Kafka topic '{CONSUMER_TOPIC}' for alerts.")

        for message in consumer:
            alert_data = message.value
            logging.info(f"Received alert: {alert_data}")
            
            # Create an asyncio task to run the broadcast function
            # on the main event loop where FastAPI is running.
            asyncio.run(manager.broadcast(json.dumps(alert_data)))

    except Exception as e:
        logging.error(f"Kafka consumer thread failed: {e}")

# --- FastAPI Endpoints ---
@app.on_event("startup")
async def startup_event():
    """
    On startup, create and start the Kafka consumer thread.
    """
    logging.info("Guard service starting up...")
    consumer_thread = threading.Thread(target=consume_alerts, daemon=True)
    consumer_thread.start()
    logging.info("Kafka consumer thread started.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    The main WebSocket endpoint for clients to connect to.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive. The client can send pings
            # or other messages if needed, but for now, we just wait.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "guard"}


@app.get("/api/replay")
async def replay_historical_data(
    start_time: str = Query(..., description="Start time in ISO format"),
    end_time: str = Query(..., description="End time in ISO format"),
    speed: float = Query(1.0, description="Playback speed multiplier (e.g., 2.0 for 2x speed)")
):
    """
    Replay Mode: Stream historical market data from TimescaleDB.
    
    Example: /api/replay?start_time=2024-01-01T14:00:00Z&end_time=2024-01-01T15:00:00Z&speed=2.0
    """
    REPLAY_REQUESTS.inc()
    
    try:
        # Connect to TimescaleDB
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query historical data
        query = """
            SELECT time, symbol, price, volume, exchange
            FROM market_data
            WHERE time BETWEEN %s AND %s
            ORDER BY time ASC
        """
        
        cursor.execute(query, (start_time, end_time))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "symbol": row['symbol'],
                "price": float(row['price']),
                "volume": float(row['volume']) if row['volume'] else 0,
                "exchange": row['exchange'],
                "timestamp": row['time'].isoformat(),
                "replay": True
            })
        
        cursor.close()
        conn.close()
        
        logging.info(f"📼 Replay request: {len(results)} records from {start_time} to {end_time} at {speed}x speed")
        
        return {
            "status": "success",
            "records": len(results),
            "data": results,
            "speed": speed,
            "start_time": start_time,
            "end_time": end_time
        }
    
    except Exception as e:
        logging.error(f"Replay error: {e}")
        return {"status": "error", "message": str(e)}
