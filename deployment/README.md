# 🚀 Quick Deployment Reference

## Server Details
- **IP:** 72.60.111.9
- **Domain:** researchrationale.in
- **Project:** rationale-studio
- **OS:** Ubuntu 24.04 LTS

---

## 🎯 One-Command Deployment

### First Time Setup
```bash
# SSH to server
ssh root@72.60.111.9

# Download and run deployment
cd /root
curl -o deploy.sh https://raw.githubusercontent.com/sudiptarafdar7-spec/PHD-Capital-Rationale-Studio-Ready/main/deployment/deploy.sh
chmod +x deploy.sh
bash deploy.sh
```

**Wait 10-15 minutes** ☕

---

## 🔄 Quick Update (After Git Push)

```bash
ssh root@72.60.111.9
cd /var/www/rationale-studio
sudo bash deployment/update.sh
```

### What the Update Script Does:
1. ✅ Creates database backup (preserves your data!)
2. ✅ Backs up environment file
3. ✅ Pulls latest code from GitHub
4. ✅ Updates Python dependencies
5. ✅ Updates Node.js dependencies
6. ✅ Rebuilds React frontend
7. ✅ Runs database schema migration (safe - only adds new columns)
8. ✅ Restarts application
9. ✅ Verifies everything is running

### Your Data is SAFE:
- ✅ All users preserved
- ✅ All jobs preserved
- ✅ All saved rationales preserved
- ✅ All uploaded files (master CSV, logos, fonts) preserved
- ✅ All API keys preserved
- ✅ All channel configurations preserved

---

## 🔑 Default Login

- **Email:** admin@phdcapital.in
- **Password:** admin123

---

## 📋 Common Commands

### Application
```bash
# Status
systemctl status phd-capital

# Logs (live)
journalctl -u phd-capital -f

# Restart
systemctl restart phd-capital

# Update after git push
cd /var/www/rationale-studio
sudo bash deployment/update.sh
```

### Nginx
```bash
# Test config
nginx -t

# Restart
systemctl restart nginx

# Logs
tail -f /var/log/nginx/error.log
```

### Database
```bash
# Connect
sudo -u postgres psql -d phd_rationale_db

# Backup manually
sudo -u postgres pg_dump phd_rationale_db > backup.sql

# View automatic backups
ls -la /var/www/rationale-studio-backups/
```

---

## 🔐 SSL Setup (Optional)

```bash
# First verify DNS points to 72.60.111.9
dig researchrationale.in +short

# Install certbot
apt install -y certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d researchrationale.in -d www.researchrationale.in
```

---

## 💾 Backups

Automatic backups are created in `/var/www/rationale-studio-backups/`:
- Database backups: `db_backup_YYYYMMDD_HHMMSS.sql`
- Environment backups: `.env_backup_YYYYMMDD_HHMMSS`
- Last 10 backups are kept automatically

### Restore from Backup
```bash
# Restore database
sudo -u postgres psql phd_rationale_db < /var/www/rationale-studio-backups/db_backup_XXXXXXXX_XXXXXX.sql

# Restore environment
cp /var/www/rationale-studio-backups/.env_backup_XXXXXXXX_XXXXXX /var/www/rationale-studio/.env
systemctl restart phd-capital
```

---

## 🆘 Troubleshooting

### App Not Running?
```bash
systemctl status phd-capital
journalctl -u phd-capital -n 50
systemctl restart phd-capital
```

### Step 8 Failing? (Database Schema Issue)
```bash
cd /var/www/rationale-studio
source venv/bin/activate
python3.11 backend/migrations/run_migration.py
deactivate
systemctl restart phd-capital
```

### Can't Login?
```bash
cd /var/www/rationale-studio
source venv/bin/activate
python3.11 -m backend.seed_data
deactivate
```

### Fresh Start (CAUTION: Deletes all data!)
```bash
systemctl stop phd-capital
rm -rf /var/www/rationale-studio
cd /root && bash deploy.sh
```

---

## 📁 Important Paths

- **Project:** `/var/www/rationale-studio`
- **Environment:** `/var/www/rationale-studio/.env`
- **Backups:** `/var/www/rationale-studio-backups/`
- **Service:** `/etc/systemd/system/phd-capital.service`
- **Nginx:** `/etc/nginx/sites-available/rationale-studio`
- **Uploaded Files:** `/var/www/rationale-studio/backend/uploaded_files/`
- **Job Files:** `/var/www/rationale-studio/backend/job_files/`
- **Logs:** `journalctl -u phd-capital -f`

---

## 📚 Full Guide

See `DEPLOYMENT-GUIDE.md` for complete documentation including:
- Detailed Windows PowerShell SSH instructions
- API key configuration
- Troubleshooting steps
- Database management

---

## ✅ Update Checklist

After pushing changes to GitHub:

- [ ] SSH: `ssh root@72.60.111.9`
- [ ] Navigate: `cd /var/www/rationale-studio`
- [ ] Update: `sudo bash deployment/update.sh`
- [ ] Verify: Check "UPDATE COMPLETE!" message
- [ ] Test: Visit http://researchrationale.in

**Done!** 🎉
