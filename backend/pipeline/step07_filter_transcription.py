"""
Step 7: Filter Transcription - Keep only Anchor & Pradip Speakers

This step filters the English transcript to keep only dialogue from:
- The TV Anchor (interviewer)
- Mr. Pradip Halder (stock expert)

Removes all other speakers from the transcription.

Input: 
  - analysis/detected_speakers.txt (from Step 6)
  - transcripts/transcript_english.txt (from Step 5)
Output: 
  - transcripts/filtered_transcription.txt
"""

import os
import re


def run(job_folder):
    """
    Filter transcript to keep only Anchor and Pradip lines.
    
    Args:
        job_folder: Path to job working directory
        
    Returns:
        dict with status, message, and output_files
    """
    print(f"\n{'='*60}")
    print("STEP 7: Filter Transcription (Anchor & Pradip Only)")
    print(f"{'='*60}\n")

    try:
        # Input/Output paths
        detected_speakers_file = os.path.join(job_folder, "analysis", "detected_speakers.txt")
        transcript_file = os.path.join(job_folder, "transcripts", "transcript_english.txt")
        output_file = os.path.join(job_folder, "transcripts", "filtered_transcription.txt")
        
        # Verify input files exist
        if not os.path.exists(detected_speakers_file):
            return {
                'status': 'failed',
                'message': 'detected_speakers.txt not found. Run Step 6 first.',
                'output_files': []
            }
        
        if not os.path.exists(transcript_file):
            return {
                'status': 'failed',
                'message': 'transcript_english.txt not found. Run Step 5 first.',
                'output_files': []
            }
        
        # --- Step 1: Load detected speakers ---
        print(f"📄 Reading detected speakers: {detected_speakers_file}")
        with open(detected_speakers_file, "r", encoding="utf-8") as f:
            detected = f.read().strip().splitlines()
        
        anchor_speaker = None
        pradip_speaker = None
        
        for line in detected:
            if line.startswith("Anchor:"):
                anchor_speaker = line.split(":", 1)[1].strip()
            elif line.startswith("Pradip:"):
                pradip_speaker = line.split(":", 1)[1].strip()
        
        if not anchor_speaker or not pradip_speaker:
            return {
                'status': 'failed',
                'message': 'Could not parse Anchor and Pradip from detected_speakers.txt',
                'output_files': []
            }
        
        print(f"✅ Anchor detected as: {anchor_speaker}")
        print(f"✅ Pradip detected as: {pradip_speaker}")
        
        # --- Step 2: Load transcript ---
        print(f"\n📄 Reading transcript: {transcript_file}")
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript_lines = [line.strip() for line in f.readlines() if line.strip()]
        
        print(f"✓ Loaded {len(transcript_lines)} total lines")
        
        # --- Step 3: Keep only Anchor + Pradip lines ---
        print(f"\n🔍 Filtering lines for {anchor_speaker} and {pradip_speaker}...")
        filtered_lines = []
        
        for line in transcript_lines:
            if line.startswith(f"[{anchor_speaker}]") or line.startswith(f"[{pradip_speaker}]"):
                filtered_lines.append(line)
        
        print(f"✓ Kept {len(filtered_lines)} lines out of {len(transcript_lines)}")
        
        if len(filtered_lines) == 0:
            return {
                'status': 'failed',
                'message': f'No lines found for {anchor_speaker} or {pradip_speaker}',
                'output_files': []
            }
        
        # --- Step 4: Save filtered transcript ---
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(filtered_lines))
        
        print(f"\n✅ Saved filtered transcript: {output_file}")
        print(f"📊 Removed {len(transcript_lines) - len(filtered_lines)} lines from other speakers")
        
        # Preview first 3 lines
        print("\n--- Preview (first 3 filtered lines) ---")
        for line in filtered_lines[:3]:
            print(line)
        print()
        
        return {
            'status': 'success',
            'message': f'Filtered transcript: kept {len(filtered_lines)} lines from {anchor_speaker} and {pradip_speaker}, removed {len(transcript_lines) - len(filtered_lines)} other lines',
            'output_files': ['transcripts/filtered_transcription.txt']
        }
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'failed',
            'message': f'Error filtering transcription: {str(e)}',
            'output_files': []
        }
