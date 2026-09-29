#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "=== [1/3] Building ChainSentry Frontend SPA ==="
cd frontend
npm ci
npm run build
cd ..

echo "=== [2/3] Installing Python Dependencies ==="
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "=== [3/3] Initializing Database Schema ==="
python -c "from backend.chainsentry_common.db import init_db; init_db()"

echo "=== ChainSentry Build Complete! Ready for deployment. ==="
