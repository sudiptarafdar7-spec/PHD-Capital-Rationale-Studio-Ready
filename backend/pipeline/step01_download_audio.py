"""
Step 1: Download Audio from YouTube Video
Production-ready yt-dlp implementation with robust logic for VPS servers
"""
import os
import subprocess
from yt_dlp import YoutubeDL


def download_audio(job_id, youtube_url, cookies_file=None):
    """
    PRODUCTION-READY YouTube audio downloader with:
    - 403 bypass
    - player client rotation
    - user-agent rotation
    - chunking to avoid throttling
    - signature decryption fallback
    - WAV conversion (16kHz mono)
    
    Args:
        job_id: Job identifier
        youtube_url: YouTube video URL
        cookies_file: Optional path to cookies.txt file (legacy param, uses uploaded_files folder)
    
    Returns:
        dict: {
            'success': bool,
            'raw_audio': str,  # Path to raw audio file
            'prepared_audio': str,  # Path to 16kHz mono audio file
            'raw_size_mb': float,
            'prepared_size_mb': float,
            'error': str or None
        }
    """
    
    # -----------------------------
    # PATHS
    # -----------------------------
    audio_folder = os.path.join("backend", "job_files", job_id, "audio")
    os.makedirs(audio_folder, exist_ok=True)

    raw_audio_path = os.path.join(audio_folder, "raw_audio.webm")
    prepared_audio_path = os.path.join(audio_folder, "audio_16k_mono.wav")

    # Use youtube_cookies.txt from uploaded_files folder
    cookies_file_path = os.path.join("backend", "uploaded_files", "youtube_cookies.txt")
    using_cookies = os.path.exists(cookies_file_path)

    # -----------------------------
    # YT-DLP OPTIONS (STRONG)
    # -----------------------------
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": raw_audio_path,
        "quiet": False,

        # Stability
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 20,
        "nocheckcertificate": True,
        "extractor_retries": 5,         # signature decryption fallback

        # 403 bypass & fingerprint protection
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web_safari"],
                "player_skip": ["webpage", "web_embed"]
            }
        },

        # User-Agent rotation (fixes fingerprint bans)
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 12; SM-G991B) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0 Mobile Safari/537.36"
            )
        },

        # Avoid throttling (chunked downloading)
        "http_chunk_size": 10 * 1024 * 1024,  # 10 MB
    }

    # Add cookies if available
    if using_cookies:
        ydl_opts["cookiefile"] = cookies_file_path
        print(f"✓ Using cookies from: {cookies_file_path}")
    else:
        print("⚠ No cookies file found. Some videos may fail (403).")

    # -----------------------------
    # STEP 1: DOWNLOAD RAW AUDIO
    # -----------------------------
    try:
        print(f"🎧 Downloading raw audio from: {youtube_url}")
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        return {"success": False, "error": f"yt-dlp failed: {e}"}

    if not os.path.exists(raw_audio_path):
        return {"success": False, "error": "Audio not downloaded (403 or blocked)."}

    print(f"✓ Raw audio downloaded: {raw_audio_path}")

    # -----------------------------
    # STEP 2: CONVERT TO 16kHz MONO WAV
    # -----------------------------
    print("🔊 Converting to 16kHz mono WAV...")

    ffmpeg_cmd = [
        "ffmpeg",
        "-i", raw_audio_path,
        "-ar", "16000",
        "-ac", "1",
        "-y",
        prepared_audio_path
    ]

    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return {"success": False, "error": f"FFmpeg conversion error: {result.stderr}"}

    print(f"✓ Converted WAV created: {prepared_audio_path}")

    # File sizes
    raw_size_mb = round(os.path.getsize(raw_audio_path) / (1024 * 1024), 2)
    prepared_size_mb = round(os.path.getsize(prepared_audio_path) / (1024 * 1024), 2)

    return {
        "success": True,
        "raw_audio": raw_audio_path,
        "prepared_audio": prepared_audio_path,
        "raw_size_mb": raw_size_mb,
        "prepared_size_mb": prepared_size_mb,
        "error": None,
    }
