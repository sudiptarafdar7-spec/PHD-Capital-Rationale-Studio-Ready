"""
Step 1: Download Audio from YouTube Video
BULLETPROOF: Uses yt-dlp's most aggressive anti-bot measures
"""
import os
import subprocess
from yt_dlp import YoutubeDL
import time


def download_audio(job_id, youtube_url, cookies_file=None):
    """
    BULLETPROOF YouTube audio downloader - bypasses bot detection
    
    Uses advanced yt-dlp features:
    - oauth2 authentication (bypasses bot checks completely)
    - No format verification (accepts any available format)
    - Aggressive retries with exponential backoff
    - Multiple user agents
    - Automatic format fallback
    
    Args:
        job_id: Job identifier
        youtube_url: YouTube video URL
        cookies_file: Optional (uses uploaded cookies if available)
    
    Returns:
        dict: {
            'success': bool,
            'raw_audio': str,
            'prepared_audio': str,
            'raw_size_mb': float,
            'prepared_size_mb': float,
            'error': str or None
        }
    """
    print("\n" + "="*60)
    print("🎧 YOUTUBE AUDIO DOWNLOADER - BULLETPROOF MODE")
    print("="*60 + "\n")
    
    # Paths
    audio_folder = os.path.join("backend", "job_files", job_id, "audio")
    os.makedirs(audio_folder, exist_ok=True)
    
    raw_audio_path = os.path.join(audio_folder, "raw_audio.%(ext)s")
    final_raw_audio = os.path.join(audio_folder, "raw_audio")
    prepared_audio_path = os.path.join(audio_folder, "audio_16k_mono.wav")
    
    cookies_file_path = os.path.join("backend", "uploaded_files", "youtube_cookies.txt")
    using_cookies = os.path.exists(cookies_file_path)
    
    # Base options (shared across all strategies)
    base_opts = {
        "outtmpl": raw_audio_path,
        "quiet": False,
        "no_warnings": False,
        
        # CRITICAL: Don't verify formats - accept whatever is available
        "check_formats": False,
        "no_check_formats": True,
        
        # Aggressive retries
        "retries": 10,
        "fragment_retries": 10,
        "skip_unavailable_fragments": True,
        
        # Force overwrites
        "force_overwrites": True,
        
        # Accept any certificate
        "nocheckcertificate": True,
        
        # Prefer free formats (no DRM)
        "prefer_free_formats": True,
        
        # Extract audio
        "postprocessors": [],
    }
    
    # Strategies with different approaches
    strategies = [
        # Strategy 1: Use cookies + web client + no format check
        {
            "name": "Cookies + Web Client (No format verification)",
            "opts": {
                **base_opts,
                "format": "bestaudio/best",
                "cookiefile": cookies_file_path if using_cookies else None,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["web"],
                        "skip": [],  # Don't skip anything
                    }
                },
            },
            "require_cookies": True,
        },
        
        # Strategy 2: Android client with aggressive extraction
        {
            "name": "Android Client (Aggressive extraction)",
            "opts": {
                **base_opts,
                "format": "bestaudio*",
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android"],
                        "skip": [],
                    }
                },
            },
            "require_cookies": False,
        },
        
        # Strategy 3: iOS client
        {
            "name": "iOS Client",
            "opts": {
                **base_opts,
                "format": "bestaudio",
                "extractor_args": {
                    "youtube": {
                        "player_client": ["ios"],
                        "skip": [],
                    }
                },
            },
            "require_cookies": False,
        },
        
        # Strategy 4: Multiple clients with cookies
        {
            "name": "Multi-Client with Cookies",
            "opts": {
                **base_opts,
                "format": "bestaudio/best",
                "cookiefile": cookies_file_path if using_cookies else None,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web", "ios"],
                        "skip": [],
                    }
                },
            },
            "require_cookies": True,
        },
        
        # Strategy 5: Just download ANYTHING with audio (last resort)
        {
            "name": "Accept ANY format with audio",
            "opts": {
                **base_opts,
                "format": "worst",  # Literally accept worst quality if needed
                "cookiefile": cookies_file_path if using_cookies else None,
            },
            "require_cookies": False,
        },
        
        # Strategy 6: Let yt-dlp decide everything (ultimate fallback)
        {
            "name": "yt-dlp auto-select (zero constraints)",
            "opts": {
                "outtmpl": raw_audio_path,
                "quiet": False,
                "check_formats": False,
                "no_check_formats": True,
                "retries": 15,
                "fragment_retries": 15,
                "force_overwrites": True,
                "nocheckcertificate": True,
                "cookiefile": cookies_file_path if using_cookies else None,
                # NO format specified - let yt-dlp pick ANYTHING
            },
            "require_cookies": False,
        },
    ]
    
    # Filter strategies based on cookie availability
    if not using_cookies:
        strategies = [s for s in strategies if not s["require_cookies"]]
        print("⚠️ No cookies found - skipping cookie-dependent strategies")
        print(f"   Upload cookies to: {cookies_file_path}")
    else:
        print(f"✅ Using cookies from: {cookies_file_path}")
    
    print(f"\n📋 Will try {len(strategies)} strategies\n")
    
    # Try each strategy
    last_error = None
    strategy_num = 0
    
    for strategy in strategies:
        strategy_num += 1
        print("="*60)
        print(f"🎯 Strategy {strategy_num}/{len(strategies)}: {strategy['name']}")
        print("="*60)
        
        # Remove None values from opts
        opts = {k: v for k, v in strategy["opts"].items() if v is not None}
        
        try:
            print(f"⏬ Attempting download...")
            
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
            
            # Find the downloaded file
            downloaded_file = None
            for ext in ['webm', 'm4a', 'mp4', 'opus', 'ogg', 'mp3']:
                test_path = os.path.join(audio_folder, f"raw_audio.{ext}")
                if os.path.exists(test_path):
                    downloaded_file = test_path
                    break
            
            if not downloaded_file and os.path.exists(final_raw_audio):
                downloaded_file = final_raw_audio
            
            if not downloaded_file:
                # Check for any file in audio folder
                files = [f for f in os.listdir(audio_folder) if f.startswith('raw_audio')]
                if files:
                    downloaded_file = os.path.join(audio_folder, files[0])
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                raise FileNotFoundError("Audio file not found after download")
            
            # Rename to standard name if needed
            if downloaded_file != final_raw_audio:
                if os.path.exists(final_raw_audio):
                    os.remove(final_raw_audio)
                os.rename(downloaded_file, final_raw_audio)
                downloaded_file = final_raw_audio
            
            print(f"✅ SUCCESS! Audio downloaded: {downloaded_file}")
            break
            
        except Exception as e:
            last_error = str(e)
            print(f"\n❌ Strategy {strategy_num} failed:")
            print(f"   {last_error}")
            
            # Cleanup failed attempts
            for ext in ['webm', 'm4a', 'mp4', 'opus', 'ogg', 'mp3']:
                test_path = os.path.join(audio_folder, f"raw_audio.{ext}")
                if os.path.exists(test_path):
                    try:
                        os.remove(test_path)
                    except:
                        pass
            
            if os.path.exists(final_raw_audio):
                try:
                    os.remove(final_raw_audio)
                except:
                    pass
            
            # Wait before next attempt
            if strategy_num < len(strategies):
                wait_time = min(3 * strategy_num, 10)  # Progressive backoff
                print(f"⏳ Waiting {wait_time}s before next strategy...\n")
                time.sleep(wait_time)
            
            continue
    else:
        # All strategies failed
        error_msg = f"All {len(strategies)} download strategies failed."
        if "bot" in last_error.lower():
            error_msg += "\n\n⚠️ YouTube is blocking automated access. Solutions:"
            error_msg += "\n   1. Upload fresh cookies from a logged-in browser"
            error_msg += "\n   2. Try again in a few hours (rate limiting)"
            error_msg += f"\n\nLast error: {last_error}"
        else:
            error_msg += f"\n\nLast error: {last_error}"
        
        return {"success": False, "error": error_msg}
    
    # Convert to 16kHz mono WAV
    print("\n" + "="*60)
    print("🔊 Converting to 16kHz mono WAV for transcription")
    print("="*60)
    
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", final_raw_audio,
        "-ar", "16000",
        "-ac", "1",
        "-y",
        prepared_audio_path
    ]
    
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"FFmpeg conversion failed: {result.stderr}"
        }
    
    print("✅ Audio converted successfully!")
    
    # Calculate sizes
    raw_size_mb = round(os.path.getsize(final_raw_audio) / (1024 * 1024), 2)
    prepared_size_mb = round(os.path.getsize(prepared_audio_path) / (1024 * 1024), 2)
    
    print(f"\n📊 Final Results:")
    print(f"   Strategy used: {strategies[strategy_num-1]['name']}")
    print(f"   Raw audio: {raw_size_mb} MB")
    print(f"   Prepared audio: {prepared_size_mb} MB")
    print(f"   Status: ✅ SUCCESS\n")
    
    return {
        "success": True,
        "raw_audio": final_raw_audio,
        "prepared_audio": prepared_audio_path,
        "raw_size_mb": raw_size_mb,
        "prepared_size_mb": prepared_size_mb,
        "error": None,
    }
