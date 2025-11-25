"""
Step 4: Merge AssemblyAI Transcription with YouTube Captions

This step combines:
- Speaker labels and timestamps from AssemblyAI (transcript.csv)
- Actual text content from YouTube auto-generated captions (captions.json)

Uses boundary-aware word-to-segment alignment with tolerance handling to ensure
accurate word assignment without cross-speaker leakage.

Output: final_transcript.txt with format:
[Speaker X] HH:MM:SS - HH:MM:SS | merged text from YouTube
"""

import json
import pandas as pd
import os

# Configuration for boundary-aware alignment
TOLERANCE_SECONDS = 0.5  # Tolerance for near-boundary words
GAP_THRESHOLD_SECONDS = 2.0  # Max gap to bridge when assigning orphan words


def time_to_seconds(t):
    """Convert HH:MM:SS or MM:SS to seconds (supports float seconds)"""
    parts = t.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        raise ValueError("Time must be MM:SS or HH:MM:SS")


def find_best_segment_for_gap_word(word_time, speakers, tolerance=TOLERANCE_SECONDS):
    """
    Find the best speaker segment for a word that falls in a gap or near boundaries.
    
    Key principle: When a word falls between segments, prefer the UPCOMING segment
    (the one that's about to start) over the previous segment. This ensures natural
    speaker transitions where leading words go to the new speaker.
    
    Args:
        word_time: Timestamp of the word in seconds
        speakers: List of speaker segment dicts with 'start' and 'end' keys
        tolerance: Tolerance in seconds for near-boundary words
        
    Returns:
        tuple: (segment_index, match_type) or (-1, None) if no match
    """
    candidates = []
    
    for i, seg in enumerate(speakers):
        start = seg['start']
        end = seg['end']
        
        # Calculate distances to this segment's boundaries
        dist_to_start = word_time - start  # Negative if word is before start
        dist_to_end = word_time - end      # Negative if word is before end
        
        # Word is before this segment's start
        if word_time < start:
            gap = start - word_time
            if gap <= tolerance:
                candidates.append((i, gap, 'before_start', 'boundary'))
            elif gap <= GAP_THRESHOLD_SECONDS:
                candidates.append((i, gap, 'before_start', 'gap'))
        
        # Word is after this segment's end
        elif word_time > end:
            gap = word_time - end
            if gap <= tolerance:
                candidates.append((i, gap, 'after_end', 'boundary'))
            elif gap <= GAP_THRESHOLD_SECONDS:
                candidates.append((i, gap, 'after_end', 'gap'))
    
    if not candidates:
        return (-1, None)
    
    # Sort candidates: prefer closest distance, then prefer 'before_start' (upcoming speaker)
    # This ensures words in gaps go forward to the new speaker, not backward
    def sort_key(c):
        idx, dist, position, match_type = c
        # Priority: 1. Smaller distance, 2. Prefer 'before_start' (upcoming speaker)
        # Use position weight: 'before_start' gets 0, 'after_end' gets 0.001
        position_weight = 0 if position == 'before_start' else 0.001
        return (dist + position_weight, -idx)  # -idx to prefer later segment on tie
    
    candidates.sort(key=sort_key)
    best = candidates[0]
    return (best[0], best[3])


def find_best_segment_with_overlap_resolution(word_time, speakers):
    """
    Find the best segment for a word, handling overlaps and gaps correctly.
    
    Algorithm:
    1. Use half-open intervals [start, end) to avoid double-counting at boundaries
    2. When segments overlap, prefer the later-starting segment (new speaker)
    3. When word falls in a gap, prefer the upcoming segment over the previous one
    
    Args:
        word_time: Timestamp of the word in seconds
        speakers: List of speaker segment dicts
        
    Returns:
        tuple: (segment_index, match_type) where match_type is 'exact', 'boundary', 'gap', or None
    """
    # Find all segments that contain this word using half-open intervals [start, end)
    containing_segments = []
    for i, seg in enumerate(speakers):
        start = seg['start']
        end = seg['end']
        
        # Half-open interval: word_time in [start, end)
        # Exception: for the LAST segment, include the end (closed interval)
        is_last = (i == len(speakers) - 1)
        
        if is_last:
            # Last segment uses closed interval [start, end]
            if start <= word_time <= end:
                containing_segments.append((i, seg))
        else:
            # Other segments use half-open interval [start, end)
            if start <= word_time < end:
                containing_segments.append((i, seg))
    
    if len(containing_segments) == 1:
        # Exactly one segment contains this word - use it
        return (containing_segments[0][0], 'exact')
    
    elif len(containing_segments) > 1:
        # Multiple overlapping segments - prefer the latest-starting one
        # This ensures words go to the new speaker during overlap
        best_idx = -1
        best_start = -float('inf')
        
        for idx, seg in containing_segments:
            if seg['start'] > best_start:
                best_start = seg['start']
                best_idx = idx
        
        return (best_idx, 'exact')
    
    else:
        # No segment contains this word - find best match in gaps/boundaries
        return find_best_segment_for_gap_word(word_time, speakers)


def assign_words_to_segments_boundary_aware(youtube_words, speakers):
    """
    Assign YouTube words to speaker segments using boundary-aware alignment.
    
    This algorithm respects actual speaker start/end times and correctly handles
    overlapping segments by preferring the most recently started speaker.
    
    Overlap Resolution Strategy:
    When a word falls within multiple overlapping segments, we pick the segment
    whose start time is closest to (but not after) the word's timestamp. This
    ensures words are attributed to the speaker who most recently started speaking.
    
    Args:
        youtube_words: List of (timestamp, word) tuples
        speakers: List of speaker segment dicts
        
    Returns:
        list: List of lists, where each inner list contains words for that segment
    """
    assigned = [[] for _ in speakers]
    exact_count = 0
    boundary_count = 0
    gap_count = 0
    overlap_resolved_count = 0
    unassigned_count = 0
    
    # Detect and log overlapping segments
    overlap_count = 0
    for i in range(len(speakers) - 1):
        if speakers[i]['end'] > speakers[i + 1]['start']:
            overlap_count += 1
    
    if overlap_count > 0:
        print(f"\n⚠️  Detected {overlap_count} overlapping segment pairs")
        print(f"   Using overlap resolution: prefer most recently started speaker")
    
    for word_time, word in youtube_words:
        seg_idx, match_type = find_best_segment_with_overlap_resolution(word_time, speakers)
        
        if seg_idx >= 0:
            assigned[seg_idx].append((word_time, word))
            
            if match_type == 'exact':
                # Check if this was an overlap resolution
                containing = sum(1 for seg in speakers if seg['start'] <= word_time < seg['end'] + 0.01)
                if containing > 1:
                    overlap_resolved_count += 1
                else:
                    exact_count += 1
            elif match_type == 'boundary':
                boundary_count += 1
            elif match_type == 'gap':
                gap_count += 1
        else:
            unassigned_count += 1
    
    # Sort words within each segment by timestamp
    for i in range(len(assigned)):
        assigned[i].sort(key=lambda x: x[0])
    
    # Log assignment statistics
    print(f"\n📊 Word Assignment Statistics:")
    print(f"   - Exact matches (within boundaries): {exact_count}")
    if overlap_resolved_count > 0:
        print(f"   - Overlap resolutions: {overlap_resolved_count}")
    print(f"   - Boundary tolerance matches: {boundary_count}")
    print(f"   - Gap assignments: {gap_count}")
    if unassigned_count > 0:
        print(f"   - Unassigned (too far from any segment): {unassigned_count}")
    
    return assigned


def parse_youtube_captions(captions_file):
    """
    Parse YouTube captions JSON into word-level timestamps.
    
    Handles JSON3 format with proper timestamp calculation for each word.
    
    Args:
        captions_file: Path to captions.json file
        
    Returns:
        list: List of (timestamp_seconds, word) tuples
    """
    with open(captions_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    youtube_words = []
    
    for ev in data.get("events", []):
        base_ms = ev.get("tStartMs", 0)
        dur_ms = ev.get("dDurationMs", 0)
        segs = ev.get("segs", [])
        
        if not segs:
            continue
        
        # Calculate total text length for proportional distribution
        all_tokens = []
        for seg in segs:
            text = seg.get("utf8", "")
            if text and text.strip():
                offset_ms = seg.get("tOffsetMs", 0)
                tokens = text.strip().split()
                for token in tokens:
                    all_tokens.append({
                        'token': token,
                        'offset_ms': offset_ms
                    })
        
        if not all_tokens:
            continue
        
        # Distribute words across the event duration
        if len(all_tokens) == 1:
            # Single word - use base time + offset
            t = (base_ms + all_tokens[0]['offset_ms']) / 1000.0
            youtube_words.append((t, all_tokens[0]['token']))
        else:
            # Multiple words - distribute proportionally across duration
            if dur_ms > 0:
                word_duration = dur_ms / len(all_tokens)
                for i, token_info in enumerate(all_tokens):
                    # Use offset if available, otherwise distribute evenly
                    if token_info['offset_ms'] > 0:
                        t = (base_ms + token_info['offset_ms']) / 1000.0
                    else:
                        t = (base_ms + i * word_duration) / 1000.0
                    youtube_words.append((t, token_info['token']))
            else:
                # No duration - use offsets or space words 50ms apart
                for i, token_info in enumerate(all_tokens):
                    if token_info['offset_ms'] > 0:
                        t = (base_ms + token_info['offset_ms']) / 1000.0
                    else:
                        t = (base_ms + i * 50) / 1000.0
                    youtube_words.append((t, token_info['token']))
    
    # Sort by timestamp
    youtube_words.sort(key=lambda x: x[0])
    
    return youtube_words


def run(job_folder):
    """
    Merge AssemblyAI transcript with YouTube captions using boundary-aware alignment.
    
    Uses actual speaker segment boundaries (start/end times) with tolerance handling
    to accurately assign words to speakers without cross-speaker leakage.
    
    Args:
        job_folder: Path to job working directory
        
    Returns:
        dict with status, message, and output_files
    """
    print(f"\n{'='*60}")
    print("STEP 4: Merge Transcripts (Boundary-Aware)")
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
        assembly_df["start_s"] = assembly_df["Start Time"].apply(time_to_seconds)
        assembly_df["end_s"] = assembly_df["End Time"].apply(time_to_seconds)
        assembly_df = assembly_df.sort_values("start_s").reset_index(drop=True)

        # Extract speaker segments with boundaries
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
        
        # Show segment boundaries for debugging
        print(f"\n📋 Speaker Segment Boundaries:")
        for i, sp in enumerate(speakers[:5]):  # Show first 5
            print(f"   [{i}] {sp['speaker']}: {sp['start']:.2f}s - {sp['end']:.2f}s")
        if len(speakers) > 5:
            print(f"   ... and {len(speakers) - 5} more segments")

        # --- Parse YouTube captions ---
        captions_file = os.path.join(job_folder, "captions/captions.json")

        if not os.path.exists(captions_file):
            return {
                'status': 'failed',
                'message': 'captions.json not found',
                'output_files': []
            }

        print(f"\n📄 Loading YouTube captions: {captions_file}")
        youtube_words = parse_youtube_captions(captions_file)
        print(f"✓ Extracted {len(youtube_words)} words from YouTube captions")
        
        # Show caption time range
        if youtube_words:
            first_time = youtube_words[0][0]
            last_time = youtube_words[-1][0]
            print(f"   Caption time range: {first_time:.2f}s - {last_time:.2f}s")

        if not speakers:
            return {
                'status': 'failed',
                'message': 'No speaker segments found',
                'output_files': []
            }

        # --- Assign words to segments using boundary-aware algorithm ---
        print(f"\n🔄 Assigning words to segments (tolerance: {TOLERANCE_SECONDS}s)...")
        assigned = assign_words_to_segments_boundary_aware(youtube_words, speakers)

        # --- Build final merged transcript ---
        final_lines = []
        empty_segments = 0
        
        for i, sp in enumerate(speakers):
            words = [tok for _, tok in assigned[i]]
            if words:
                merged_text = " ".join(words).strip()
            else:
                # Fallback to AssemblyAI text if no YouTube words found
                merged_text = sp["assembly_text"].strip()
                empty_segments += 1

            final_lines.append(
                f"[{sp['speaker']}] {sp['start_str']} - {sp['end_str']} | {merged_text}"
            )

        if empty_segments > 0:
            print(f"\n⚠️  {empty_segments} segments used AssemblyAI fallback (no YouTube words matched)")

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
            # Truncate long lines for preview
            if len(line) > 120:
                print(f"{line[:120]}...")
            else:
                print(line)
        print()

        return {
            'status': 'success',
            'message': f'Merged {len(speakers)} speaker segments with YouTube captions (boundary-aware)',
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
