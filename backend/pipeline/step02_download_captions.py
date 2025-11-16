"""
Step 2: Download Auto-Generated Captions from YouTube Video
100% Reliable - Downloads ALL auto-generated captions at once using --sub-langs ".*"
No dependency on --list-subs (which can randomly fail)
"""
import os
import subprocess
import json
import glob
import re


def download_captions(job_id, youtube_url, cookies_file=None):
    """
    100% Reliable Auto-Generated Caption Downloader
    Downloads ALL available auto-generated captions and selects preferred language
    
    Strategy:
    1. Use --sub-langs ".*" to download ALL auto-generated captions at once
    2. Use --convert-subs json3 to force JSON3 format (most reliable)
    3. Select preferred language: Hindi > English > Others
    4. No dependency on --list-subs (which can randomly fail)
    
    Args:
        job_id: Job identifier
        youtube_url: YouTube video URL
        cookies_file: Optional path to cookies.txt file (legacy param, uses uploaded_files folder)
    
    Returns:
        dict: {
            'success': bool,
            'captions_path': str,  # Path to captions.json file
            'format': str,  # Always 'json3'
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
        cookies_file_path = os.path.join("backend", "uploaded_files", "youtube_cookies.txt")

        print("⏳ Downloading ALL available auto-generated captions...")

        # ROBUST yt-dlp command - download ALL auto-generated captions
        cmd = [
            "python3.11", "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs", "all",  # Download ALL languages (Hindi, English, Spanish, etc.)
            "--convert-subs", "json3",  # Force JSON3 format (stable & reliable)
            "-o", os.path.join(captions_folder, "youtube.%(lang)s.%(ext)s"),
            youtube_url
        ]

        # Add cookies if available
        if os.path.exists(cookies_file_path):
            cmd.extend(["--cookies", cookies_file_path])
            print(f"✓ Using cookies file for authentication")

        # Run yt-dlp with 90s timeout
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            print("⚠️ yt-dlp stderr:", result.stderr)

        # Look for JSON3 auto subtitles
        json3_files = glob.glob(os.path.join(captions_folder, "*.json3"))

        if not json3_files:
            return {
                'success': False,
                'error': 'No auto-generated captions found. Captions may be disabled for this video.'
            }

        print(f"✓ Found {len(json3_files)} auto-generated caption file(s)")

        # Prefer Hindi > English > Others
        preferred_langs = ["hi", "hi-IN", "en", "en-US"]
        selected_file = None

        for lang_code in preferred_langs:
            for caption_file in json3_files:
                # Match language in filename (e.g., youtube.hi.json3, youtube.en.json3)
                if f".{lang_code}." in caption_file:
                    selected_file = caption_file
                    print(f"✓ Selected preferred language: {lang_code}")
                    break
            if selected_file:
                break

        # If no preferred language found, use first available
        if not selected_file:
            selected_file = json3_files[0]
            print(f"✓ No preferred language found, using first available")

        # Extract language from filename
        lang_match = re.search(r"\.(.+?)\.json3$", os.path.basename(selected_file))
        detected_language = lang_match.group(1) if lang_match else "unknown"

        # Load JSON3 data
        with open(selected_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Save as captions.json
        with open(captions_json_path, "w", encoding="utf-8") as outj:
            json.dump(data, outj, ensure_ascii=False, indent=2)

        # Cleanup - remove intermediate files
        for caption_file in json3_files:
            try:
                os.remove(caption_file)
            except:
                pass

        file_size = os.path.getsize(captions_json_path) / 1024

        print(f"✅ Captions saved successfully (Language: {detected_language})")

        return {
            'success': True,
            'captions_path': captions_json_path,
            'format': 'json3',
            'language': detected_language,
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
