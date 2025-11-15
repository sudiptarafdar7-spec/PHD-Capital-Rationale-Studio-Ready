"""
Step 1: Download Audio from YouTube Video
Using external RapidAPI YouTube to MP3 converter
"""
import os
import subprocess
import requests
import re


def download_audio(job_id, youtube_url, cookies_file=None):
    """
    Simple YouTube audio downloader using external API
    
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
    
    raw_audio_path = os.path.join(audio_folder, "raw_audio.mp3")
    prepared_audio_path = os.path.join(audio_folder, "audio_16k_mono.wav")
    
    # Extract video ID from URL
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return {
            "success": False,
            "error": f"Could not extract video ID from URL: {youtube_url}"
        }
    
    print(f"📹 Video ID: {video_id}")
    print(f"⏬ Requesting audio conversion...\n")
    
    # Call RapidAPI to get download link
    try:
        api_url = "https://youtube-mp36.p.rapidapi.com/dl"
        querystring = {"id": video_id}
        headers = {
            "x-rapidapi-key": "c7762ba089msh6c8a18942b1f9cdp1bbc0cjsn10d61d38bef5",
            "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
        }
        
        response = requests.get(api_url, headers=headers, params=querystring, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != "ok":
            return {
                "success": False,
                "error": f"API returned status: {data.get('status')}, message: {data.get('msg')}"
            }
        
        download_link = data.get("link")
        video_title = data.get("title", "Unknown")
        
        if not download_link:
            return {
                "success": False,
                "error": "API did not return a download link"
            }
        
        print(f"✅ Audio ready: {video_title}")
        print(f"📥 Downloading from API...\n")
        
        # Download the MP3 file
        audio_response = requests.get(download_link, timeout=120, stream=True)
        audio_response.raise_for_status()
        
        with open(raw_audio_path, 'wb') as f:
            for chunk in audio_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Audio downloaded: {raw_audio_path}")
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}"
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


def extract_video_id(youtube_url):
    """
    Extract YouTube video ID from various URL formats
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'[?&]v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    
    return None
