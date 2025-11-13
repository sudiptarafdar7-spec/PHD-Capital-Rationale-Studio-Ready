# YouTube Cookies Export Guide

## Why Do I Need This?

YouTube has implemented bot detection that sometimes blocks automated video downloads. By providing YouTube cookies from an authenticated browser session, you can bypass this restriction.

## When Do I Need YouTube Cookies?

Upload YouTube cookies when you see this error during video downloads:
```
ERROR: Sign in to confirm you're not a bot
```

## How to Export YouTube Cookies

### Method 1: Using Browser Extension (Recommended)

#### For Chrome/Edge/Brave:

1. **Install the Extension**
   - Go to: https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
   - Click "Add to Chrome" / "Add to Edge"

2. **Visit YouTube**
   - Open https://youtube.com in your browser
   - Make sure you're logged into your YouTube account

3. **Export Cookies**
   - Click the "Get cookies.txt LOCALLY" extension icon in your browser toolbar
   - The extension will automatically download a file named `youtube.com_cookies.txt`

4. **Rename the File**
   - Rename the downloaded file to exactly: `youtube_cookies.txt`

5. **Upload to Rationale Studio**
   - Log into Rationale Studio as Admin
   - Go to **Settings > Upload Files**
   - Find the "YouTube Cookies File" section
   - Click "Upload File" and select your `youtube_cookies.txt` file

#### For Firefox:

1. **Install the Extension**
   - Go to: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/
   - Click "Add to Firefox"

2. **Follow steps 2-5 above** (same as Chrome)

### Method 2: Manual Export (Advanced Users)

If you prefer not to use browser extensions, you can manually export cookies using browser DevTools:

1. Open YouTube in your browser (logged in)
2. Press F12 to open Developer Tools
3. Go to Application tab (Chrome) or Storage tab (Firefox)
4. Click "Cookies" > "https://www.youtube.com"
5. Export cookies in Netscape format (requires additional tools)

**Note:** Method 1 (Browser Extension) is much easier and recommended.

## Important Security Notes

⚠️ **Never share your cookies file with anyone!**
- Cookies contain your YouTube authentication tokens
- Anyone with your cookies can access your YouTube account
- The file is stored securely on the server and never leaves your system

✅ **Best Practices:**
- Only upload cookies from your own YouTube account
- Re-export cookies if you sign out of YouTube or change your password
- Delete the cookies file from your Downloads folder after uploading

## How Long Do Cookies Last?

YouTube cookies typically expire after a few months. If you start seeing bot detection errors again:
1. Re-export fresh cookies from your browser
2. Upload the new cookies file to replace the old one

## Troubleshooting

**Q: I uploaded cookies but still get bot detection errors**
- Make sure you're logged into YouTube when exporting cookies
- Try using a different browser
- Re-export cookies and try again

**Q: The extension doesn't work**
- Make sure you're on the actual YouTube.com website (not embedded videos)
- Try refreshing the page and exporting again
- Check if the extension needs to be updated

**Q: Is this safe?**
- Yes, when using official browser extensions
- Cookies are stored securely on your server
- Only you (as admin) have access to upload/manage cookies

## Video Tutorial Links

- **Get cookies.txt LOCALLY (Chrome)**: https://youtu.be/OmLYprPwJPw
- **Alternative Guide**: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp

## Need Help?

If you continue experiencing issues after uploading cookies, please contact technical support with:
- The exact error message you're seeing
- The browser you used to export cookies
- Screenshots of the error (if possible)
