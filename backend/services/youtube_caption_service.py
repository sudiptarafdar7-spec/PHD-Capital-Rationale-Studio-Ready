"""
YouTube Caption Service - Standalone caption fetching with RapidAPI + yt-dlp fallback
Downloads captions with timestamps and returns formatted text
"""
import os
import re
import json
import uuid
import requests
import subprocess
import threading
import time
from datetime import datetime, timedelta
from backend.utils.database import get_db_cursor

TEMP_CAPTIONS_FOLDER = os.path.join('backend', 'temp_captions')
COOKIES_FILE_PATH = os.path.join('backend', 'uploaded_files', 'youtube_cookies.txt')
CLEANUP_HOURS = 24

os.makedirs(TEMP_CAPTIONS_FOLDER, exist_ok=True)


def normalize_youtube_url(url: str) -> tuple:
    """
    Converts any YouTube URL to standard format and extracts video ID.
    
    Returns:
        tuple: (normalized_url, video_id)
    """
    patterns = [
        r"youtube\.com/live/([a-zA-Z0-9_-]{6,})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{6,})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{6,})",
        r"youtu\.be/([a-zA-Z0-9_-]{6,})",
        r"[?&]v=([a-zA-Z0-9_-]{6,})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}", video_id

    return url, None


def get_rapidapi_key():
    """Get RapidAPI Video Transcript key from database"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT key_value FROM api_keys WHERE provider = %s", ('rapidapi_video_transcript',))
            result = cursor.fetchone()
            if result:
                return result['key_value']
    except Exception as e:
        print(f"Error fetching RapidAPI key: {e}")
    return None


def format_timestamp(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS format"""
    seconds = ms // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def fetch_available_languages_rapidapi(video_url: str, rapidapi_key: str) -> dict:
    """
    Fetch available caption languages using RapidAPI
    
    Returns:
        dict: {
            'success': bool,
            'languages': [{'code': 'en', 'name': 'English'}, ...],
            'error': str or None
        }
    """
    try:
        url = "https://video-transcript-scraper.p.rapidapi.com/transcript"
        
        payload = {"video_url": video_url}
        headers = {
            "x-rapidapi-key": rapidapi_key,
            "x-rapidapi-host": "video-transcript-scraper.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code != 200:
            return {
                'success': False,
                'languages': [],
                'error': f"API request failed (Status {response.status_code})"
            }
        
        data = response.json()
        
        if data.get("status") != "success":
            return {
                'success': False,
                'languages': [],
                'error': data.get('message', 'Unknown error')
            }
        
        video_info = data.get("data", {}).get("video_info", {})
        available_langs = video_info.get("available_languages", [])
        selected_lang = video_info.get("selected_language", "auto")
        
        languages = []
        if available_langs:
            for lang in available_langs:
                if isinstance(lang, dict):
                    languages.append({
                        'code': lang.get('code', 'unknown'),
                        'name': lang.get('name', lang.get('code', 'Unknown'))
                    })
                elif isinstance(lang, str):
                    lang_names = {
                        'hi': 'Hindi', 'en': 'English', 'ta': 'Tamil', 'te': 'Telugu',
                        'mr': 'Marathi', 'gu': 'Gujarati', 'kn': 'Kannada', 'ml': 'Malayalam',
                        'pa': 'Punjabi', 'bn': 'Bengali', 'ur': 'Urdu', 'or': 'Odia',
                        'as': 'Assamese', 'ne': 'Nepali', 'si': 'Sinhala',
                        'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese', 'ar': 'Arabic',
                        'fr': 'French', 'de': 'German', 'es': 'Spanish', 'pt': 'Portuguese',
                        'ru': 'Russian', 'it': 'Italian', 'nl': 'Dutch', 'pl': 'Polish',
                        'tr': 'Turkish', 'th': 'Thai', 'vi': 'Vietnamese', 'id': 'Indonesian'
                    }
                    languages.append({
                        'code': lang,
                        'name': lang_names.get(lang.split('-')[0], lang.upper())
                    })
        
        if not languages and selected_lang:
            languages.append({
                'code': selected_lang,
                'name': 'Auto-detected'
            })
        
        return {
            'success': True,
            'languages': languages,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'languages': [],
            'error': str(e)
        }


def fetch_available_languages_ytdlp(video_url: str) -> dict:
    """
    Fetch available caption languages using yt-dlp
    
    Returns:
        dict: {
            'success': bool,
            'languages': [{'code': 'en', 'name': 'English'}, ...],
            'error': str or None
        }
    """
    try:
        cmd = [
            'yt-dlp',
            '--list-subs',
            '--skip-download',
            video_url
        ]
        
        if os.path.exists(COOKIES_FILE_PATH):
            cmd.extend(['--cookies', COOKIES_FILE_PATH])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        
        languages = []
        
        auto_caption_match = re.findall(r'\[info\] Available automatic captions.*?Language.*?\n(.*?)(?=\n\[|\Z)', output, re.DOTALL)
        manual_caption_match = re.findall(r'\[info\] Available subtitles.*?Language.*?\n(.*?)(?=\n\[|\Z)', output, re.DOTALL)
        
        lang_pattern = re.compile(r'^([a-z]{2,3}(?:-[A-Za-z0-9]+)?)\s+(.+?)(?:\s+vtt|\s+srv|\s+ttml|\s*$)', re.MULTILINE)
        
        for section in auto_caption_match + manual_caption_match:
            for match in lang_pattern.finditer(section):
                code = match.group(1)
                name = match.group(2).strip()
                if code and not any(l['code'] == code for l in languages):
                    languages.append({'code': code, 'name': name or code})
        
        if not languages:
            languages.append({'code': 'en', 'name': 'English (default)'})
        
        return {
            'success': True,
            'languages': languages,
            'error': None
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'languages': [],
            'error': 'yt-dlp timed out'
        }
    except Exception as e:
        return {
            'success': False,
            'languages': [],
            'error': str(e)
        }


def fetch_captions_rapidapi(video_url: str, rapidapi_key: str, language: str = None) -> dict:
    """
    Fetch captions using RapidAPI Video Transcript Scraper
    
    Returns:
        dict: {
            'success': bool,
            'captions': [{'timestamp': '00:00:05', 'text': '...'}, ...],
            'raw_text': str,
            'language': str,
            'error': str or None
        }
    """
    try:
        url = "https://video-transcript-scraper.p.rapidapi.com/transcript"
        
        payload = {"video_url": video_url}
        if language:
            payload["language"] = language
            
        headers = {
            "x-rapidapi-key": rapidapi_key,
            "x-rapidapi-host": "video-transcript-scraper.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        
        print(f"📡 Fetching captions via RapidAPI (language: {language or 'auto'})...")
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f"API request failed (Status {response.status_code}): {response.text}"
            }
        
        data = response.json()
        
        if data.get("status") != "success":
            return {
                'success': False,
                'error': data.get('message', 'Unknown error')
            }
        
        transcript = data.get("data", {}).get("transcript", [])
        if not transcript:
            return {
                'success': False,
                'error': 'No captions available for this video'
            }
        
        captions = []
        raw_lines = []
        
        for entry in transcript:
            text = entry.get("text", "").strip()
            start_ms = int(float(entry.get("start", 0)) * 1000)
            timestamp = format_timestamp(start_ms)
            
            if text:
                captions.append({
                    'timestamp': timestamp,
                    'start_ms': start_ms,
                    'text': text
                })
                raw_lines.append(f"[{timestamp}] {text}")
        
        video_info = data.get("data", {}).get("video_info", {})
        detected_lang = video_info.get("selected_language", language or "auto")
        
        print(f"✅ RapidAPI returned {len(captions)} caption segments")
        
        return {
            'success': True,
            'captions': captions,
            'raw_text': '\n'.join(raw_lines),
            'language': detected_lang,
            'error': None
        }
        
    except requests.Timeout:
        return {
            'success': False,
            'error': 'RapidAPI request timed out'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'RapidAPI error: {str(e)}'
        }


def fetch_captions_ytdlp(video_url: str, language: str = 'en') -> dict:
    """
    Fetch captions using yt-dlp as fallback
    
    Returns:
        dict: {
            'success': bool,
            'captions': [{'timestamp': '00:00:05', 'text': '...'}, ...],
            'raw_text': str,
            'language': str,
            'error': str or None
        }
    """
    try:
        temp_id = uuid.uuid4().hex[:8]
        temp_folder = os.path.join(TEMP_CAPTIONS_FOLDER, f"ytdlp_{temp_id}")
        os.makedirs(temp_folder, exist_ok=True)
        
        output_template = os.path.join(temp_folder, 'captions')
        
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-auto-sub',
            '--write-sub',
            '--sub-lang', language,
            '--sub-format', 'vtt',
            '--convert-subs', 'vtt',
            '-o', output_template,
            video_url
        ]
        
        if os.path.exists(COOKIES_FILE_PATH):
            cmd.extend(['--cookies', COOKIES_FILE_PATH])
            print(f"✅ Using cookies from: {COOKIES_FILE_PATH}")
        
        print(f"📡 Fetching captions via yt-dlp (language: {language})...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        vtt_files = [f for f in os.listdir(temp_folder) if f.endswith('.vtt')]
        
        if not vtt_files:
            import shutil
            shutil.rmtree(temp_folder, ignore_errors=True)
            return {
                'success': False,
                'error': 'No captions found for this video/language'
            }
        
        vtt_path = os.path.join(temp_folder, vtt_files[0])
        
        captions = []
        raw_lines = []
        
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        vtt_pattern = re.compile(
            r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})\s*\n((?:(?!\d{2}:\d{2}:\d{2}\.\d{3}).+\n?)+)',
            re.MULTILINE
        )
        
        for match in vtt_pattern.finditer(content):
            start_time = match.group(1)
            text = match.group(3).strip()
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\n+', ' ', text).strip()
            
            if text:
                parts = start_time.split(':')
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                start_ms = int((hours * 3600 + minutes * 60 + seconds) * 1000)
                
                timestamp = format_timestamp(start_ms)
                
                captions.append({
                    'timestamp': timestamp,
                    'start_ms': start_ms,
                    'text': text
                })
                raw_lines.append(f"[{timestamp}] {text}")
        
        import shutil
        shutil.rmtree(temp_folder, ignore_errors=True)
        
        if not captions:
            return {
                'success': False,
                'error': 'Could not parse captions from VTT file'
            }
        
        print(f"✅ yt-dlp returned {len(captions)} caption segments")
        
        return {
            'success': True,
            'captions': captions,
            'raw_text': '\n'.join(raw_lines),
            'language': language,
            'error': None
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'yt-dlp timed out'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'yt-dlp error: {str(e)}'
        }


class YoutubeCaptionService:
    def __init__(self):
        self.rapidapi_key = get_rapidapi_key()
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread to clean up old caption files"""
        def cleanup_old_files():
            while True:
                try:
                    if os.path.exists(TEMP_CAPTIONS_FOLDER):
                        cutoff = datetime.now() - timedelta(hours=CLEANUP_HOURS)
                        for filename in os.listdir(TEMP_CAPTIONS_FOLDER):
                            filepath = os.path.join(TEMP_CAPTIONS_FOLDER, filename)
                            if os.path.isfile(filepath):
                                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                                if file_mtime < cutoff:
                                    os.remove(filepath)
                                    print(f"🗑️ Cleaned up old caption file: {filename}")
                except Exception as e:
                    print(f"Cleanup error: {e}")
                time.sleep(3600)
        
        cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
        cleanup_thread.start()
    
    def get_available_languages(self, youtube_url: str) -> dict:
        """
        Get available caption languages for a YouTube video
        
        Returns:
            dict: {
                'success': bool,
                'languages': [{'code': 'en', 'name': 'English'}, ...],
                'video_id': str,
                'error': str or None
            }
        """
        normalized_url, video_id = normalize_youtube_url(youtube_url)
        
        if not video_id:
            return {
                'success': False,
                'languages': [],
                'video_id': None,
                'error': 'Invalid YouTube URL'
            }
        
        if self.rapidapi_key:
            result = fetch_available_languages_rapidapi(normalized_url, self.rapidapi_key)
            if result['success']:
                result['video_id'] = video_id
                return result
            print(f"⚠️ RapidAPI language fetch failed: {result['error']}")
        
        print("🔄 Falling back to yt-dlp for language detection...")
        result = fetch_available_languages_ytdlp(normalized_url)
        result['video_id'] = video_id
        return result
    
    def fetch_captions(self, youtube_url: str, language: str = None) -> dict:
        """
        Fetch captions for a YouTube video
        
        Returns:
            dict: {
                'success': bool,
                'caption_id': str,
                'captions': [{'timestamp': '00:00:05', 'text': '...'}, ...],
                'raw_text': str,
                'language': str,
                'download_url': str,
                'error': str or None
            }
        """
        normalized_url, video_id = normalize_youtube_url(youtube_url)
        
        if not video_id:
            return {
                'success': False,
                'error': 'Invalid YouTube URL'
            }
        
        caption_id = f"{video_id}_{uuid.uuid4().hex[:8]}"
        result = None
        
        if self.rapidapi_key:
            result = fetch_captions_rapidapi(normalized_url, self.rapidapi_key, language)
            if result['success']:
                txt_path = os.path.join(TEMP_CAPTIONS_FOLDER, f"{caption_id}.txt")
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"YouTube Caption - Video ID: {video_id}\n")
                    f.write(f"Language: {result['language']}\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(result['raw_text'])
                
                result['caption_id'] = caption_id
                result['download_url'] = f"/api/v1/youtube-caption/download/{caption_id}"
                return result
            print(f"⚠️ RapidAPI caption fetch failed: {result['error']}")
        
        print("🔄 Falling back to yt-dlp...")
        result = fetch_captions_ytdlp(normalized_url, language or 'en')
        
        if result['success']:
            txt_path = os.path.join(TEMP_CAPTIONS_FOLDER, f"{caption_id}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"YouTube Caption - Video ID: {video_id}\n")
                f.write(f"Language: {result['language']}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(result['raw_text'])
            
            result['caption_id'] = caption_id
            result['download_url'] = f"/api/v1/youtube-caption/download/{caption_id}"
            return result
        
        return result
    
    def get_caption_file(self, caption_id: str) -> str:
        """Get path to caption file"""
        txt_path = os.path.join(TEMP_CAPTIONS_FOLDER, f"{caption_id}.txt")
        if os.path.exists(txt_path):
            return txt_path
        return None
    
    def delete_caption_file(self, caption_id: str) -> bool:
        """Delete caption file after download"""
        txt_path = os.path.join(TEMP_CAPTIONS_FOLDER, f"{caption_id}.txt")
        if os.path.exists(txt_path):
            os.remove(txt_path)
            return True
        return False


caption_service = YoutubeCaptionService()
