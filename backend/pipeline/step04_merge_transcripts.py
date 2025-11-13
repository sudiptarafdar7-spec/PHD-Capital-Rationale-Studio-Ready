"""
Step 4: Merge AssemblyAI Transcription with YouTube Captions

This step combines:
- Speaker labels and timestamps from AssemblyAI (transcript.csv)
- Actual text content from YouTube auto-generated captions (captions.json)

Output: final_transcript.txt with format:
[Speaker X] HH:MM:SS - HH:MM:SS | merged text from YouTube
"""

import json
import pandas as pd
from bisect import bisect_right
import os


def time_to_seconds(t):
    """Convert HH:MM:SS or MM:SS to seconds"""
    parts = t.split(":")
    parts = [int(x) for x in parts]
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h = 0
        m, s = parts
    else:
        raise ValueError("Time must be MM:SS or HH:MM:SS")
    return h * 3600 + m * 60 + s


def run(job_folder):
    """
    Merge AssemblyAI transcript with YouTube captions.
    
    Args:
        job_folder: Path to job working directory
        
    Returns:
        dict with status, message, and output_files
    """
    print(f"\n{'='*60}")
    print("STEP 4: Merge Transcripts")
    print(f"{'='*60}\n")

    try:
        # --- Load AssemblyAI transcript ---
        assembly_file = os.path.join(job_folder, "transcripts/transcript.csv")
        if not os.path.exists(assembly_file):
            return {
                'status': 'failed',
                'message': 'transcript.csv not found',
                'output_files': []
            }

        print(f"📄 Loading AssemblyAI transcript: {assembly_file}")
        assembly_df = pd.read_csv(assembly_file)

        # Convert times to seconds
        assembly_df["start_s"] = assembly_df["Start Time"].apply(
            time_to_seconds)
        assembly_df["end_s"] = assembly_df["End Time"].apply(time_to_seconds)
        assembly_df = assembly_df.sort_values("start_s").reset_index(drop=True)

        # Extract speaker segments
        speakers = []
        for _, r in assembly_df.iterrows():
            speakers.append({
                "speaker": r["Speaker"],
                "start": r["start_s"],
                "end": r["end_s"],
                "start_str": r["Start Time"],
                "end_str": r["End Time"],
                "assembly_text": r.get("Transcription", "")
            })

        print(f"✓ Found {len(speakers)} speaker segments")

        # --- Parse YouTube captions into word-level timestamps ---
        youtube_words = []
        captions_file = os.path.join(job_folder, "captions/captions.json")

        if not os.path.exists(captions_file):
            return {
                'status': 'failed',
                'message': 'captions.json not found',
                'output_files': []
            }

        print(f"📄 Loading YouTube captions: {captions_file}")

        with open(captions_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Parse JSON3 format with word-level timestamps
        for ev in data.get("events", []):
            base = ev.get("tStartMs", 0) / 1000.0
            dur_ms = ev.get("dDurationMs", None)
            segs = ev.get("segs", [])

            for seg in segs:
                text = seg.get("utf8")
                if not text or text.strip() == "":
                    continue

                offset_ms = seg.get("tOffsetMs", 0)
                tokens = text.strip().split()

                if not tokens:
                    continue

                if len(tokens) == 1:
                    # Single word - use exact timestamp
                    t = base + offset_ms / 1000.0
                    youtube_words.append((t, tokens[0]))
                else:
                    # Multiple words - distribute evenly across duration
                    if dur_ms:
                        dur = dur_ms / 1000.0
                        for i, tk in enumerate(tokens):
                            t = base + (i * dur / max(1, len(tokens)))
                            youtube_words.append((t, tk))
                    else:
                        # No duration - space words 1ms apart
                        t_base = base + offset_ms / 1000.0
                        for i, tk in enumerate(tokens):
                            t = t_base + i * 0.001
                            youtube_words.append((t, tk))

        youtube_words.sort(key=lambda x: x[0])
        print(f"✓ Extracted {len(youtube_words)} words from YouTube captions")

        if not speakers:
            return {
                'status': 'failed',
                'message': 'No speaker segments found',
                'output_files': []
            }

        # --- Partition timeline between speakers using midpoints ---
        midpoints = []
        for i in range(len(speakers) - 1):
            mid = (speakers[i]["end"] + speakers[i + 1]["start"]) / 2.0
            midpoints.append(mid)

        # Assign YouTube words to speaker segments
        assigned = [[] for _ in speakers]
        for t, token in youtube_words:
            idx = bisect_right(midpoints, t)
            assigned[idx].append((t, token))

        print(f"✓ Assigned YouTube words to {len(speakers)} speaker segments")

        # --- Build final merged transcript ---
        final_lines = []
        for i, sp in enumerate(speakers):
            words = [tok for _, tok in assigned[i]]
            if words:
                merged_text = " ".join(words).strip()
            else:
                # Fallback to AssemblyAI text if no YouTube words found
                merged_text = sp["assembly_text"].strip()

            final_lines.append(
                f"[{sp['speaker']}] {sp['start_str']} - {sp['end_str']} | {merged_text}"
            )

        # --- Save final transcript ---
        output_file = os.path.join(job_folder, "transcripts", "final_transcript.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            for line in final_lines:
                f.write(line + "\n")

        print(f"\n✅ Final transcript saved: {output_file}")
        print(f"📊 Total segments: {len(final_lines)}")

        # Preview first 3 segments
        print("\n--- Preview (first 3 segments) ---")
        for line in final_lines[:3]:
            print(line)
        print()

        return {
            'status': 'success',
            'message':
            f'Merged {len(speakers)} speaker segments with YouTube captions',
            'output_files': ['final_transcript.txt']
        }

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'failed',
            'message': f'Error merging transcripts: {str(e)}',
            'output_files': []
        }
