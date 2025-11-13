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
bash deployment/update.sh
```

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
bash deployment/update.sh
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

# Backup
sudo -u postgres pg_dump phd_rationale_db > backup.sql
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

## 🆘 Troubleshooting

### App Not Running?
```bash
systemctl status phd-capital
journalctl -u phd-capital -n 50
systemctl restart phd-capital
```

### Can't Login?
```bash
cd /var/www/rationale-studio
source venv/bin/activate
python3.11 -m backend.seed_data
deactivate
```

### Fresh Start
```bash
systemctl stop phd-capital
rm -rf /var/www/rationale-studio
cd /root && bash deploy.sh
```

---

## 📁 Important Paths

- **Project:** `/var/www/rationale-studio`
- **Environment:** `/var/www/rationale-studio/.env`
- **Service:** `/etc/systemd/system/phd-capital.service`
- **Nginx:** `/etc/nginx/sites-available/rationale-studio`
- **Logs:** `journalctl -u phd-capital -f`

---

## 📚 Full Guide

See `DEPLOYMENT-GUIDE.md` for complete documentation including:
- Detailed Windows PowerShell SSH instructions
- API key configuration
- Troubleshooting steps
- Database management

---

## ✅ Deployment Checklist

- [ ] SSH: `ssh root@72.60.111.9`
- [ ] Deploy: `bash deploy.sh`
- [ ] Login: `admin@phdcapital.in` / `admin123`
- [ ] Add API keys in Admin Panel
- [ ] (Optional) SSL: `certbot --nginx`

**Done!** 🎉
