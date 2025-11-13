# 🚀 Ready to Push to GitHub & Deploy

## ✅ System Status

Your codebase is now **production-ready**:

- ✅ All bugs fixed
- ✅ Database-based API system understood
- ✅ Repository cleaned (no build/, no temp files)
- ✅ Fresh deployment scripts created
- ✅ .gitignore properly configured
- ✅ Frontend builds successfully
- ✅ Complete documentation included

---

## 📝 Push to GitHub

Run these commands in your **Replit Shell**:

```bash
# Stage all changes
git add .

# Commit
git commit -m "Production-ready: Fresh deployment system with database-based API management"

# Push to GitHub
git push origin main
```

---

## 🚀 Deploy to Hostinger VPS

### Step 1: Open Windows PowerShell

Press `Windows + X`, select **"Windows PowerShell"**

### Step 2: Connect via SSH

```powershell
ssh root@72.60.111.9
```

Enter your root password when prompted.

### Step 3: Run One-Command Deployment

```bash
# Download deployment script
cd /root
curl -o deploy.sh https://raw.githubusercontent.com/sudiptarafdar7-spec/PHD-Capital-Rationale-Studio-v1/main/deployment/deploy.sh

# Make executable
chmod +x deploy.sh

# Run deployment (5-10 minutes)
bash deploy.sh
```

**That's it!** The script will:
- Install all dependencies
- Create database: phd_rationale_db
- Clone your GitHub repo
- Setup Python venv
- Build React frontend
- Configure Nginx + domain
- Start your application

---

## 🔐 After Deployment

### 1. Configure DNS (if not done)

Go to your domain registrar and add:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | 72.60.111.9 | 3600 |
| A | www | 72.60.111.9 | 3600 |

Wait 5-60 minutes for DNS propagation.

### 2. Install SSL Certificate

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d researchrationale.in -d www.researchrationale.in
```

### 3. Add API Keys via Admin Panel

1. Visit: **https://researchrationale.in/login**
2. Login with:
   - Username: `admin@phdcapital.com`
   - Password: `admin123`
3. **CHANGE PASSWORD IMMEDIATELY!**
4. Navigate to: **API Keys** (in sidebar)
5. Add all 4 keys:
   - **openai** → Your OpenAI API key
   - **dhan** → Your Dhan API key
   - **assemblyai** → Your AssemblyAI API key
   - **google_cloud** → Upload Google Cloud JSON file

**Now your pipeline will work!**

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| **deployment/DEPLOYMENT-GUIDE.md** | Complete step-by-step guide with Windows PowerShell SSH instructions, troubleshooting, SSL setup, monitoring |
| **deployment/deploy.sh** | Main deployment script (auto-installs everything) |
| **deployment/update.sh** | Quick update script for code changes |
| **deployment/README.md** | Quick reference guide |

---

## 🎯 Your URLs

After successful deployment:

- **HTTP:** http://researchrationale.in
- **HTTPS:** https://researchrationale.in (after SSL)
- **WWW:** https://www.researchrationale.in
- **Direct IP:** http://72.60.111.9

---

## ⚠️ IMPORTANT: Google Cloud Credentials

The leaked `google-cloud.json` file was removed. You **MUST**:

1. Go to **Google Cloud Console**
2. **REVOKE/DELETE** the old service account
3. Create a **NEW** service account
4. Download **NEW** JSON credentials
5. Upload via Admin Panel > API Keys > google_cloud

---

## 📊 Useful Commands

```bash
# Check application status
systemctl status phd-capital

# View live logs
journalctl -u phd-capital -f

# Restart application
systemctl restart phd-capital

# Update after git push
cd /var/www/rationale-studio
bash deployment/update.sh
```

---

## ✅ Success Checklist

- [ ] Code pushed to GitHub
- [ ] SSH connected to VPS (72.60.111.9)
- [ ] Deployment script completed successfully
- [ ] Application running: `systemctl status phd-capital`
- [ ] Can access: http://72.60.111.9
- [ ] DNS configured (A records)
- [ ] SSL certificate installed
- [ ] HTTPS working: https://researchrationale.in
- [ ] Admin password changed
- [ ] All 4 API keys added via admin panel
- [ ] Test video processing works

---

**🚀 Ready to deploy! Push to GitHub and run the deployment script!**
