import grpc
from pymongo import MongoClient
from concurrent import futures
import logging
import os
import joblib
import numpy as np
from datetime import datetime

# Import generated gRPC code
import fraud_pb2
import fraud_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the trained model
MODEL_PATH = os.getenv("MODEL_PATH", "fraud_model.joblib")
try:
    model = joblib.load(MODEL_PATH)
    logger.info(f"Model loaded successfully from {MODEL_PATH}")
except FileNotFoundError:
    logger.warning(f"Model file not found at {MODEL_PATH}. Using rule-based fallback.")
    model = None
except Exception as e:
    logger.error(f"Error loading model: {e}. Using rule-based fallback.")
    model = None


# MongoDB connection setup
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URL)
db = client.fraud_detection_db
transactions_collection = db.transactions


# Define the gRPC Servicer
class FraudDetectionServicer(fraud_pb2_grpc.FraudDetectionServiceServicer):
    def __init__(self):
        # Country mapping for model input
        self.country_map = {
            'USA': 0, 'US': 0,
            'Ireland': 1, 'IE': 1, 'IRL': 1,
            'Russia': 2, 'RU': 2, 'RUS': 2
        }
    
    def _extract_features(self, request):
        """Extract features from the transaction request for model prediction."""
        # Extract hour from timestamp
        try:
            timestamp = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
            hour = timestamp.hour
        except Exception as e:
            logger.warning(f"Could not parse timestamp: {e}. Using default hour=12")
            hour = 12
        
        # Map country to code (default to 0 if unknown)
        country_code = self.country_map.get(request.location.country.upper(), 0)
        
        # Create feature array: [amount, hour, country_code]
        features = np.array([[request.amount, hour, country_code]])
        return features
    
    def CheckTransaction(self, request, context):
        """
        Analyzes a transaction to determine if it's fraudulent using ML model.
        """
        logger.info(
            f"Received transaction check request: "
            f"id={request.transaction_id}, "
            f"amount={request.amount}, "
            f"currency={request.currency}, "
            f"user_id={request.user_id}, "
            f"country={request.location.country}"
        )
        
        if model is not None:
            try:
                # Extract features and make prediction
                features = self._extract_features(request)
                prediction = model.predict(features)[0]
                prediction_proba = model.predict_proba(features)[0]
                
                is_fraud = bool(prediction)
                risk_score = float(prediction_proba[1])  # Probability of fraud class
                
                if is_fraud:
                    reason = f"ML Model detected fraud (confidence: {risk_score:.2%})"
                else:
                    reason = f"ML Model: Transaction appears legitimate (fraud risk: {risk_score:.2%})"
                
                logger.info(
                    f"Transaction {request.transaction_id}: "
                    f"IsFraud={is_fraud}, RiskScore={risk_score:.4f}"
                )
            except Exception as e:
                logger.error(f"Error during model prediction: {e}. Falling back to rule-based logic.")
                # Fall back to rule-based logic
                is_fraud, risk_score, reason = self._rule_based_check(request)
        else:
            # Use rule-based logic if model is not available
            logger.info("Using rule-based fallback logic")
            is_fraud, risk_score, reason = self._rule_based_check(request)

        return fraud_pb2.RiskAssessment(
            is_fraud=is_fraud,
            risk_score=risk_score,
            reason=reason
        )
    
    def _rule_based_check(self, request):
        """Fallback rule-based fraud detection."""
        if request.amount > 10000:
            is_fraud = True
            risk_score = 0.9
            reason = "Rule-based: Transaction amount exceeds the high-value threshold."
        else:
            is_fraud = False
            risk_score = 0.1
            reason = "Rule-based: Transaction is within normal parameters."
        
        logger.info(
            f"Transaction {request.transaction_id}: "
            f"IsFraud={is_fraud}, RiskScore={risk_score}"
        )
        return is_fraud, risk_score, reason


def serve():
    """Start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    fraud_pb2_grpc.add_FraudDetectionServiceServicer_to_server(
        FraudDetectionServicer(), server
    )
    
    port = "50051"
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    
    logger.info(f"gRPC Fraud Detection server started on port {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(0)


if __name__ == "__main__":
    serve()
