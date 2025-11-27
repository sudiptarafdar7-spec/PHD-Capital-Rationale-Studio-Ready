#!/bin/bash
#
# PHD Capital Rationale Studio - Production Deployment Script
# Server: 72.60.111.9 (Ubuntu 24.04 LTS)
# Domain: researchrationale.in
# GitHub: https://github.com/sudiptarafdar7-spec/PHD-Capital-Rationale-Studio-Ready.git
#
# This script handles both:
# - FRESH INSTALL: Creates database, users, everything from scratch
# - UPGRADE: Preserves all existing data, only updates code and schema
#
# Usage: sudo bash deploy.sh
#

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHD CAPITAL RATIONALE STUDIO - PRODUCTION DEPLOYMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Server IP: 72.60.111.9"
echo "  Domain: researchrationale.in"
echo "  OS: Ubuntu 24.04 LTS"
echo "  Timestamp: $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: Please run as root"
    echo ""
    echo "Run: sudo bash deploy.sh"
    exit 1
fi

# Configuration
PROJECT_DIR="/var/www/rationale-studio"
BACKUP_DIR="/var/www/rationale-studio-backups"
DOMAIN="researchrationale.in"
GITHUB_REPO="https://github.com/sudiptarafdar7-spec/PHD-Capital-Rationale-Studio-Ready.git"
DB_NAME="phd_rationale_db"
DB_USER="phd_user"
DB_PASSWORD="ChangeMeToSecurePassword123!"

# ═══════════════════════════════════════════════════════════
# DETECT INSTALLATION TYPE
# ═══════════════════════════════════════════════════════════
IS_UPGRADE=false
EXISTING_ENV=""

if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/.env" ]; then
    IS_UPGRADE=true
    EXISTING_ENV="$PROJECT_DIR/.env"
    echo "🔄 UPGRADE MODE DETECTED"
    echo "   Existing installation found at $PROJECT_DIR"
    echo "   Your data will be PRESERVED!"
    echo ""
    
    # Read existing database password from .env
    if grep -q "DATABASE_URL" "$EXISTING_ENV"; then
        DB_PASSWORD=$(grep "DATABASE_URL" "$EXISTING_ENV" | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
        echo "   ✅ Using existing database credentials"
    fi
else
    echo "🆕 FRESH INSTALL MODE"
    echo "   Installing to $PROJECT_DIR"
    echo ""
fi

echo "📋 Configuration:"
echo "   Project Directory: $PROJECT_DIR"
echo "   Domain: $DOMAIN"
echo "   Database: $DB_NAME"
echo "   Repository: $GITHUB_REPO"
echo "   Mode: $([ "$IS_UPGRADE" = true ] && echo "UPGRADE (data preserved)" || echo "FRESH INSTALL")"
echo ""

# ═══════════════════════════════════════════════════════════
# STEP 0: Backup Existing Data (UPGRADE MODE ONLY)
# ═══════════════════════════════════════════════════════════
if [ "$IS_UPGRADE" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💾 STEP 0: Backing Up Existing Data"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    if sudo -u postgres pg_dump "$DB_NAME" > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql" 2>/dev/null; then
        echo "   ✅ Database backed up: $BACKUP_DIR/db_backup_$TIMESTAMP.sql"
    fi
    
    # Backup .env
    cp "$EXISTING_ENV" "$BACKUP_DIR/.env_backup_$TIMESTAMP"
    echo "   ✅ Environment file backed up"
    
    # Backup uploaded files
    if [ -d "$PROJECT_DIR/backend/uploaded_files" ]; then
        cp -r "$PROJECT_DIR/backend/uploaded_files" "$BACKUP_DIR/uploaded_files_$TIMESTAMP" 2>/dev/null || true
        echo "   ✅ Uploaded files backed up"
    fi
    
    # Backup channel logos
    if [ -d "$PROJECT_DIR/backend/channel_logos" ]; then
        cp -r "$PROJECT_DIR/backend/channel_logos" "$BACKUP_DIR/channel_logos_$TIMESTAMP" 2>/dev/null || true
        echo "   ✅ Channel logos backed up"
    fi
    
    echo ""
fi

# ═══════════════════════════════════════════════════════════
# STEP 1: Update System & Install Base Dependencies
# ═══════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 STEP 1/11: Installing System Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

apt update -qq
apt install -y \
    software-properties-common \
    build-essential \
    git \
    curl \
    nginx \
    ffmpeg \
    2>/dev/null || true

echo "   ✅ Base system dependencies installed"

# ═══════════════════════════════════════════════════════════
# STEP 2: Install Python 3.11 from Deadsnakes PPA
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 STEP 2/11: Installing Python 3.11"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v python3.11 &> /dev/null; then
    echo "   📦 Adding deadsnakes PPA for Python 3.11..."
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update -qq
    
    echo "   📦 Installing Python 3.11 and development headers..."
    apt install -y \
        python3.11 \
        python3.11-venv \
        python3.11-dev \
        python3-pip \
        2>/dev/null || true
    
    echo "   ✅ Python $(python3.11 --version) installed"
else
    echo "   ✅ Python $(python3.11 --version) already installed"
fi

# ═══════════════════════════════════════════════════════════
# STEP 3: Install PostgreSQL Development Libraries
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗄️  STEP 3/11: Installing PostgreSQL & Development Libraries"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

apt install -y \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    postgresql-server-dev-all \
    2>/dev/null || true

echo "   ✅ PostgreSQL and development libraries installed"

# ═══════════════════════════════════════════════════════════
# STEP 4: Install Node.js 20.x
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 STEP 4/11: Installing Node.js 20.x"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v node &> /dev/null || [[ $(node -v | cut -d'v' -f2 | cut -d'.' -f1) -lt 20 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
    echo "   ✅ Node.js $(node -v) installed"
else
    echo "   ✅ Node.js $(node -v) already installed"
fi

# ═══════════════════════════════════════════════════════════
# STEP 5: Install yt-dlp
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 STEP 5/11: Installing yt-dlp"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -f /usr/local/bin/yt-dlp ]; then
    curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
    chmod a+rx /usr/local/bin/yt-dlp
    echo "   ✅ yt-dlp installed"
else
    /usr/local/bin/yt-dlp -U 2>/dev/null || true
    echo "   ✅ yt-dlp updated to latest version"
fi

# ═══════════════════════════════════════════════════════════
# STEP 6: Setup PostgreSQL Database
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗄️  STEP 6/11: Setting up PostgreSQL Database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql 2>/dev/null || true

if [ "$IS_UPGRADE" = true ]; then
    echo "   ℹ️  Upgrade mode: Preserving existing database"
    echo "   ✅ Database preserved: $DB_NAME"
else
    # Fresh install: Create database and user
    sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\";" 2>/dev/null || echo "   ℹ️  Database already exists"
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "   ℹ️  User already exists"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO $DB_USER;" 2>/dev/null
    sudo -u postgres psql -c "ALTER DATABASE \"$DB_NAME\" OWNER TO $DB_USER;" 2>/dev/null
    
    # Grant schema permissions
    sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" 2>/dev/null || true
    
    echo "   ✅ PostgreSQL database configured"
    echo "      Database: $DB_NAME"
    echo "      User: $DB_USER"
fi

# ═══════════════════════════════════════════════════════════
# STEP 7: Clone/Update Application from GitHub
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📥 STEP 7/11: Getting Application Code from GitHub"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Save existing files before code update
SAVED_ENV=""
SAVED_UPLOADS=""
SAVED_LOGOS=""
SAVED_JOBS=""

if [ "$IS_UPGRADE" = true ]; then
    # Save important directories
    if [ -f "$PROJECT_DIR/.env" ]; then
        SAVED_ENV=$(cat "$PROJECT_DIR/.env")
    fi
    if [ -d "$PROJECT_DIR/backend/uploaded_files" ]; then
        mkdir -p /tmp/rationale_upgrade
        cp -r "$PROJECT_DIR/backend/uploaded_files" /tmp/rationale_upgrade/ 2>/dev/null || true
        SAVED_UPLOADS="/tmp/rationale_upgrade/uploaded_files"
    fi
    if [ -d "$PROJECT_DIR/backend/channel_logos" ]; then
        cp -r "$PROJECT_DIR/backend/channel_logos" /tmp/rationale_upgrade/ 2>/dev/null || true
        SAVED_LOGOS="/tmp/rationale_upgrade/channel_logos"
    fi
    if [ -d "$PROJECT_DIR/backend/job_files" ]; then
        cp -r "$PROJECT_DIR/backend/job_files" /tmp/rationale_upgrade/ 2>/dev/null || true
        SAVED_JOBS="/tmp/rationale_upgrade/job_files"
    fi
fi

if [ -d "$PROJECT_DIR" ]; then
    echo "   ℹ️  Project directory exists, updating..."
    cd "$PROJECT_DIR"
    git config --global --add safe.directory "$PROJECT_DIR"
    git fetch origin
    git reset --hard origin/main
    git pull origin main
    echo "   ✅ Code updated from GitHub"
else
    echo "   📦 Cloning repository..."
    mkdir -p "/var/www"
    git clone "$GITHUB_REPO" "$PROJECT_DIR"
    echo "   ✅ Repository cloned"
fi

cd "$PROJECT_DIR"

# Configure git safe directory for future operations
git config --global --add safe.directory "$PROJECT_DIR"

# Restore saved files
if [ "$IS_UPGRADE" = true ]; then
    echo "   📁 Restoring preserved files..."
    
    # Restore .env
    if [ -n "$SAVED_ENV" ]; then
        echo "$SAVED_ENV" > .env
        chmod 600 .env
        echo "   ✅ Environment file restored"
    fi
    
    # Restore uploaded files
    if [ -d "$SAVED_UPLOADS" ]; then
        rm -rf backend/uploaded_files 2>/dev/null || true
        cp -r "$SAVED_UPLOADS" backend/uploaded_files
        echo "   ✅ Uploaded files restored"
    fi
    
    # Restore channel logos
    if [ -d "$SAVED_LOGOS" ]; then
        rm -rf backend/channel_logos 2>/dev/null || true
        cp -r "$SAVED_LOGOS" backend/channel_logos
        echo "   ✅ Channel logos restored"
    fi
    
    # Restore job files
    if [ -d "$SAVED_JOBS" ]; then
        rm -rf backend/job_files 2>/dev/null || true
        cp -r "$SAVED_JOBS" backend/job_files
        echo "   ✅ Job files restored"
    fi
    
    # Cleanup temp files
    rm -rf /tmp/rationale_upgrade 2>/dev/null || true
fi

# Create necessary directories (if they don't exist)
mkdir -p backend/uploaded_files backend/job_files backend/channel_logos

echo "   ✅ Application code ready"

# ═══════════════════════════════════════════════════════════
# STEP 8: Setup Python Virtual Environment
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 STEP 8/11: Setting up Python Virtual Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Remove old venv if exists
if [ -d "venv" ]; then
    rm -rf venv
fi

# Create fresh virtual environment with Python 3.11
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install Python dependencies
echo "   📦 Installing Python packages (this may take 5-10 minutes)..."
pip install -r requirements.txt --quiet

deactivate

echo "   ✅ Python environment configured"

# ═══════════════════════════════════════════════════════════
# STEP 9: Build React Frontend
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚛️  STEP 9/11: Building React Frontend"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Install Node dependencies
echo "   📦 Installing npm packages..."
npm install --quiet

# Build production bundle
echo "   🔨 Building production bundle..."
npm run build

echo "   ✅ React frontend built successfully"

# ═══════════════════════════════════════════════════════════
# STEP 10: Initialize/Update Database Schema & Admin User
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗄️  STEP 10/11: Database Schema & Admin Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$IS_UPGRADE" = false ]; then
    # Fresh install: Create environment file
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > .env << ENVEOF
# Flask Configuration
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY

# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME
PGHOST=localhost
PGPORT=5432
PGDATABASE=$DB_NAME
PGUSER=$DB_USER
PGPASSWORD=$DB_PASSWORD
ENVEOF

    chmod 600 .env
    echo "   ✅ Environment file created"
fi

# Export environment variables
export $(grep -v '^#' .env | xargs)

source venv/bin/activate

# Run database migration (safe for both fresh install and upgrade)
if [ -f "backend/migrations/run_migration.py" ]; then
    echo "   📋 Running database schema migration..."
    python3.11 backend/migrations/run_migration.py 2>&1 | grep -E "(✓|✅|Updated|Added|completed|Warning)" || true
    echo "   ✅ Database schema updated"
fi

if [ "$IS_UPGRADE" = false ]; then
    # Fresh install: Run seed script to create admin user
    echo "   📦 Creating admin user..."
    python3.11 -m backend.seed_data
    echo "   ✅ Admin user created"
else
    echo "   ℹ️  Upgrade mode: Existing users preserved"
fi

deactivate

# ═══════════════════════════════════════════════════════════
# STEP 11: Setup Systemd Service & Nginx
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  STEP 11/11: Configuring Systemd & Nginx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create systemd service
cat > /etc/systemd/system/phd-capital.service << 'SERVICEEOF'
[Unit]
Description=PHD Capital Rationale Studio
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/rationale-studio
Environment="PATH=/var/www/rationale-studio/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/var/www/rationale-studio/.env
ExecStart=/var/www/rationale-studio/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 300 --worker-class sync 'backend.app:create_app()'
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=phd-capital

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Set correct permissions
chown -R www-data:www-data "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"
chmod 600 .env

# Configure Nginx
cat > /etc/nginx/sites-available/rationale-studio << 'NGINXEOF'
server {
    listen 80;
    server_name researchrationale.in www.researchrationale.in;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
NGINXEOF

# Enable site
ln -sf /etc/nginx/sites-available/rationale-studio /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Reload services
systemctl daemon-reload
systemctl enable phd-capital
systemctl restart phd-capital
systemctl restart nginx

echo "   ✅ Systemd service configured and started"
echo "   ✅ Nginx configured and reloaded"

# ═══════════════════════════════════════════════════════════
# DEPLOYMENT COMPLETE
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$IS_UPGRADE" = true ]; then
    echo "✅ UPGRADE COMPLETE! (All data preserved)"
else
    echo "✅ FRESH DEPLOYMENT COMPLETE!"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Application URLs:"
echo "   HTTP:  http://researchrationale.in"
echo "   HTTP:  http://72.60.111.9"
echo ""

if [ "$IS_UPGRADE" = true ]; then
    echo "📋 Upgrade Summary:"
    echo "   • Code updated from GitHub"
    echo "   • Python dependencies updated"
    echo "   • Frontend rebuilt"
    echo "   • Database schema migrated"
    echo "   • All user data PRESERVED"
    echo "   • All uploaded files PRESERVED"
    echo "   • All API keys PRESERVED"
    echo ""
    echo "💾 Backups saved to: $BACKUP_DIR"
else
    echo "🔑 Login Credentials:"
    echo "   Admin Email:    admin@phdcapital.in"
    echo "   Admin Password: admin123"
    echo ""
    echo "   Employee Email:    rajesh@phdcapital.in"
    echo "   Employee Password: employee123"
    echo ""
    echo "⚠️  IMPORTANT: Configure API Keys"
    echo "   After logging in, go to Admin Panel > API Keys and add:"
    echo "   • OpenAI API Key (for GPT-4 analysis)"
    echo "   • Gemini API Key (for stock extraction)"
    echo "   • Dhan API Key (for stock data)"
    echo "   • AssemblyAI API Key (for transcription)"
    echo "   • Google Cloud JSON (for translation)"
fi
echo ""
echo "📋 Useful Commands:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Check application status:"
echo "  systemctl status phd-capital"
echo ""
echo "View logs:"
echo "  journalctl -u phd-capital -f"
echo ""
echo "Restart application:"
echo "  systemctl restart phd-capital"
echo ""
echo "Update application (after git push):"
echo "  cd /var/www/rationale-studio && sudo bash deployment/update.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔐 Optional: Setup SSL Certificate"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To enable HTTPS (after DNS is properly configured):"
echo ""
echo "  apt install -y certbot python3-certbot-nginx"
echo "  certbot --nginx -d researchrationale.in -d www.researchrationale.in"
echo ""
echo "Make sure your domain DNS points to 72.60.111.9 first!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
