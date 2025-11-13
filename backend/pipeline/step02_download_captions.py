"""
Step 2: Download Auto-Generated Captions from YouTube Video
Uses yt-dlp to download Hindi/English captions in JSON format
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


def download_captions(job_id, youtube_url, cookies_file=None):
    """
    Download auto-generated captions from YouTube video
    
    Args:
        job_id: Job identifier
        youtube_url: YouTube video URL
        cookies_file: Optional path to cookies.txt file for authentication
    
    Returns:
        dict: {
            'success': bool,
            'captions_path': str,  # Path to captions.json file
            'format': str,  # Source format (json3, vtt, or srt)
            'language': str,  # Language code (hi or en)
            'error': str or None
        }
    """
    try:
        # Setup paths
        captions_folder = os.path.join('backend', 'job_files', job_id, 'captions')
        os.makedirs(captions_folder, exist_ok=True)
        
        captions_json_path = os.path.join(captions_folder, 'captions.json')
        
        print(f"⏳ Downloading auto-generated captions (Hindi/English)...")
        
        # Build yt-dlp command (use Python module to avoid version conflicts)
        cmd = [
            "python3.11", "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-lang", "hi,en",  # Try Hindi first, then English
            "--sub-format", "json3/vtt/srt",
            "-o", os.path.join(captions_folder, "youtube.%(ext)s"),
            youtube_url
        ]
        
        # Add cookies if available
        if cookies_file and os.path.exists(cookies_file):
            cmd.extend(["--cookies", cookies_file])
            print(f"✓ Using cookies file for authentication")
        
        # Run yt-dlp command
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            print(f"yt-dlp stderr: {result.stderr}")
        
        # Find downloaded subtitle files
        subs_found = glob.glob(os.path.join(captions_folder, "youtube.*"))
        subs_found = [p for p in subs_found if p.lower().endswith(('.json3', '.vtt', '.srt'))]
        
        if not subs_found:
            return {
                'success': False,
                'error': 'No auto-generated captions found. Captions may be disabled for this video.'
            }
        
        # Process subtitles based on format
        source_format = None
        language = None
        
        # Prefer JSON3 format
        json3_files = [f for f in subs_found if f.endswith(".json3")]
        if json3_files:
            src = json3_files[0]
            source_format = 'json3'
            
            # Extract language from filename (e.g., youtube.hi.json3)
            if '.hi.' in src:
                language = 'hi'
            elif '.en.' in src:
                language = 'en'
            
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            with open(captions_json_path, "w", encoding="utf-8") as outj:
                json.dump(data, outj, ensure_ascii=False, indent=2)
            
            print(f"✅ Captions saved from JSON3 format ({language})")
        
        # Fall back to VTT format
        elif any(f.endswith(".vtt") for f in subs_found):
            src = [f for f in subs_found if f.endswith(".vtt")][0]
            source_format = 'vtt'
            
            # Extract language from filename
            if '.hi.' in src:
                language = 'hi'
            elif '.en.' in src:
                language = 'en'
            
            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                vtt_text = f.read()
            
            data = parse_vtt(vtt_text)
            
            with open(captions_json_path, "w", encoding="utf-8") as outj:
                json.dump(data, outj, ensure_ascii=False, indent=2)
            
            print(f"✅ Captions saved from VTT format ({language})")
        
        else:
            # Only SRT found - parse it similarly to VTT
            src = [f for f in subs_found if f.endswith(".srt")][0]
            source_format = 'srt'
            
            if '.hi.' in src:
                language = 'hi'
            elif '.en.' in src:
                language = 'en'
            
            # SRT parsing (simplified - similar to VTT)
            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                srt_text = f.read()
            
            # Parse SRT (basic implementation)
            data = parse_vtt(srt_text)  # VTT parser works for SRT too
            
            with open(captions_json_path, "w", encoding="utf-8") as outj:
                json.dump(data, outj, ensure_ascii=False, indent=2)
            
            print(f"✅ Captions saved from SRT format ({language})")
        
        # Clean up intermediate files (keep only captions.json)
        for sub_file in subs_found:
            try:
                os.remove(sub_file)
            except:
                pass
        
        # Verify captions file exists
        if not os.path.exists(captions_json_path):
            return {
                'success': False,
                'error': 'Failed to create captions.json file'
            }
        
        # Get file size
        file_size = os.path.getsize(captions_json_path) / 1024  # KB
        
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
