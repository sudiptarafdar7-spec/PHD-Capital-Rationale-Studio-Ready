"""
Step 1: Download Audio from YouTube Video
Using RapidAPI YouTube Media Downloader
"""
import os
import subprocess
import requests
import re


def download_audio(job_id, youtube_url, cookies_file=None):
    """
    Simple YouTube audio downloader using RapidAPI
    
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
    
    # Extract video ID from URL
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return {
            "success": False,
            "error": f"Could not extract video ID from URL: {youtube_url}"
        }
    
    print(f"📹 Video ID: {video_id}")
    print(f"⏬ Fetching audio download link...\n")
    
    # Call RapidAPI to get video details with audio download link
    try:
        # Get API key from environment (fallback to provided key for convenience)
        rapidapi_key = os.environ.get(
            "RAPIDAPI_KEY",
            "c7762ba089msh6c8a18942b1f9cdp1bbc0cjsn10d61d38bef5"
        )
        
        api_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
        querystring = {
            "videoId": video_id,
            "urlAccess": "normal",
            "videos": "auto",
            "audios": "auto"
        }
        headers = {
            "x-rapidapi-key": rapidapi_key,
            "x-rapidapi-host": "youtube-media-downloader.p.rapidapi.com"
        }
        
        print(f"📡 Calling API...")
        response = requests.get(api_url, headers=headers, params=querystring, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for errors
        if data.get("errorId") != "Success":
            return {
                "success": False,
                "error": f"API error: {data.get('errorId', 'Unknown error')}"
            }
        
        # Get video title
        video_title = data.get("title", "Unknown")
        print(f"📹 Video: {video_title}")
        
        # Extract audio download URL
        audios = data.get("audios", {})
        if audios.get("errorId") != "Success":
            return {
                "success": False,
                "error": f"Audio extraction failed: {audios.get('errorId', 'Unknown error')}"
            }
        
        audio_items = audios.get("items", [])
        if not audio_items:
            return {
                "success": False,
                "error": "No audio streams available for this video"
            }
        
        # Get the first audio item (usually best quality)
        audio_item = audio_items[0]
        download_link = audio_item.get("url")
        audio_size = audio_item.get("sizeText", "Unknown size")
        
        if not download_link:
            return {
                "success": False,
                "error": "API did not return an audio download URL"
            }
        
        print(f"✅ Audio found: {audio_size}")
        print(f"🔗 Download URL obtained")
        
        print(f"📥 Downloading audio...\n")
        
        # Download the audio file
        audio_response = requests.get(download_link, timeout=120, stream=True)
        audio_response.raise_for_status()
        
        # Write to file
        with open(raw_audio_path, 'wb') as f:
            for chunk in audio_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Verify file was downloaded
        if not os.path.exists(raw_audio_path) or os.path.getsize(raw_audio_path) == 0:
            return {
                "success": False,
                "error": "Downloaded file is empty or doesn't exist"
            }
        
        size_mb = os.path.getsize(raw_audio_path) / (1024 * 1024)
        print(f"✅ Audio downloaded: {raw_audio_path} ({size_mb:.2f} MB)")
        
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
    - https://www.youtube.com/live/VIDEO_ID (live streams)
    - https://www.youtube.com/shorts/VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com\/(?:watch\?v=|embed\/|v\/|live\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'[?&]v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    
    return None
