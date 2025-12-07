import asyncio
import json
import os
import websockets
from kafka import KafkaProducer

# CONFIGURATION
# We listen to Bitcoin (btcusdt) and Ethereum (ethusdt)
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@aggTrade/ethusdt@aggTrade"
KAFKA_TOPIC = "market_data"
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:29092')

# SETUP KAFKA PRODUCER
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

async def binance_listener():
    print(f"🏹 Hunter connecting to Binance Stream: {BINANCE_WS_URL}")
    
    async with websockets.connect(BINANCE_WS_URL) as websocket:
        while True:
            try:
                # 1. Receive Raw Message
                message = await websocket.recv()
                data = json.loads(message)
                
                # 2. Transform Data (Normalize it for The Judge)
                # Binance keys are short: 's'=symbol, 'p'=price, 'q'=quantity, 'T'=timestamp
                payload = {
                    "symbol": data['s'],      # e.g., "BTCUSDT"
                    "price": float(data['p']),
                    "size": float(data['q']),
                    "timestamp": data['T']    # Unix ms timestamp
                }
                
                # 3. Log it (so you see it working)
                print(f"⚡ Trade: {payload['symbol']} @ {payload['price']}")
                
                # 4. Push to Kafka
                producer.send(KAFKA_TOPIC, payload)
                
            except Exception as e:
                print(f"Error processing message: {e}")
                await asyncio.sleep(1) # Prevent tight loops on error

if __name__ == "__main__":
    # Wait for Kafka to boot up (simple retry logic)
    print("Hunter waiting 10s for Kafka to warm up...")
    asyncio.run(asyncio.sleep(10)) 
    
    # Start the Loop
    asyncio.run(binance_listener())