#!/bin/bash
# compile_protos.sh: Compile protobuf files for both services

set -e

echo "Compiling protobuf files..."

# Compile for brain service
echo "→ Compiling protos for brain service..."
python3 -m grpc_tools.protoc \
    -I=backend/protos \
    --python_out=backend/brain \
    --grpc_python_out=backend/brain \
    backend/protos/fraud.proto

# Compile for gateway service
echo "→ Compiling protos for gateway service..."
python3 -m grpc_tools.protoc \
    -I=backend/protos \
    --python_out=backend/gateway \
    --grpc_python_out=backend/gateway \
    backend/protos/fraud.proto

echo "✅ Proto compilation complete!"
echo ""
echo "Generated files:"
echo "  - backend/brain/fraud_pb2.py"
echo "  - backend/brain/fraud_pb2_grpc.py"
echo "  - backend/gateway/fraud_pb2.py"
echo "  - backend/gateway/fraud_pb2_grpc.py"
