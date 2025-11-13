#!/bin/bash
#
# PHD Capital Rationale Studio - Quick Update Script
# Run this after pushing changes to GitHub
#
# Usage: bash update.sh
#

set -e

PROJECT_DIR="/var/www/rationale-studio"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHD CAPITAL - UPDATE DEPLOYMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: Please run as root"
    echo ""
    echo "Run: sudo bash update.sh"
    exit 1
fi

# Navigate to project directory
cd "$PROJECT_DIR"

echo "📥 STEP 1/6: Pulling latest code from GitHub..."
git fetch origin
git reset --hard origin/main
git pull origin main
echo "   ✅ Code updated"
echo ""

echo "🐍 STEP 2/6: Updating Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet
deactivate
echo "   ✅ Python dependencies updated"
echo ""

echo "📦 STEP 3/6: Updating Node.js dependencies..."
npm install --quiet
echo "   ✅ Node dependencies updated"
echo ""

echo "⚛️  STEP 4/6: Building React frontend..."
npm run build
echo "   ✅ Frontend built"
echo ""

echo "🔄 STEP 5/6: Restarting application..."
systemctl restart phd-capital
echo "   ✅ Application restarted"
echo ""

echo "🔍 STEP 6/6: Checking status..."
sleep 3
systemctl status phd-capital --no-pager -l | head -20
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ UPDATE COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Application URL: http://researchrationale.in"
echo ""
echo "📋 View logs: journalctl -u phd-capital -f"
echo ""
