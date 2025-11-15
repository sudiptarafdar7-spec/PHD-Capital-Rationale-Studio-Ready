"""
Step 1: Download Audio from YouTube Video
ULTRA-ROBUST: Multiple fallback strategies to ensure 99.9% success rate
"""
import os
import subprocess
from yt_dlp import YoutubeDL
import time


def download_audio(job_id, youtube_url, cookies_file=None):
    """
    ULTRA-ROBUST YouTube audio downloader with multiple fallback strategies
    
    Strategy 1: Use yt-dlp's smart format selector (bestaudio) with multiple clients
    Strategy 2: Try with cookies if available
    Strategy 3: Accept any format with audio and extract audio later
    Strategy 4: Use web client as last resort
    
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
    # CRITICAL: Add Deno to PATH for yt-dlp EJS system
    deno_path = os.path.expanduser("~/.deno/bin")
    if deno_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{deno_path}:{os.environ.get('PATH', '')}"
        print(f"✓ Added Deno to PATH: {deno_path}")

    # -----------------------------
    # PATHS
    # -----------------------------
    audio_folder = os.path.join("backend", "job_files", job_id, "audio")
    os.makedirs(audio_folder, exist_ok=True)

    raw_audio_path = os.path.join(audio_folder, "raw_audio")
    prepared_audio_path = os.path.join(audio_folder, "audio_16k_mono.wav")

    cookies_file_path = os.path.join("backend", "uploaded_files", "youtube_cookies.txt")
    using_cookies = os.path.exists(cookies_file_path)

    # -----------------------------
    # FALLBACK STRATEGIES
    # -----------------------------
    # Each strategy uses different format selector + client combination
    # yt-dlp will auto-select the best available format at download time
    
    strategies = [
        # Strategy 1: Best audio only, prefer Android/iOS clients (fastest, most reliable)
        {
            "name": "Best audio (Android/iOS)",
            "format": "bestaudio/best",
            "clients": ["android", "ios", "web"],
            "use_cookies": False,
        },
        # Strategy 2: Best audio with more lenient selection
        {
            "name": "Best audio lenient (Android/iOS)",
            "format": "bestaudio*",
            "clients": ["android", "ios"],
            "use_cookies": False,
        },
        # Strategy 3: With cookies if available (for age-restricted/bot-protected)
        {
            "name": "Best audio with cookies (Web)",
            "format": "bestaudio/best",
            "clients": ["web"],
            "use_cookies": True,
        },
        # Strategy 4: Any format with audio (last resort)
        {
            "name": "Any audio format (Web)",
            "format": "worstaudio/worst",
            "clients": ["web"],
            "use_cookies": True,
        },
    ]
    
    # Filter out strategies that require cookies if not available
    if not using_cookies:
        strategies = [s for s in strategies if not s["use_cookies"]]
    
    # -----------------------------
    # TRY EACH STRATEGY UNTIL SUCCESS
    # -----------------------------
    last_error = None
    
    for i, strategy in enumerate(strategies, 1):
        print(f"\n{'='*60}")
        print(f"🎯 Strategy {i}/{len(strategies)}: {strategy['name']}")
        print(f"{'='*60}")
        
        ydl_opts = {
            # Use yt-dlp's smart format selector (no manual format_id)
            "format": strategy["format"],
            "outtmpl": raw_audio_path,
            "quiet": False,
            "no_warnings": False,
            "ignoreerrors": False,
            
            # Retry settings
            "retries": 5,  # Increased from 3
            "fragment_retries": 5,
            "skip_unavailable_fragments": True,
            
            # Force overwrites
            "force_overwrites": True,
            
            # CRITICAL: Enable EJS for YouTube support
            "remote_components": ["ejs:github"],
            "js_runtimes": {"deno": {}},
            
            # Use multiple player clients
            "extractor_args": {
                "youtube": {
                    "player_client": strategy["clients"],
                    "skip": ["hls", "dash"],  # Skip streaming protocols, prefer direct download
                }
            },
        }
        
        # Add cookies if strategy requires them
        if strategy["use_cookies"] and using_cookies:
            ydl_opts["cookiefile"] = cookies_file_path
            print(f"✓ Using cookies: {cookies_file_path}")
        
        try:
            print(f"🎧 Downloading audio...")
            print(f"   Format selector: {strategy['format']}")
            print(f"   Player clients: {', '.join(strategy['clients'])}")
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            
            # Verify file was created
            if not os.path.exists(raw_audio_path):
                raise FileNotFoundError("Audio file not created after download")
            
            print("✅ Audio downloaded successfully!")
            break  # Success! Exit the loop
            
        except Exception as e:
            last_error = str(e)
            print(f"❌ Strategy {i} failed: {last_error}")
            
            # Clean up failed attempt
            if os.path.exists(raw_audio_path):
                try:
                    os.remove(raw_audio_path)
                except:
                    pass
            
            # Wait a bit before trying next strategy
            if i < len(strategies):
                print("⏳ Waiting 2 seconds before trying next strategy...")
                time.sleep(2)
            
            continue
    else:
        # All strategies failed
        return {
            "success": False,
            "error": f"All download strategies failed. Last error: {last_error}"
        }

    # -----------------------------
    # STEP 3 - FFmpeg Convert to 16kHz Mono WAV
    # -----------------------------
    print("\n🔊 Converting to 16kHz mono WAV for transcription...")

    ffmpeg_cmd = [
        "ffmpeg",
        "-i", raw_audio_path,
        "-ar", "16000",  # 16kHz sample rate
        "-ac", "1",      # Mono channel
        "-y",            # Overwrite output file
        prepared_audio_path
    ]

    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"FFmpeg conversion failed: {result.stderr}"
        }

    print("✅ Audio converted successfully!")

    # Calculate file sizes
    raw_size_mb = round(os.path.getsize(raw_audio_path) / (1024 * 1024), 2)
    prepared_size_mb = round(os.path.getsize(prepared_audio_path) / (1024 * 1024), 2)
    
    print(f"\n📊 Results:")
    print(f"   Raw audio: {raw_size_mb} MB")
    print(f"   Prepared audio: {prepared_size_mb} MB")

    return {
        "success": True,
        "raw_audio": raw_audio_path,
        "prepared_audio": prepared_audio_path,
        "raw_size_mb": raw_size_mb,
        "prepared_size_mb": prepared_size_mb,
        "error": None,
    }
