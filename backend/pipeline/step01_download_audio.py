"""
Step 1: Download Audio from YouTube Video
Using yt-dlp command-line tool (simple subprocess approach)
"""
import os
import subprocess


def download_audio(job_id, youtube_url, cookies_file=None):
    """
    Simple YouTube audio downloader using yt-dlp
    
    Args:
        job_id: Job identifier
        youtube_url: YouTube video URL
        cookies_file: Not used (kept for compatibility)
    
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
    print("🎧 YOUTUBE AUDIO DOWNLOADER")
    print("="*60 + "\n")
    
    # Paths
    audio_folder = os.path.join("backend", "job_files", job_id, "audio")
    os.makedirs(audio_folder, exist_ok=True)
    
    raw_audio_path = os.path.join(audio_folder, "raw_audio.m4a")
    prepared_audio_path = os.path.join(audio_folder, "audio_16k_mono.wav")
    
    print(f"📹 URL: {youtube_url}")
    print(f"⏬ Downloading audio with yt-dlp...\n")
    
    # Use yt-dlp to download audio - simple and reliable
    try:
        ytdlp_cmd = [
            "env", "-i",
            "PATH=/nix/store/am2x1y1qyja0hbyjpffj7rcvycp9d644-yt-dlp-2025.6.30/bin:/usr/bin:/bin",
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio",  # Best audio in m4a format
            "-o", raw_audio_path,                   # Output file
            "--no-playlist",                        # Don't download playlists
            "--no-warnings",                        # Suppress warnings
            "--quiet",                              # Quiet mode
            "--progress",                           # Show progress
            youtube_url
        ]
        
        result = subprocess.run(ytdlp_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            return {
                "success": False,
                "error": f"yt-dlp failed: {error_msg}"
            }
        
        # Verify file was downloaded
        if not os.path.exists(raw_audio_path) or os.path.getsize(raw_audio_path) == 0:
            return {
                "success": False,
                "error": "Downloaded file is empty or doesn't exist"
            }
        
        size_mb = os.path.getsize(raw_audio_path) / (1024 * 1024)
        print(f"✅ Audio downloaded: {raw_audio_path} ({size_mb:.2f} MB)")
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Download timed out after 5 minutes"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Download failed: {str(e)}"
        }
    
    # Convert to 16kHz mono WAV
    print("\n" + "="*60)
    print("🔊 Converting to 16kHz mono WAV for transcription")
    print("="*60)
    
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
        return {
            "success": False,
            "error": f"FFmpeg conversion failed: {result.stderr}"
        }
    
    print("✅ Audio converted successfully!")
    
    # Calculate sizes
    raw_size_mb = round(os.path.getsize(raw_audio_path) / (1024 * 1024), 2)
    prepared_size_mb = round(os.path.getsize(prepared_audio_path) / (1024 * 1024), 2)
    
    print(f"\n📊 Final Results:")
    print(f"   📦 Raw audio: {raw_size_mb} MB")
    print(f"   🎵 Prepared audio: {prepared_size_mb} MB")
    print(f"   Status: ✅ SUCCESS\n")
    
    return {
        "success": True,
        "raw_audio": raw_audio_path,
        "prepared_audio": prepared_audio_path,
        "raw_size_mb": raw_size_mb,
        "prepared_size_mb": prepared_size_mb,
        "error": None,
    }
