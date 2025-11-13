# Quick Start: YouTube Cookies Setup

## 📋 What You Need

1. A browser extension to export cookies
2. Access to YouTube while logged in
3. 5 minutes

## 🚀 Quick Setup Steps

### Step 1: Install Browser Extension

**For Chrome/Edge:**
1. Go to: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
2. Click "Add to Chrome"

**For Firefox:**
1. Go to: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/
2. Click "Add to Firefox"

### Step 2: Export Cookies

1. Open YouTube in your browser: https://www.youtube.com
2. **Make sure you're logged into your Google/YouTube account**
3. Click the extension icon in your browser toolbar
4. Click "Export" or "Get cookies.txt"
5. Save the file

### Step 3: Add to Project

1. Rename the downloaded file to: `youtube_cookies.txt`
2. Place it in the `backend/` directory
3. The final path should be: `backend/youtube_cookies.txt`

### Step 4: Restart Backend

1. Click the "Restart" button for the Backend workflow
2. Or wait for auto-reload

### Step 5: Test

1. Go to Media Rationale page in the app
2. Enter any YouTube URL (e.g., `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
3. Click "Fetch Video"
4. ✅ Success! Video metadata should load

## ⚠️ Important Notes

- **Never commit** `youtube_cookies.txt` to git (it's already in .gitignore)
- Cookies expire - if it stops working, re-export fresh cookies
- Must be logged into YouTube when exporting
- Works with any Google account

## 🔍 Troubleshooting

**"YouTube requires authentication" error:**
- The cookies file is missing or not named correctly
- Make sure it's exactly `youtube_cookies.txt` (not `.txt.txt`)
- Place it directly in the `backend/` folder

**Still getting bot detection error:**
- Cookies may be expired - export fresh ones
- Make sure you were logged into YouTube when exporting
- Try a different browser (Chrome vs Firefox)

**Can't find the extension icon:**
- Look in the extensions area of your browser toolbar
- May need to pin the extension to make it visible

## 📝 File Location

```
backend/
├── youtube_cookies.txt          ← Your cookies file goes here
├── youtube_cookies.txt.example  ← Template/example
└── YOUTUBE_COOKIES_SETUP.md    ← Detailed guide
```

## 🎯 Expected Result

Before cookies:
```
❌ Error: YouTube requires authentication
```

After cookies:
```
✅ Video metadata fetched successfully!
   Title: "Your Video Title"
   Channel: "Channel Name"
   Duration: "12:34"
```

---

For detailed information, see: `backend/YOUTUBE_COOKIES_SETUP.md`
