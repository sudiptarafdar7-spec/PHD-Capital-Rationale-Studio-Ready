#!/bin/bash

set -e

echo "=========================================="
echo "PHD Capital Rationale Studio - VPS Setup"
echo "=========================================="
echo ""

if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root (use sudo)"
   exit 1
fi

APP_NAME="phd-capital"
APP_USER="phd"
APP_DIR="/home/$APP_USER/app"
DOMAIN="${1:-147.79.68.141}"

echo "Setting up for domain/IP: $DOMAIN"
echo ""

echo "[1/8] Updating system packages..."
apt-get update
apt-get upgrade -y

echo "[2/8] Installing required packages..."
apt-get install -y \
    git \
    nginx \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nodejs \
    npm \
    ufw \
    fail2ban \
    supervisor \
    ffmpeg \
    curl

echo "[3/8] Setting up firewall (UFW)..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw status

echo "[4/8] Creating application user..."
if id "$APP_USER" &>/dev/null; then
    echo "User $APP_USER already exists"
else
    useradd -m -s /bin/bash $APP_USER
    echo "User $APP_USER created"
fi

echo "[5/8] Setting up PostgreSQL..."
# Check if PostgreSQL user already exists
if sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = '${APP_USER}'" | grep -q 1; then
    echo "PostgreSQL user '${APP_USER}' already exists"
    # Extract existing password from env file if it exists
    if [ -f "/etc/${APP_NAME}.env" ]; then
        DB_PASSWORD=$(grep "DATABASE_URL" /etc/${APP_NAME}.env | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
        echo "Using existing database password from /etc/${APP_NAME}.env"
    else
        echo "WARNING: User exists but no env file found. You'll need to manually set DATABASE_URL."
        DB_PASSWORD="PLEASE_SET_MANUALLY"
    fi
else
    # Generate a secure random password for new user
    DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 24)
    sudo -u postgres psql -c "CREATE USER ${APP_USER} WITH PASSWORD '${DB_PASSWORD}';"
    echo "PostgreSQL user '${APP_USER}' created with secure auto-generated password"
fi

# Create database if it doesn't exist
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${APP_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${APP_NAME};"

# Grant privileges and set ownership (idempotent)
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${APP_NAME} TO ${APP_USER};"
sudo -u postgres psql -c "ALTER DATABASE ${APP_NAME} OWNER TO ${APP_USER};"
echo "PostgreSQL database '${APP_NAME}' configured"

echo "[6/8] Creating application directories..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/backend/job_files
mkdir -p /var/log/$APP_NAME
chown -R $APP_USER:$APP_USER $APP_DIR
chown -R $APP_USER:$APP_USER /var/log/$APP_NAME

echo "[7/8] Setting up Git repository..."
sudo -u $APP_USER git init --bare /home/$APP_USER/repo.git
echo "Bare Git repository created at /home/$APP_USER/repo.git"

echo "[8/8] Creating environment file with secure credentials..."
cat > /etc/${APP_NAME}.env << EOF
# Database Configuration
DATABASE_URL=postgresql://${APP_USER}:${DB_PASSWORD}@localhost:5432/${APP_NAME}

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=CHANGE_THIS_TO_A_RANDOM_SECRET_KEY
JWT_SECRET_KEY=CHANGE_THIS_TO_ANOTHER_RANDOM_SECRET_KEY

# API Keys (fill these in after deployment)
OPENAI_API_KEY=
ASSEMBLYAI_API_KEY=
GOOGLE_TRANSLATE_API_KEY=
DHAN_API_KEY=
RAPIDAPI_KEY=

# Application Settings
ALLOWED_ORIGINS=http://147.79.68.141,https://yourdomain.com
EOF

chmod 600 /etc/${APP_NAME}.env
chown $APP_USER:$APP_USER /etc/${APP_NAME}.env

echo "[9/9] Configuring passwordless sudo for deployment..."
cat > /etc/sudoers.d/${APP_NAME}-deploy << 'SUDOEOF'
# Allow phd user to restart services without password (for automated deployment)
phd ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload
phd ALL=(ALL) NOPASSWD: /bin/systemctl restart phd-capital-backend
phd ALL=(ALL) NOPASSWD: /bin/systemctl restart nginx
phd ALL=(ALL) NOPASSWD: /bin/systemctl status phd-capital-backend
SUDOEOF
chmod 440 /etc/sudoers.d/${APP_NAME}-deploy
echo "Passwordless sudo configured for deployment automation"

echo ""
echo "=========================================="
echo "VPS Setup Complete!"
echo "=========================================="
echo ""
echo "IMPORTANT: Your PostgreSQL password has been automatically generated and saved."
echo "Database credentials are in /etc/${APP_NAME}.env (secure, only readable by phd user)"
echo ""
echo "Next steps:"
echo "1. Edit /etc/${APP_NAME}.env and fill in your API keys (database password is already set)"
echo "2. Copy the systemd service file: sudo cp deploy/systemd/${APP_NAME}-backend.service /etc/systemd/system/"
echo "3. Copy the Nginx config: sudo cp deploy/nginx/${APP_NAME}.conf /etc/nginx/sites-available/"
echo "4. Enable Nginx site: sudo ln -s /etc/nginx/sites-available/${APP_NAME}.conf /etc/nginx/sites-enabled/"
echo "5. Copy the post-receive hook: sudo cp deploy/post-receive /home/$APP_USER/repo.git/hooks/"
echo "6. Make it executable: sudo chmod +x /home/$APP_USER/repo.git/hooks/post-receive"
echo "7. Add your VPS as a Git remote: git remote add vps $APP_USER@$DOMAIN:/home/$APP_USER/repo.git"
echo "8. Deploy: git push vps main"
echo ""
echo "Security Note: Database password is auto-generated and secure. Keep /etc/${APP_NAME}.env protected!"
echo ""
