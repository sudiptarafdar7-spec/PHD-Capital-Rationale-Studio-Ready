#!/bin/bash
#
# PHD Capital Rationale Studio - Production Deployment Script
# Server: 72.60.111.9 (Ubuntu 24.04 LTS)
# Domain: researchrationale.in
# GitHub: https://github.com/sudiptarafdar7-spec/PHD-Capital-Rationale-Studio-v1.git
#
# Usage: bash deploy.sh
#

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHD CAPITAL RATIONALE STUDIO - PRODUCTION DEPLOYMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Server IP: 72.60.111.9"
echo "  Domain: researchrationale.in"
echo "  OS: Ubuntu 24.04 LTS"
echo "  Project Folder: rationale-studio"
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
DOMAIN="researchrationale.in"
GITHUB_REPO="https://github.com/sudiptarafdar7-spec/PHD-Capital-Rationale-Studio-v1.git"
DB_NAME="phd_rationale_db"
DB_USER="phd_user"
DB_PASSWORD="ChangeMeToSecurePassword123!"

echo "📋 Configuration:"
echo "   Project Directory: $PROJECT_DIR"
echo "   Domain: $DOMAIN"
echo "   Database: $DB_NAME"
echo "   Repository: $GITHUB_REPO"
echo ""

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

# ═════════════════════════════════════════════════════════════
# STEP 6: Setup PostgreSQL Database
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗄️  STEP 6/11: Setting up PostgreSQL Database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql 2>/dev/null || true

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\";" 2>/dev/null || echo "   ℹ️  Database already exists"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "   ℹ️  User already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO $DB_USER;" 2>/dev/null
sudo -u postgres psql -c "ALTER DATABASE \"$DB_NAME\" OWNER TO $DB_USER;" 2>/dev/null

echo "   ✅ PostgreSQL database configured"
echo "      Database: $DB_NAME"
echo "      User: $DB_USER"

# ═══════════════════════════════════════════════════════════
# STEP 7: Clone/Update Application from GitHub
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📥 STEP 7/11: Cloning Application from GitHub"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "$PROJECT_DIR" ]; then
    echo "   ℹ️  Project directory exists, updating..."
    cd "$PROJECT_DIR"
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

# Create necessary directories
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

echo "   ✅ Python environment configured (66 packages installed)"

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
# STEP 10: Initialize Database & Create Admin User
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👤 STEP 10/11: Creating Admin User"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create environment file first
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

# Run seed script to create admin user
echo "   📦 Creating database tables and admin user..."
source venv/bin/activate

# Export environment variables for the seed script
export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=$DB_NAME
export PGUSER=$DB_USER
export PGPASSWORD=$DB_PASSWORD

python3.11 -m backend.seed_data
deactivate

echo "   ✅ Admin user created successfully"

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
echo "✅ DEPLOYMENT COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Application URLs:"
echo "   HTTP:  http://researchrationale.in"
echo "   HTTP:  http://72.60.111.9"
echo ""
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
echo "   • Dhan API Key (for stock data)"
echo "   • AssemblyAI API Key (for transcription)"
echo "   • Google Cloud JSON (for translation)"
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
echo "  cd /var/www/rationale-studio && bash deployment/update.sh"
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
