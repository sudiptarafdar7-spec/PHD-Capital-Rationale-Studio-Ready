# 🚀 PHD Capital Rationale Studio - Complete Deployment Guide

## Server Information
- **VPS IP:** 72.60.111.9
- **Domain:** researchrationale.in
- **OS:** Ubuntu 24.04 LTS
- **GitHub:** https://github.com/sudiptarafdar7-spec/PHD-Capital-Rationale-Studio-Ready.git

---

## 📋 Prerequisites

### What You Need
1. **Hostinger VPS Access:**
   - Server IP: `72.60.111.9`
   - Root password (from Hostinger panel)

2. **Domain Configuration:**
   - DNS A Records pointing to `72.60.111.9`
   - Both `researchrationale.in` and `www.researchrationale.in`

3. **Windows PC with PowerShell** (for deployment)

---

## 🔐 Step 1: Connect to VPS via SSH (Windows PowerShell)

### Open PowerShell
1. Press `Windows + X`
2. Click **"Windows PowerShell (Admin)"** or **"Terminal (Admin)"**

### Connect to Server
```powershell
ssh root@72.60.111.9
```

- Type `yes` when asked about fingerprint
- Enter your root password (from Hostinger)

**You're now connected to your VPS!**

---

## 📥 Step 2: Download Deployment Script

Run these commands one by one:

```bash
# Download deployment script
cd /root
curl -o deploy.sh https://raw.githubusercontent.com/sudiptarafdar7-spec/PHD-Capital-Rationale-Studio-Ready/main/deployment/deploy.sh

# Make it executable
chmod +x deploy.sh
```

---

## 🚀 Step 3: Run Deployment (ONE COMMAND!)

```bash
bash deploy.sh
```

**This will:**
- ✅ Install Python 3.11, Node.js 20, PostgreSQL, Nginx
- ✅ Clone your code from GitHub
- ✅ Install all dependencies (Python + Node.js)
- ✅ Build React frontend
- ✅ Create PostgreSQL database
- ✅ Create admin user automatically
- ✅ Configure systemd service
- ✅ Configure Nginx reverse proxy
- ✅ Start the application

**Time:** 10-15 minutes (grab a coffee! ☕)

---

## ✅ Step 4: Verify Deployment

### Check Application Status
```bash
systemctl status phd-capital
```

You should see: **"active (running)"** in green.

### View Live Logs
```bash
journalctl -u phd-capital -f
```

Press `Ctrl+C` to stop viewing logs.

### Test Application
Open browser and visit:
- `http://researchrationale.in`
- `http://72.60.111.9`

---

## 🔑 Step 5: Login & Configure

### Login Credentials
- **Admin Email:** `admin@phdcapital.in`
- **Admin Password:** `admin123`

### Add API Keys
After logging in:

1. Go to **Admin Panel** → **API Keys**
2. Add these keys:

| Provider | Description | Required For |
|----------|-------------|--------------|
| **OpenAI** | GPT-4 API Key | Speaker detection, content analysis |
| **Dhan** | Dhan API Access Token | Stock price charts |
| **AssemblyAI** | AssemblyAI API Key | Audio transcription |
| **Google Cloud** | JSON credentials | Translation service |

---

## 🔄 How to Update Application (Future Updates)

### After You Push Changes to GitHub:

```bash
# Connect to server
ssh root@72.60.111.9

# Run update script
cd /var/www/rationale-studio
bash deployment/update.sh
```

**That's it!** The update script will:
- Pull latest code from GitHub
- Update dependencies
- Rebuild frontend
- Restart application

---

## 🔐 Optional: Setup SSL Certificate (HTTPS)

### Prerequisites
✅ Your domain DNS must point to `72.60.111.9` (wait 5-60 minutes after DNS change)

### Verify DNS First
```bash
# Check if DNS is configured correctly
dig researchrationale.in +short
# Should return: 72.60.111.9
```

### Install SSL Certificate
```bash
# Install certbot
apt install -y certbot python3-certbot-nginx

# Get certificate (interactive)
certbot --nginx -d researchrationale.in -d www.researchrationale.in
```

Follow the prompts:
- Enter your email
- Agree to terms
- Choose: Redirect HTTP to HTTPS

**Done!** Your site is now on HTTPS! 🔒

---

## 🛠️ Troubleshooting

### Application Not Starting?

```bash
# Check service status
systemctl status phd-capital

# View error logs
journalctl -u phd-capital -n 50 --no-pager

# Restart service
systemctl restart phd-capital
```

### Database Issues?

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# List databases
\l

# Connect to app database
\c phd_rationale_db

# List tables
\dt

# Exit
\q
```

### Nginx Issues?

```bash
# Test nginx configuration
nginx -t

# Restart nginx
systemctl restart nginx

# Check nginx status
systemctl status nginx
```

### Can't Login?

The admin user should be created automatically. If not:

```bash
# Go to project directory
cd /var/www/rationale-studio

# Activate virtual environment
source venv/bin/activate

# Run seed script manually
python3.11 -m backend.seed_data

# Deactivate
deactivate
```

This will create:
- **Admin:** admin@phdcapital.in / admin123
- **Employee:** rajesh@phdcapital.in / employee123

### Port 80/443 Not Accessible?

```bash
# Check firewall
ufw status

# Allow HTTP and HTTPS
ufw allow 80
ufw allow 443

# Restart nginx
systemctl restart nginx
```

---

## 📋 Useful Commands Reference

### Application Management
```bash
# Start application
systemctl start phd-capital

# Stop application
systemctl stop phd-capital

# Restart application
systemctl restart phd-capital

# Check status
systemctl status phd-capital

# View logs (live)
journalctl -u phd-capital -f

# View last 100 log lines
journalctl -u phd-capital -n 100 --no-pager
```

### Nginx Management
```bash
# Test configuration
nginx -t

# Restart nginx
systemctl restart nginx

# Check status
systemctl status nginx

# View nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Database Management
```bash
# Connect to database
sudo -u postgres psql -d phd_rationale_db

# Backup database
sudo -u postgres pg_dump phd_rationale_db > backup_$(date +%Y%m%d).sql

# Restore database
sudo -u postgres psql phd_rationale_db < backup_20250101.sql
```

### File Locations
```bash
# Application directory
cd /var/www/rationale-studio

# Environment file
nano /var/www/rationale-studio/.env

# Systemd service file
nano /etc/systemd/system/phd-capital.service

# Nginx configuration
nano /etc/nginx/sites-available/rationale-studio

# Uploaded files
cd /var/www/rationale-studio/backend/uploaded_files

# Job files
cd /var/www/rationale-studio/backend/job_files
```

---

## 🔥 Fresh Deployment (If Something Goes Wrong)

If you need to start from scratch:

```bash
# Stop and remove everything
systemctl stop phd-capital
systemctl disable phd-capital
rm -rf /var/www/rationale-studio
rm /etc/systemd/system/phd-capital.service
rm /etc/nginx/sites-available/rationale-studio
rm /etc/nginx/sites-enabled/rationale-studio

# Drop database
sudo -u postgres psql -c "DROP DATABASE IF EXISTS phd_rationale_db;"
sudo -u postgres psql -c "DROP USER IF EXISTS phd_user;"

# Re-run deployment
cd /root
bash deploy.sh
```

---

## 📞 Support

If you encounter issues not covered here:

1. **Check Logs:** `journalctl -u phd-capital -n 100 --no-pager`
2. **Check Nginx:** `nginx -t && tail -f /var/log/nginx/error.log`
3. **Check Database:** `sudo -u postgres psql -d phd_rationale_db -c "SELECT count(*) FROM users;"`

---

## 🎯 Quick Start Checklist

- [ ] SSH into server: `ssh root@72.60.111.9`
- [ ] Download deploy.sh from GitHub
- [ ] Run: `bash deploy.sh`
- [ ] Wait 10-15 minutes
- [ ] Visit: `http://researchrationale.in`
- [ ] Login with: `admin@phdcapital.in` / `admin123`
- [ ] Add API keys in Admin Panel
- [ ] Test by processing a YouTube video
- [ ] (Optional) Setup SSL: `certbot --nginx`

**Done!** 🎉
