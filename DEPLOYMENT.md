# PHD Capital Rationale Studio - VPS Deployment Guide

This guide will help you deploy your application to your Hostinger VPS (147.79.68.141) with one-click automated deployment via Git.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial VPS Setup](#initial-vps-setup)
3. [Configure Environment Variables](#configure-environment-variables)
4. [Deploy Services](#deploy-services)
5. [First Deployment](#first-deployment)
6. [Automated Deployments](#automated-deployments)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### On Your Local Machine
- Git installed
- SSH access to your VPS (root or sudo user)
- Your project code ready to deploy

### On Your VPS (Hostinger)
- Ubuntu 20.04 or 22.04 (recommended)
- Root or sudo access
- At least 2GB RAM
- 20GB+ disk space

---

## Initial VPS Setup

### Step 1: Connect to Your VPS

```bash
ssh root@147.79.68.141
```

### Step 2: Upload Setup Script

From your local machine, copy the setup script to your VPS:

```bash
scp deploy/vps_setup.sh root@147.79.68.141:/root/
```

### Step 3: Run VPS Setup Script

On your VPS:

```bash
cd /root
chmod +x vps_setup.sh
sudo ./vps_setup.sh
```

This script will:
- Install all required packages (Python, Node.js, PostgreSQL, Nginx, etc.)
- Create application user (`phd`)
- Set up PostgreSQL database
- Configure firewall (UFW)
- Create Git repository for deployments
- Set up directory structure

⏱️ **Time required**: 5-10 minutes

---

## Configure Environment Variables

### Step 1: Edit Production Environment File

```bash
sudo nano /etc/phd-capital.env
```

### Step 2: Fill in Your API Keys and Secrets

The VPS setup script has already configured your database with a secure auto-generated password. You only need to add your API keys.

**Note**: The database password is already set in `/etc/phd-capital.env` and was automatically generated during VPS setup. You don't need to change it unless you want to rotate it for security reasons.

Update the following values:

```bash
# 1. Database is already configured with secure password (no action needed)
# DATABASE_URL=postgresql://phd:AUTO_GENERATED_PASSWORD@localhost:5432/phd-capital

# 2. Generate secure secrets (run these commands to generate random values)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 3. Add your API keys
OPENAI_API_KEY=sk-...
ASSEMBLYAI_API_KEY=...
GOOGLE_TRANSLATE_API_KEY=...
DHAN_API_KEY=...

# 4. Update allowed origins (add your domain if you have one)
ALLOWED_ORIGINS=http://147.79.68.141,https://yourdomain.com
```

### Step 3: (Optional) Rotate Database Password

The database password was auto-generated during setup and is already configured. If you want to change it for security reasons:

```bash
# Generate a new password
NEW_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

# Update PostgreSQL
sudo -u postgres psql -c "ALTER USER phd WITH PASSWORD '$NEW_PASSWORD';"

# Update environment file
sudo sed -i "s|DATABASE_URL=postgresql://phd:[^@]*@|DATABASE_URL=postgresql://phd:$NEW_PASSWORD@|" /etc/phd-capital.env

# Restart backend
sudo systemctl restart phd-capital-backend
```

---

## Deploy Services

### Step 1: Install Systemd Service

```bash
sudo cp /home/phd/app/deploy/systemd/phd-capital-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable phd-capital-backend
```

### Step 2: Install Nginx Configuration

```bash
# Copy config file
sudo cp /home/phd/app/deploy/nginx/phd-capital.conf /etc/nginx/sites-available/

# Enable the site
sudo ln -s /etc/nginx/sites-available/phd-capital.conf /etc/nginx/sites-enabled/

# Remove default Nginx site
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 3: Set Up Git Post-Receive Hook

```bash
# Copy the hook
sudo cp /home/phd/app/deploy/post-receive /home/phd/repo.git/hooks/

# Make it executable
sudo chmod +x /home/phd/repo.git/hooks/post-receive

# Set correct ownership
sudo chown -R phd:phd /home/phd/repo.git
```

---

## First Deployment

### Step 1: Add VPS as Git Remote (On Your Local Machine)

```bash
# Navigate to your project directory
cd /path/to/phd-capital-rationale-studio

# Add VPS as a remote
git remote add vps phd@147.79.68.141:/home/phd/repo.git
```

### Step 2: Push Your Code

```bash
# Push to VPS (this will trigger automatic deployment)
git push vps main
```

If your main branch is named differently (e.g., `master`):

```bash
git push vps master:main
```

### Step 3: Monitor Deployment

The deployment will automatically:
1. ✅ Checkout your code to `/home/phd/app`
2. ✅ Install Python dependencies
3. ✅ Install Node.js dependencies
4. ✅ Build the React frontend
5. ✅ Restart the backend service
6. ✅ Restart Nginx

### Step 4: Verify Deployment

```bash
# SSH into your VPS
ssh phd@147.79.68.141

# Check backend status
sudo systemctl status phd-capital-backend

# Check Nginx status
sudo systemctl status nginx

# View backend logs
sudo journalctl -u phd-capital-backend -f
```

### Step 5: Access Your Application

Open your browser and visit:

```
http://147.79.68.141
```

You should see your PHD Capital Rationale Studio login page! 🎉

---

## Automated Deployments

After the initial setup, deploying updates is as simple as:

```bash
# Make your changes
git add .
git commit -m "Your commit message"

# Deploy to production
git push vps main
```

The Git post-receive hook will automatically:
- Pull latest code
- Install any new dependencies
- Rebuild frontend
- Restart services

No manual SSH or commands required! 🚀

---

## Monitoring & Maintenance

### View Application Logs

```bash
# Backend application logs
sudo tail -f /var/log/phd-capital/backend.log

# Backend error logs
sudo tail -f /var/log/phd-capital/backend-error.log

# Nginx access logs
sudo tail -f /var/log/nginx/phd-capital-access.log

# Nginx error logs
sudo tail -f /var/log/nginx/phd-capital-error.log

# Systemd service logs (live)
sudo journalctl -u phd-capital-backend -f
```

### Check Service Status

```bash
# Backend service
sudo systemctl status phd-capital-backend

# Nginx
sudo systemctl status nginx

# PostgreSQL
sudo systemctl status postgresql
```

### Restart Services

```bash
# Restart backend only
sudo systemctl restart phd-capital-backend

# Restart Nginx
sudo systemctl restart nginx

# Restart both
sudo systemctl restart phd-capital-backend nginx
```

### Database Backup

```bash
# Create backup
sudo -u postgres pg_dump phd-capital > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
sudo -u postgres psql phd-capital < backup_20250113_120000.sql
```

### View Database Password

If you need to retrieve your auto-generated database password:

```bash
sudo grep "DATABASE_URL" /etc/phd-capital.env
```

The password is the part between `:` and `@` in the connection string.

---

## Troubleshooting

### Issue: "502 Bad Gateway" Error

**Cause**: Backend service is not running.

**Solution**:
```bash
# Check backend status
sudo systemctl status phd-capital-backend

# View error logs
sudo journalctl -u phd-capital-backend -n 50

# Restart backend
sudo systemctl restart phd-capital-backend
```

### Issue: "Connection Refused" to Database

**Cause**: Database credentials incorrect or PostgreSQL not running.

**Solution**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Verify credentials in environment file
sudo cat /etc/phd-capital.env | grep DATABASE_URL

# Test database connection
sudo -u postgres psql phd-capital -c "SELECT version();"
```

### Issue: Frontend Not Loading

**Cause**: Build files missing or Nginx misconfigured.

**Solution**:
```bash
# Check if build directory exists
ls -la /home/phd/app/build

# Rebuild frontend manually
cd /home/phd/app
npm run build

# Test Nginx config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Issue: Deployment Hook Not Triggering

**Cause**: Post-receive hook not executable or incorrect permissions.

**Solution**:
```bash
# Make hook executable
sudo chmod +x /home/phd/repo.git/hooks/post-receive

# Fix ownership
sudo chown -R phd:phd /home/phd/repo.git

# Test manually
sudo -u phd /home/phd/repo.git/hooks/post-receive
```

### Issue: Permission Denied on Job Files

**Cause**: Incorrect file permissions on upload directories.

**Solution**:
```bash
# Fix permissions
sudo chown -R phd:phd /home/phd/app/backend/job_files
sudo chmod -R 755 /home/phd/app/backend/job_files
```

---

## Setting Up SSL (HTTPS) - Optional

Once you have a domain name pointed to your VPS:

### Step 1: Install Certbot

```bash
sudo apt-get install certbot python3-certbot-nginx
```

### Step 2: Obtain SSL Certificate

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Step 3: Update Nginx Config

Edit `/etc/nginx/sites-available/phd-capital.conf` and uncomment the HTTPS server block, replacing `yourdomain.com` with your actual domain.

### Step 4: Auto-Renewal

Certbot automatically sets up auto-renewal. Test it with:

```bash
sudo certbot renew --dry-run
```

---

## Performance Optimization

### Enable Gunicorn Worker Auto-Scaling

Edit `/etc/systemd/system/phd-capital-backend.service`:

```ini
# Change workers based on CPU cores: (2 x CPU cores) + 1
--workers 9  # For 4-core VPS
```

### Enable Gzip Compression in Nginx

Add to `/etc/nginx/sites-available/phd-capital.conf`:

```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
```

---

## Scaling Considerations

### When to Upgrade

Monitor these metrics:
- CPU usage > 80% consistently
- RAM usage > 90%
- Response times > 3 seconds
- Database connections maxed out

### Upgrade Options

1. **Vertical Scaling**: Upgrade VPS plan for more CPU/RAM
2. **Horizontal Scaling**: Use load balancer + multiple app servers
3. **Database Scaling**: Separate PostgreSQL server
4. **CDN**: Use Cloudflare for static assets

---

## Security Checklist

- ✅ Firewall enabled (UFW)
- ✅ Fail2ban installed for SSH protection
- ✅ Non-root user for app (`phd`)
- ✅ Environment variables in secure file (`chmod 600`)
- ✅ Database password changed from default
- ✅ Secret keys generated randomly
- ✅ PostgreSQL only accessible locally
- ✅ CORS configured for specific origins
- ⬜ SSL certificate installed (optional but recommended)
- ⬜ Regular backups scheduled
- ⬜ System updates automated

---

## Support & Maintenance

### Regular Maintenance Tasks

**Weekly**:
- Check disk space: `df -h`
- Review error logs
- Monitor application performance

**Monthly**:
- Update system packages: `sudo apt update && sudo apt upgrade`
- Database backup
- Review security patches

**Quarterly**:
- Review and rotate API keys
- Update Python/Node dependencies
- Performance optimization review

---

## Quick Reference Commands

```bash
# Deploy updates
git push vps main

# Restart everything
sudo systemctl restart phd-capital-backend nginx

# View live logs
sudo journalctl -u phd-capital-backend -f

# Database backup
sudo -u postgres pg_dump phd-capital > backup.sql

# Check all services
sudo systemctl status phd-capital-backend nginx postgresql

# Update environment variables
sudo nano /etc/phd-capital.env
sudo systemctl restart phd-capital-backend
```

---

## Need Help?

If you encounter issues not covered here:

1. Check the logs (see Monitoring section)
2. Verify environment variables are correct
3. Ensure all services are running
4. Check firewall rules: `sudo ufw status`
5. Test database connection manually

---

**Congratulations!** 🎉 Your PHD Capital Rationale Studio is now deployed and ready for production use!
