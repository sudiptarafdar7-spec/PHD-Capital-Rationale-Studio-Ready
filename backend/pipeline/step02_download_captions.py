"""
Step 2: Download Auto-Generated Captions from YouTube Video
100% Reliable - Downloads ALL captions (auto + manual) using wildcard pattern
"""
import os
import subprocess
import json
import glob
import re


def download_captions(job_id, youtube_url, cookies_file=None):
    """
    100% Reliable Auto-Generated Caption Downloader
    Downloads ALL available captions (auto-generated + manual) and selects preferred language
    
    Strategy:
    1. Use --sub-langs "*" to download ALL captions (wildcard pattern)
    2. Use both --write-auto-subs and --write-subs to get all caption types
    3. Use --convert-subs json3 to force JSON3 format (most reliable)
    4. Select preferred language: Hindi > English > Others
    5. Improved regex and fallback handling for unexpected filenames
    
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

        print("⏳ Downloading ALL available captions (auto-generated + manual)...")

        # ROBUST yt-dlp command - download ALL captions
        cmd = [
            "python3.11", "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs",  # Download auto-generated captions
            "--write-subs",  # Download manual captions
            "--sub-langs", "all",  # Download ALL languages (supported yt-dlp selector)
            "--convert-subs", "json3",  # Force JSON3 format (stable & reliable)
            "-o", os.path.join(captions_folder, "youtube.%(lang)s.%(ext)s"),  # Include language in filename
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

        # Look for JSON3 caption files (flexible glob pattern)
        json3_files = glob.glob(os.path.join(captions_folder, "*.json3"))

        if not json3_files:
            return {
                'success': False,
                'error': 'No auto-generated captions found. Captions may be disabled for this video.'
            }

        print(f"✓ Found {len(json3_files)} caption file(s)")

        # Prefer Hindi > English > Others
        # Improved language matching with flexible patterns
        preferred_langs = [
            # Hindi variations
            ("hi", ["hi", "hi-IN", "hi-Latn"]),
            # English variations
            ("en", ["en", "en-US", "en-GB", "en-IN"])
        ]
        
        selected_file = None
        selected_lang = None

        # Try preferred languages first
        for lang_key, lang_patterns in preferred_langs:
            for pattern in lang_patterns:
                for caption_file in json3_files:
                    filename = os.path.basename(caption_file)
                    # Match language in filename with multiple patterns
                    # Patterns: youtube.hi.json3, youtube-hi.json3, hi.json3, etc.
                    if (f".{pattern}." in filename or 
                        f"-{pattern}." in filename or 
                        filename.startswith(f"{pattern}.")):
                        selected_file = caption_file
                        selected_lang = pattern
                        print(f"✓ Selected preferred language: {pattern}")
                        break
                if selected_file:
                    break
            if selected_file:
                break

        # If no preferred language found, use first available
        if not selected_file:
            selected_file = json3_files[0]
            print(f"✓ No preferred language found, using first available")
            
            # Try to extract language from filename with improved regex
            filename = os.path.basename(selected_file)
            
            # Try multiple regex patterns for language extraction
            patterns = [
                r"\.([a-zA-Z]{2,3}(?:-[a-zA-Z0-9]+)*)\.json3$",  # youtube.en-US.json3
                r"-([a-zA-Z]{2,3}(?:-[a-zA-Z0-9]+)*)\.json3$",   # youtube-en.json3
                r"^([a-zA-Z]{2,3}(?:-[a-zA-Z0-9]+)*)\.json3$",   # en.json3
            ]
            
            for pattern in patterns:
                lang_match = re.search(pattern, filename)
                if lang_match:
                    selected_lang = lang_match.group(1)
                    break
            
            # Fallback: if still no language detected, use 'unknown'
            if not selected_lang:
                selected_lang = "unknown"

        # Load JSON3 data
        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Invalid JSON3 format in caption file: {str(e)}'
            }

        # Save as captions.json
        with open(captions_json_path, "w", encoding="utf-8") as outj:
            json.dump(data, outj, ensure_ascii=False, indent=2)

        # Cleanup - remove intermediate files
        for caption_file in json3_files:
            try:
                if caption_file != captions_json_path:
                    os.remove(caption_file)
            except:
                pass

        file_size = os.path.getsize(captions_json_path) / 1024

        print(f"✅ Captions saved successfully (Language: {selected_lang})")

        return {
            'success': True,
            'captions_path': captions_json_path,
            'format': 'json3',
            'language': selected_lang,
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
