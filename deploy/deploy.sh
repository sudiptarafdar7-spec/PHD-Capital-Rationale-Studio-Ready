#!/bin/bash

set -e

APP_NAME="phd-capital"
APP_DIR="/home/phd/app"
ENV_FILE="/etc/${APP_NAME}.env"

echo "=========================================="
echo "Deploying PHD Capital Rationale Studio"
echo "=========================================="

cd $APP_DIR

echo "[1/6] Loading environment variables..."
if [ -f "$ENV_FILE" ]; then
    set -a
    source $ENV_FILE
    set +a
    echo "Environment loaded from $ENV_FILE"
else
    echo "ERROR: Environment file not found at $ENV_FILE"
    exit 1
fi

echo "[2/6] Installing backend dependencies..."
cd $APP_DIR
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/6] Installing frontend dependencies..."
npm install

echo "[4/6] Building frontend..."
npm run build

echo "[5/6] Setting up file permissions..."
mkdir -p backend/job_files/uploaded_files
mkdir -p backend/job_files/logos
mkdir -p backend/job_files/fonts
chmod -R 755 backend/job_files

echo "[6/6] Restarting services..."
sudo systemctl daemon-reload
sudo systemctl restart ${APP_NAME}-backend
sudo systemctl restart nginx

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Backend status:"
sudo systemctl status ${APP_NAME}-backend --no-pager
echo ""
echo "Access your application at: http://$(hostname -I | awk '{print $1}')"
echo ""
