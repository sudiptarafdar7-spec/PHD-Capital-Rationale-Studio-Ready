"""
Step 2: Download Auto-Generated Captions from YouTube Video
100% Reliable - Downloads ANY auto-generated caption language YouTube provides
"""
import os
import subprocess
import json
import glob
import re


def time_to_ms(timestr):
    """Convert VTT timestamp to milliseconds"""
    parts = timestr.split(":")
    try:
        parts = [float(p) for p in parts]
    except:
        return 0
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h = 0
        m, s = parts
    else:
        return int(parts[0] * 1000)
    return int((h * 3600 + m * 60 + s) * 1000)


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
                    'tStartMs': time_to_ms(cur_start),
                    'dDurationMs': time_to_ms(cur_end) - time_to_ms(cur_start),
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


def get_available_auto_subs(youtube_url, cookies_file_path=None):
    """
    List all available auto-generated subtitles for a YouTube video
    
    Returns:
        list: List of auto-generated language codes (e.g., ['en', 'hi', 'es'])
    """
    try:
        cmd = [
            "python3.11", "-m", "yt_dlp",
            "--list-subs",
            "--skip-download",
            youtube_url
        ]
        
        if cookies_file_path and os.path.exists(cookies_file_path):
            cmd.extend(["--cookies", cookies_file_path])
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return []
        
        # Parse output to find auto-generated subtitles
        auto_langs = []
        in_auto_section = False
        
        for line in result.stdout.splitlines():
            # Look for "automatic captions" section
            if "automatic" in line.lower():
                in_auto_section = True
                continue
            
            # Stop at manual subtitles section
            if "available subtitles" in line.lower() and in_auto_section:
                break
            
            # Extract language codes from auto-generated section
            if in_auto_section:
                # Match lines like: "en          vtt, ttml, srv3, srv2, srv1, json3"
                # OR: "zh-Hans     vtt, ttml, srv3", "es-419      vtt", "sr-Latn     vtt", etc.
                # Extract first token (language code) before whitespace
                stripped = line.strip()
                if stripped and not stripped.startswith('['):
                    # Split on whitespace and take first token as language code
                    parts = stripped.split()
                    if parts and len(parts) > 1:
                        # Verify it looks like a language code (contains letters/numbers/hyphens)
                        lang_candidate = parts[0]
                        if re.match(r'^[a-zA-Z]{2,3}(-[a-zA-Z0-9]+)*$', lang_candidate):
                            auto_langs.append(lang_candidate)
        
        return auto_langs
        
    except Exception as e:
        print(f"⚠️ Warning: Could not list subtitles: {str(e)}")
        return []


def download_captions(job_id, youtube_url, cookies_file=None):
    """
    Download auto-generated captions from YouTube video using yt-dlp
    100% RELIABLE - Downloads ANY auto-generated caption language
    
    Strategy:
    1. List available auto-generated subtitles
    2. Download the first available one (prefer en > hi > others)
    3. Fallback: Try without language restriction (YouTube's default)
    
    Args:
        job_id: Job identifier
        youtube_url: YouTube video URL
        cookies_file: Optional path to cookies.txt file (legacy param, uses uploaded_files folder)
    
    Returns:
        dict: {
            'success': bool,
            'captions_path': str,  # Path to captions.json file
            'format': str,  # Source format (json3, vtt, or srt)
            'language': str,  # Detected language code
            'file_size_kb': float,
            'error': str or None
        }
    """
    try:
        # Setup paths
        captions_folder = os.path.join('backend', 'job_files', job_id, 'captions')
        os.makedirs(captions_folder, exist_ok=True)

        captions_json_path = os.path.join(captions_folder, 'captions.json')

        # Use cookies from uploaded_files folder
        cookies_file_path = os.path.join("backend", "uploaded_files", "youtube_cookies.txt")

        print(f"⏳ Listing available auto-generated captions...")
        
        # Step 1: Get list of available auto-generated subtitles
        auto_langs = get_available_auto_subs(youtube_url, cookies_file_path)
        
        if auto_langs:
            # Prioritize English, then Hindi, then any other language
            priority_order = ['en', 'en-US', 'hi', 'hi-IN']
            selected_lang = None
            
            for lang in priority_order:
                if lang in auto_langs:
                    selected_lang = lang
                    break
            
            # If no priority language found, use the first available
            if not selected_lang:
                selected_lang = auto_langs[0]
            
            print(f"✓ Found {len(auto_langs)} auto-generated caption(s): {', '.join(auto_langs)}")
            print(f"⏳ Downloading auto-generated captions in '{selected_lang}'...")
            
            # Step 2: Download the selected language
            cmd = [
                "python3.11", "-m", "yt_dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-langs", selected_lang,
                "--sub-format", "json3/vtt/srt",
                "-o", os.path.join(captions_folder, "youtube.%(ext)s"),
                youtube_url
            ]
        else:
            # Step 3: Fallback - No language restriction (download YouTube's default)
            print(f"⚠️ Could not list subtitles, trying default auto-generated captions...")
            cmd = [
                "python3.11", "-m", "yt_dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-format", "json3/vtt/srt",
                "-o", os.path.join(captions_folder, "youtube.%(ext)s"),
                youtube_url
            ]

        # Add cookies if available
        if os.path.exists(cookies_file_path):
            cmd.extend(["--cookies", cookies_file_path])
            print(f"✓ Using cookies file for authentication")

        # Run yt-dlp
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print("⚠️ yt-dlp stderr:", result.stderr)

        # Find downloaded subtitle files
        subs_found = glob.glob(os.path.join(captions_folder, "youtube.*"))
        subs_found = [p for p in subs_found if p.lower().endswith(('.json3', '.vtt', '.srt'))]

        if not subs_found:
            return {
                'success': False,
                'error': 'No auto-generated captions found. Captions may be disabled for this video.'
            }

        source_format = None
        language = None

        # Prefer json3 (best format with timestamps)
        json3_files = [f for f in subs_found if f.endswith(".json3")]
        if json3_files:
            src = json3_files[0]
            source_format = 'json3'

            # Detect language from filename (e.g., youtube.en.json3, youtube.zh-Hans.json3, youtube.es-419.json3)
            filename = os.path.basename(src)
            # Flexible pattern: 2-3 letter code + optional hyphen-separated segments
            lang_match = re.search(r'youtube\.([a-zA-Z]{2,3}(?:-[a-zA-Z0-9]+)*)\.', filename)
            if lang_match:
                language = lang_match.group(1)

            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)

            with open(captions_json_path, "w", encoding="utf-8") as outj:
                json.dump(data, outj, ensure_ascii=False, indent=2)

            print(f"✅ Captions saved from JSON3 format (Language: {language or 'unknown'})")

        # Fallback to VTT
        elif any(f.endswith(".vtt") for f in subs_found):
            src = [f for f in subs_found if f.endswith(".vtt")][0]
            source_format = 'vtt'

            filename = os.path.basename(src)
            # Flexible pattern: 2-3 letter code + optional hyphen-separated segments
            lang_match = re.search(r'youtube\.([a-zA-Z]{2,3}(?:-[a-zA-Z0-9]+)*)\.', filename)
            if lang_match:
                language = lang_match.group(1)

            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                vtt_text = f.read()

            data = parse_vtt(vtt_text)

            with open(captions_json_path, "w", encoding="utf-8") as outj:
                json.dump(data, outj, ensure_ascii=False, indent=2)

            print(f"✅ Captions saved from VTT format (Language: {language or 'unknown'})")

        # Fallback to SRT
        else:
            src = [f for f in subs_found if f.endswith(".srt")][0]
            source_format = 'srt'

            filename = os.path.basename(src)
            # Flexible pattern: 2-3 letter code + optional hyphen-separated segments
            lang_match = re.search(r'youtube\.([a-zA-Z]{2,3}(?:-[a-zA-Z0-9]+)*)\.', filename)
            if lang_match:
                language = lang_match.group(1)

            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                srt_text = f.read()

            data = parse_vtt(srt_text)

            with open(captions_json_path, "w", encoding="utf-8") as outj:
                json.dump(data, outj, ensure_ascii=False, indent=2)

            print(f"✅ Captions saved from SRT format (Language: {language or 'unknown'})")

        # Cleanup intermediate files
        for sub_file in subs_found:
            try:
                os.remove(sub_file)
            except:
                pass

        if not os.path.exists(captions_json_path):
            return {
                'success': False,
                'error': 'Failed to create captions.json file'
            }

        file_size = os.path.getsize(captions_json_path) / 1024

        return {
            'success': True,
            'captions_path': captions_json_path,
            'format': source_format,
            'language': language or 'unknown',
            'file_size_kb': round(file_size, 2),
            'error': None
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Caption download timed out. Please try again.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Caption download error: {str(e)}'
        }
