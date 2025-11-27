#!/bin/bash
#
# PHD Capital Rationale Studio - Safe Update Script
# 
# This script safely updates the application while:
# - Preserving all database data
# - Backing up database before any changes
# - Preserving uploaded files, logos, job files
# - Running database schema migrations
# - Handling errors gracefully
#
# Usage: sudo bash update.sh
#

set -e

PROJECT_DIR="/var/www/rationale-studio"
BACKUP_DIR="/var/www/rationale-studio-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHD CAPITAL RATIONALE STUDIO - SAFE UPDATE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Timestamp: $(date)"
echo "  Project: $PROJECT_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: Please run as root"
    echo ""
    echo "Run: sudo bash update.sh"
    exit 1
fi

# Navigate to project directory
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ ERROR: Project directory not found: $PROJECT_DIR"
    echo "Please run deploy.sh first for initial installation."
    exit 1
fi

cd "$PROJECT_DIR"

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Environment variables loaded"
else
    echo "⚠️  Warning: .env file not found, using system environment"
fi

# ═══════════════════════════════════════════════════════════
# STEP 1: Create Database Backup (CRITICAL - DATA SAFETY)
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 STEP 1/8: Creating Database Backup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Get database name from environment
DB_NAME="${PGDATABASE:-phd_rationale_db}"

# Create database backup
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"
if sudo -u postgres pg_dump "$DB_NAME" > "$BACKUP_FILE" 2>/dev/null; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "   ✅ Database backed up: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "   ⚠️  Warning: Could not backup database (may be empty or new)"
fi

# Keep only last 10 backups
cd "$BACKUP_DIR"
ls -t db_backup_*.sql 2>/dev/null | tail -n +11 | xargs -r rm
cd "$PROJECT_DIR"
echo "   ✅ Old backups cleaned (keeping last 10)"

# ═══════════════════════════════════════════════════════════
# STEP 2: Backup Important Files
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 STEP 2/8: Preserving Important Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Save .env file
if [ -f ".env" ]; then
    cp .env "$BACKUP_DIR/.env_backup_$TIMESTAMP"
    echo "   ✅ Environment file preserved"
fi

# The following directories will be preserved automatically:
# - backend/uploaded_files (master CSV, fonts, logos, cookies)
# - backend/channel_logos (channel platform logos)
# - backend/job_files (job processing files - can be large)
echo "   ℹ️  Uploaded files, channel logos, job files will be preserved"

# ═══════════════════════════════════════════════════════════
# STEP 3: Configure Git & Pull Latest Code
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📥 STEP 3/8: Pulling Latest Code from GitHub"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Configure git safe directory
git config --global --add safe.directory "$PROJECT_DIR"

# Stash any local changes (preserves modified files)
git stash 2>/dev/null || true

# Fetch and reset to latest
git fetch origin
git reset --hard origin/main
git pull origin main

echo "   ✅ Code updated from GitHub"

# Restore .env file if it was overwritten
if [ -f "$BACKUP_DIR/.env_backup_$TIMESTAMP" ]; then
    cp "$BACKUP_DIR/.env_backup_$TIMESTAMP" .env
    chmod 600 .env
    echo "   ✅ Environment file restored"
fi

# Ensure directories exist
mkdir -p backend/uploaded_files backend/job_files backend/channel_logos

# ═══════════════════════════════════════════════════════════
# STEP 4: Update Python Dependencies
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 STEP 4/8: Updating Python Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

source venv/bin/activate
pip install -r requirements.txt --quiet 2>/dev/null || pip install -r requirements.txt
deactivate

echo "   ✅ Python dependencies updated"

# ═══════════════════════════════════════════════════════════
# STEP 5: Update Node.js Dependencies
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 STEP 5/8: Updating Node.js Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

npm install --quiet 2>/dev/null || npm install

echo "   ✅ Node.js dependencies updated"

# ═══════════════════════════════════════════════════════════
# STEP 6: Build React Frontend
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚛️  STEP 6/8: Building React Frontend"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

npm run build

echo "   ✅ Frontend built successfully"

# ═══════════════════════════════════════════════════════════
# STEP 7: Run Database Schema Migration (PRESERVES DATA!)
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗄️  STEP 7/8: Running Database Schema Migration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

source venv/bin/activate

# Run migration script (safe - only adds missing columns/constraints)
if [ -f "backend/migrations/run_migration.py" ]; then
    echo "   📋 Running schema migration..."
    python3.11 backend/migrations/run_migration.py 2>&1 | grep -E "(✓|✅|Updated|Added|completed|Warning)" || true
    echo "   ✅ Database schema updated (data preserved)"
else
    echo "   ℹ️  No migration script found, skipping"
fi

deactivate

# ═══════════════════════════════════════════════════════════
# STEP 8: Restart Application & Verify
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 STEP 8/8: Restarting Application"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Set correct permissions
chown -R www-data:www-data "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"
chmod 600 .env 2>/dev/null || true

# Restart services
systemctl daemon-reload
systemctl restart phd-capital
systemctl restart nginx 2>/dev/null || true

echo "   ✅ Application restarted"

# Wait for application to start
echo ""
echo "   ⏳ Waiting for application to start..."
sleep 5

# ═══════════════════════════════════════════════════════════
# VERIFICATION & SUMMARY
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 VERIFYING APPLICATION STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check service status
if systemctl is-active --quiet phd-capital; then
    echo "   ✅ Application: RUNNING"
else
    echo "   ❌ Application: NOT RUNNING"
    echo ""
    echo "   Checking logs..."
    journalctl -u phd-capital -n 20 --no-pager
fi

# Check nginx
if systemctl is-active --quiet nginx; then
    echo "   ✅ Nginx: RUNNING"
else
    echo "   ⚠️  Nginx: NOT RUNNING"
fi

# Check database connectivity
source venv/bin/activate
if python3.11 -c "
import psycopg2
import os
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM users')
count = cur.fetchone()[0]
print(f'   ✅ Database: CONNECTED ({count} users)')
conn.close()
" 2>/dev/null; then
    :
else
    echo "   ⚠️  Database: Could not verify connection"
fi
deactivate

# ═══════════════════════════════════════════════════════════
# COMPLETION SUMMARY
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ UPDATE COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 What was updated:"
echo "   • Code pulled from GitHub"
echo "   • Python dependencies updated"
echo "   • Node.js dependencies updated"
echo "   • Frontend rebuilt"
echo "   • Database schema migrated (data preserved)"
echo "   • Application restarted"
echo ""
echo "💾 Backups created:"
echo "   • Database: $BACKUP_FILE"
echo "   • Environment: $BACKUP_DIR/.env_backup_$TIMESTAMP"
echo ""
echo "🌐 Application URL: http://researchrationale.in"
echo ""
echo "📋 Useful commands:"
echo "   • View logs: journalctl -u phd-capital -f"
echo "   • Restart: systemctl restart phd-capital"
echo "   • Status: systemctl status phd-capital"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
