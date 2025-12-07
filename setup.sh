#!/bin/bash
# setup.sh: Scaffold Sentinel monorepo structure

set -e

# Create backend structure
mkdir -p backend/gateway
mkdir -p backend/brain

touch backend/gateway/__init__.py

touch backend/brain/__init__.py

# Create frontend structure
mkdir -p dashboard

# Create infra structure
mkdir -p infra/k8s
mkdir -p infra/docker

echo "Scaffold complete."
