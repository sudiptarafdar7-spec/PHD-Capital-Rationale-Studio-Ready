"""
Step 1: Download Audio from YouTube Video
Uses RapidAPI YouTube Media Downloader to extract audio and converts to 16kHz mono WAV format
"""
import os
import subprocess
import requests
import re
from urllib.parse import urlparse, parse_qs
from backend.utils.database import get_db_cursor


def download_audio(job_id, youtube_url, cookies_file=None):
    """
    Download audio from YouTube video and convert to 16 kHz mono WAV
    
    Args:
        job_id: Job identifier
        youtube_url: YouTube video URL
        cookies_file: Optional path to cookies.txt file for authentication
    
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
    try:
        # Setup paths
        audio_folder = os.path.join('backend', 'job_files', job_id, 'audio')
        os.makedirs(audio_folder, exist_ok=True)

        raw_audio_path = os.path.join(audio_folder, 'raw_audio.wav')
        prepared_audio_path = os.path.join(audio_folder, 'audio_16k_mono.wav')
        temp_download_path = os.path.join(audio_folder, 'temp_download')

        # Step 1: Get RapidAPI key from database
        print(f"🔑 Fetching RapidAPI key from database...")
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT key_value FROM api_keys WHERE provider = %s",
                ('rapidapi', ))
            result = cursor.fetchone()
            if not result or not result['key_value']:
                return {
                    'success':
                    False,
                    'error':
                    'RapidAPI key not configured. Please add your RapidAPI key in the admin panel.'
                }
            rapidapi_key = result['key_value']

        # Step 2: Extract video ID from YouTube URL
        print(f"🎧 Extracting video ID from: {youtube_url}")
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return {
                'success': False,
                'error': f'Invalid YouTube URL format: {youtube_url}'
            }
        print(f"✓ Video ID: {video_id}")

        # Step 3: Get audio download URL from RapidAPI
        print(f"🌐 Fetching audio download URL from RapidAPI...")
        rapidapi_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
        querystring = {
            "videoId": video_id,
            "urlAccess": "normal",
            "videos": "false",
            "audios": "raw"
        }
        headers = {
            "x-rapidapi-key": rapidapi_key,
            "x-rapidapi-host": "youtube-media-downloader.p.rapidapi.com"
        }

        response = requests.get(rapidapi_url,
                                headers=headers,
                                params=querystring,
                                timeout=30)

        if response.status_code != 200:
            return {
                'success':
                False,
                'error':
                f'RapidAPI request failed with status {response.status_code}: {response.text}'
            }

        data = response.json()
        print(f"✓ RapidAPI response received (keys: {list(data.keys())})")

        # Check for API errors (handle both response formats)
        # Format 1: errorId field
        if 'errorId' in data and data.get('errorId') != 'Success':
            return {
                'success': False,
                'error':
                f'RapidAPI error: {data.get("errorId", "Unknown error")}'
            }
        # Format 2: status/code fields
        if 'status' in data and data.get('status') != 'success':
            error_msg = data.get('message', 'Unknown error')
            return {'success': False, 'error': f'RapidAPI error: {error_msg}'}

        # Extract audio download URL (handle both formats)
        audios = data.get('audios', {})

        # If audios is a dict with errorId/items (Format 1)
        if isinstance(audios, dict):
            if 'errorId' in audios and audios.get('errorId') != 'Success':
                return {
                    'success':
                    False,
                    'error':
                    f'Audio extraction error: {audios.get("errorId", "No audio available")}'
                }
            audio_items = audios.get('items', [])
        # If audios is already an array (Format 2)
        elif isinstance(audios, list):
            audio_items = audios
        else:
            audio_items = []

        if not audio_items:
            return {
                'success': False,
                'error': 'No audio tracks found for this video'
            }

        # Get the best quality audio (first item is usually highest quality)
        audio_url = audio_items[0]['url']
        audio_extension = audio_items[0].get('extension', 'm4a')
        print(
            f"✓ Found audio URL (format: {audio_extension}, size: {audio_items[0].get('sizeText', 'unknown')})"
        )

        # Step 4: Download the audio file
        print(f"⬇️  Downloading audio file...")
        temp_file = f"{temp_download_path}.{audio_extension}"

        audio_response = requests.get(audio_url, stream=True, timeout=120)
        if audio_response.status_code != 200:
            return {
                'success':
                False,
                'error':
                f'Failed to download audio file: HTTP {audio_response.status_code}'
            }

        with open(temp_file, 'wb') as f:
            for chunk in audio_response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✓ Audio downloaded: {temp_file}")

        # Step 5: Convert directly to 16kHz mono WAV (single step optimization)
        print(
            f"🔄 Converting {audio_extension} to 16kHz mono WAV for transcription..."
        )

        # Copy to raw_audio for reference (without conversion to save time)
        import shutil
        shutil.copy2(temp_file,
                     raw_audio_path.replace('.wav', f'.{audio_extension}'))
        raw_audio_path = raw_audio_path.replace('.wav', f'.{audio_extension}')

        # Convert directly from downloaded file to 16kHz mono WAV (optimized single-step)
        ffmpeg_cmd = [
            'ffmpeg',
            '-i',
            temp_file,
            '-ar',
            '16000',  # 16 kHz sample rate (required for AssemblyAI)
            '-ac',
            '1',  # mono (1 channel)
            '-acodec',
            'pcm_s16le',  # PCM 16-bit encoding
            '-y',  # overwrite output file if exists
            prepared_audio_path
        ]

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {
                'success': False,
                'error': f'FFmpeg conversion failed: {result.stderr}'
            }

        if not os.path.exists(prepared_audio_path):
            return {
                'success': False,
                'error': 'Prepared audio file was not created'
            }

        # Clean up temporary download file
        if os.path.exists(temp_file):
            os.remove(temp_file)

        print(f"✓ Audio prepared: {prepared_audio_path}")

        # Get file sizes for logging
        raw_size = os.path.getsize(raw_audio_path) / (1024 * 1024)  # MB
        prepared_size = os.path.getsize(prepared_audio_path) / (1024 * 1024
                                                                )  # MB

        return {
            'success': True,
            'raw_audio': raw_audio_path,
            'prepared_audio': prepared_audio_path,
            'raw_size_mb': round(raw_size, 2),
            'prepared_size_mb': round(prepared_size, 2),
            'error': None
        }

    except Exception as e:
        return {'success': False, 'error': f'Audio download error: {str(e)}'}


def extract_video_id(youtube_url):
    """
    Extract video ID from various YouTube URL formats
    
    Supported formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/live/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - And any other format with an 11-character alphanumeric ID
    
    Args:
        youtube_url: YouTube video URL
        
    Returns:
        str: Video ID or None if not found
    """
    # Try parsing query parameters (watch?v=...)
    parsed = urlparse(youtube_url)
    if parsed.query:
        query_params = parse_qs(parsed.query)
        if 'v' in query_params:
            return query_params['v'][0]

    # Comprehensive regex pattern that matches ALL YouTube URL formats
    # Looks for 11-character alphanumeric IDs after common YouTube paths
    pattern = r'(?:youtube\.com\/(?:watch\?v=|live\/|shorts\/|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})'

    match = re.search(pattern, youtube_url)
    if match:
        return match.group(1)

    return None
