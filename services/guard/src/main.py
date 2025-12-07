from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import grpc
import logging
import pybreaker
import os
import asyncio
from functools import partial

# Import generated gRPC code
import sys
sys.path.append('../brain')
import fraud_pb2
import fraud_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sentinel Fraud Detection Gateway")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Next.js dev server (if needed)
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Environment variables
BRAIN_SERVICE_HOST = os.getenv("BRAIN_SERVICE_HOST", "localhost:50051")

# Circuit Breaker configuration
circuit_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)


# Pydantic Models for request and response
class Location(BaseModel):
    ip_address: str = Field(..., example="192.168.1.1")
    country: str = Field(..., example="USA")

class Transaction(BaseModel):
    transaction_id: str = Field(..., example="txn-12345")
    user_id: str = Field(..., example="user-67890")
    amount: float = Field(..., example=125.50)
    currency: str = Field(..., example="USD")
    timestamp: str = Field(..., example="2023-10-27T10:00:00Z")
    merchant_id: str = Field(..., example="merchant-abc")
    payment_method: str = Field(..., example="credit_card")
    location: Location

class TransactionResponse(BaseModel):
    transaction_id: str
    is_fraud: bool
    risk_score: float
    reason: str
    circuit_state: str


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "circuit_state": circuit_breaker.current_state,
        "service": "sentinel-gateway"
    }


@app.get("/circuit/status")
async def circuit_status():
    """Get circuit breaker status."""
    state = circuit_breaker.current_state
    return {
        "state": state,
        "fail_counter": circuit_breaker.fail_counter,
        "fail_max": circuit_breaker.fail_max,
        "reset_timeout": circuit_breaker.reset_timeout
    }


# Correctly define the function that will be protected by the circuit breaker
async def call_fraud_detection_service(transaction: Transaction) -> fraud_pb2.RiskAssessment:
    """
    Calls the fraud detection gRPC service asynchronously.
    The blocking gRPC call is run in a separate thread to avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    
    # Define the synchronous gRPC call that will be wrapped by the circuit breaker
    @circuit_breaker
    def grpc_call():
        with grpc.insecure_channel(BRAIN_SERVICE_HOST) as channel:
            stub = fraud_pb2_grpc.FraudDetectionServiceStub(channel)
            request = fraud_pb2.TransactionInfo(
                transaction_id=transaction.transaction_id,
                user_id=transaction.user_id,
                amount=transaction.amount,
                currency=transaction.currency,
                timestamp=transaction.timestamp,
                merchant_id=transaction.merchant_id,
                payment_method=transaction.payment_method,
                location=fraud_pb2.LocationInfo(
                    ip_address=transaction.location.ip_address,
                    country=transaction.location.country
                )
            )
            return stub.CheckTransaction(request)
    
    try:
        # Use run_in_executor to run the circuit-breaker-protected blocking call in a thread pool
        return await loop.run_in_executor(None, grpc_call)
    except grpc.RpcError as e:
        logging.error(f"gRPC call failed: {e.details()}")
        raise e # Re-raise to be caught by the circuit breaker


@app.post("/transaction", response_model=TransactionResponse)
async def check_transaction(transaction: Transaction):
    """
    Receives a transaction, calls the fraud detection service,
    and returns a risk assessment.
    """
    try:
        logging.info(f"Processing transaction: {transaction.transaction_id}")
        
        grpc_response = await call_fraud_detection_service(transaction)

        response = TransactionResponse(
            transaction_id=transaction.transaction_id,
            is_fraud=grpc_response.is_fraud,
            risk_score=grpc_response.risk_score,
            reason=grpc_response.reason,
            circuit_state=str(circuit_breaker.current_state)
        )
        logging.info(f"Transaction processed successfully: {transaction.transaction_id}")
        return response

    except pybreaker.CircuitBreakerError:
        logging.warning(f"Circuit breaker is open. Defaulting to safe response for transaction {transaction.transaction_id}")
        return TransactionResponse(
            transaction_id=transaction.transaction_id,
            is_fraud=False,
            risk_score=0.0,
            reason="Circuit breaker is open. Service is temporarily unavailable.",
            circuit_state=str(circuit_breaker.current_state)
        )
    except Exception as e:
        logging.error(f"An unexpected error occurred for transaction {transaction.transaction_id}: {e}", exc_info=True)
        return TransactionResponse(
            transaction_id=transaction.transaction_id,
            is_fraud=False,
            risk_score=0.0,
            reason=f"Service error - defaulting to safe response: {e}",
            circuit_state=str(circuit_breaker.current_state)
        )


# Main entry point for running the app with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
