"""
Step 2: Download Auto-Generated Captions from YouTube Video
Production-ready implementation with YouTube Transcript API (primary) and yt-dlp fallback
"""
import os
import json
import subprocess
import glob
import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


def time_to_ms(seconds):
    """Convert seconds (float) to milliseconds (int)."""
    try:
        return int(float(seconds) * 1000)
    except:
        return 0


def transcript_to_json_format(transcript):
    """Convert transcript list to your JSON3-like structure."""
    events = []
    for t in transcript:
        events.append({
            "tStartMs": time_to_ms(t.get("start", 0)),
            "dDurationMs": time_to_ms(t.get("duration", 0)),
            "segs": [{"utf8": t.get("text", "").strip()}]
        })
    return {"events": events}


def parse_vtt(vtt_text):
    """Parse VTT subtitle format to JSON structure"""
    events = []
    lines = vtt_text.splitlines()
    cur_start, cur_end, cur_text_lines = None, None, []
    
    for line in lines:
        line = line.strip()
        if not line:
            if cur_start and cur_text_lines:
                text = " ".join(cur_text_lines).strip()
                events.append({
                    'tStartMs': time_to_ms_str(cur_start),
                    'dDurationMs': time_to_ms_str(cur_end) - time_to_ms_str(cur_start),
                    'segs': [{'utf8': text}]
                })
            cur_start, cur_end, cur_text_lines = None, None, []
            continue
        if "-->" in line:
            parts = line.split("-->")
            cur_start = parts[0].strip()
            cur_end = parts[1].strip()
        else:
            cur_text_lines.append(line)
    
    return {'events': events}


def time_to_ms_str(timestr):
    """Convert VTT timestamp to milliseconds"""
    parts = timestr.split(":")
    try:
        parts = [float(p.replace(",", ".")) for p in parts]
    except:
        return 0
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = 0, parts[0], parts[1]
    else:
        return int(parts[0] * 1000)
    return int((h * 3600 + m * 60 + s) * 1000)


def download_captions(job_id, youtube_url, cookies_file=None):
    """
    Download auto-generated captions using YouTube Transcript API (preferred)
    and fall back to yt-dlp if needed.
    
    Args:
        job_id: Job identifier
        youtube_url: YouTube video URL
        cookies_file: Optional path to cookies.txt file (legacy param, uses uploaded_files folder)
    
    Returns:
        dict: {
            'success': bool,
            'captions_path': str,  # Path to captions.json file
            'format': str,  # Source format (transcript-api, json3, vtt, or srt)
            'language': str,  # Language code
            'file_size_kb': float,
            'error': str or None
        }
    """
    captions_folder = os.path.join('backend', 'job_files', job_id, 'captions')
    os.makedirs(captions_folder, exist_ok=True)
    captions_json_path = os.path.join(captions_folder, 'captions.json')

    # Extract video ID from URL
    video_id_match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", youtube_url)
    if not video_id_match:
        return {'success': False, 'error': 'Invalid YouTube URL'}

    video_id = video_id_match.group(1)

    print(f"🎬 Processing YouTube video: {video_id}")

    # Try YouTube Transcript API first (most reliable for auto-generated captions)
    try:
        print("🔍 Attempting to fetch captions via YouTube Transcript API...")
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, 
            languages=['hi', 'hi-IN', 'en', 'en-US']
        )
        print(f"✅ Captions fetched via YouTube Transcript API ({len(transcript)} segments)")

        data = transcript_to_json_format(transcript)
        with open(captions_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Detect language from first segment if available
        detected_lang = 'unknown'
        if transcript:
            first_text = transcript[0].get('text', '').strip()
            # Simple heuristic: check for Devanagari characters for Hindi
            if any('\u0900' <= char <= '\u097F' for char in first_text):
                detected_lang = 'hi'
            else:
                detected_lang = 'en'

        return {
            'success': True,
            'captions_path': captions_json_path,
            'format': 'transcript-api',
            'language': detected_lang,
            'file_size_kb': round(os.path.getsize(captions_json_path) / 1024, 2),
            'error': None
        }

    except (TranscriptsDisabled, NoTranscriptFound) as e:
        print(f"⚠️ Transcript API failed: {e}. Falling back to yt-dlp...")

    except Exception as e:
        print(f"⚠️ Transcript API unexpected error: {e}. Falling back to yt-dlp...")

    # Fallback: use yt-dlp for auto-generated captions
    try:
        print("⏳ Downloading auto-generated captions with yt-dlp...")

        # Use cookies from uploaded_files folder
        cookies_file_path = os.path.join("backend", "uploaded_files", "youtube_cookies.txt")
        
        cmd = [
            "python3.11", "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs", "hi,hi-IN,en,en-US",
            "--sub-format", "json3/vtt/srt",
            "-o", os.path.join(captions_folder, "youtube.%(ext)s"),
            youtube_url
        ]

        if os.path.exists(cookies_file_path):
            cmd.extend(["--cookies", cookies_file_path])
            print(f"✓ Using cookies file for authentication")

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"yt-dlp stderr: {result.stderr}")

        # Find downloaded subtitle files
        subs_found = glob.glob(os.path.join(captions_folder, "**"), recursive=True)
        subs_found = [p for p in subs_found if re.search(r'\.(json3|vtt|srt)$', p, re.IGNORECASE)]

        if not subs_found:
            return {'success': False, 'error': 'No auto-generated captions found via yt-dlp.'}

        src = subs_found[0]
        ext = os.path.splitext(src)[1].lower()
        language = 'hi' if 'hi' in src.lower() else 'en' if 'en' in src.lower() else 'unknown'

        if ext == '.json3':
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            data = parse_vtt(text)

        with open(captions_json_path, "w", encoding="utf-8") as outj:
            json.dump(data, outj, ensure_ascii=False, indent=2)

        # Cleanup intermediate files
        for f in subs_found:
            try:
                os.remove(f)
            except:
                pass

        print(f"✅ Captions saved via yt-dlp fallback ({language})")

        return {
            'success': True,
            'captions_path': captions_json_path,
            'format': ext.replace('.', ''),
            'language': language,
            'file_size_kb': round(os.path.getsize(captions_json_path) / 1024, 2),
            'error': None
        }

    except Exception as e:
        return {'success': False, 'error': f'yt-dlp fallback error: {e}'}
