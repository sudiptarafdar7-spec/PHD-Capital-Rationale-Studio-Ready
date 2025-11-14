"""
Step 2: Download Auto-Generated Captions from YouTube Video
Simple and robust implementation using yt-dlp with wildcard language matching
"""
import os
import subprocess
import json
import glob


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


def download_captions(job_id, youtube_url, cookies_file=None):
    """
    Download auto-generated captions from YouTube video using yt-dlp
    
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

        print(f"⏳ Downloading auto-generated captions (Any Language)...")

        # Use cookies from uploaded_files folder
        cookies_file_path = os.path.join("backend", "uploaded_files", "youtube_cookies.txt")

        # ROBUST yt-dlp command - prioritize Hindi, then English
        cmd = [
            "python3.11", "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs", "hi,hi-IN,en,en-US",  # Priority: Hindi first, then English
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
            text=True
        )

        if result.returncode != 0:
            print("yt-dlp stderr:", result.stderr)

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

            # Detect language from filename
            for lang_code in ["hi", "en", "ur", "bn", "mr", "ta", "te", "pa", "gu", "kn", "ml", "or"]:
                if f".{lang_code}" in src.lower():
                    language = lang_code
                    break

            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)

            with open(captions_json_path, "w", encoding="utf-8") as outj:
                json.dump(data, outj, ensure_ascii=False, indent=2)

            print(f"✅ Captions saved from JSON3 format ({language or 'unknown'})")

        # Fallback to VTT
        elif any(f.endswith(".vtt") for f in subs_found):
            src = [f for f in subs_found if f.endswith(".vtt")][0]
            source_format = 'vtt'

            for lang_code in ["hi", "en", "ur", "bn", "mr", "ta", "te"]:
                if f".{lang_code}" in src.lower():
                    language = lang_code
                    break

            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                vtt_text = f.read()

            data = parse_vtt(vtt_text)

            with open(captions_json_path, "w", encoding="utf-8") as outj:
                json.dump(data, outj, ensure_ascii=False, indent=2)

            print(f"✅ Captions saved from VTT format ({language or 'unknown'})")

        # Fallback to SRT
        else:
            src = [f for f in subs_found if f.endswith(".srt")][0]
            source_format = 'srt'

            for lang_code in ["hi", "en", "ur", "bn", "mr", "ta", "te"]:
                if f".{lang_code}" in src.lower():
                    language = lang_code
                    break

            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                srt_text = f.read()

            data = parse_vtt(srt_text)

            with open(captions_json_path, "w", encoding="utf-8") as outj:
                json.dump(data, outj, ensure_ascii=False, indent=2)

            print(f"✅ Captions saved from SRT format ({language or 'unknown'})")

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

    except Exception as e:
        return {
            'success': False,
            'error': f'Caption download error: {str(e)}'
        }
