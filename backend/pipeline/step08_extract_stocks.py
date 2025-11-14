import os
import psycopg2
from openai import OpenAI


def run(job_folder):
    """
    Step 8: Extract Stock Mentions (OPTIMIZED - using gpt-4o-mini for speed)
    """

    print("\n" + "=" * 60)
    print("STEP 8: Extract Stock Mentions (OPTIMIZED)")
    print(f"{'='*60}\n")

    try:
        # Input/Output paths
        detected_speakers_file = os.path.join(job_folder, "analysis",
                                              "detected_speakers.txt")
        filtered_transcript_file = os.path.join(job_folder, "transcripts",
                                                "filtered_transcription.txt")
        output_csv = os.path.join(job_folder, "analysis",
                                  "extracted_stocks.csv")

        # Verify input files exist
        if not os.path.exists(detected_speakers_file):
            return {
                'status':
                'failed',
                'message':
                f'Detected speakers file not found: {detected_speakers_file}'
            }
        if not os.path.exists(filtered_transcript_file):
            return {
                'status':
                'failed',
                'message':
                f'Filtered transcript file not found: {filtered_transcript_file}'
            }

        # Step 1: Load speaker mapping
        print("📖 Reading detected speakers...")
        with open(detected_speakers_file, 'r', encoding='utf-8') as f:
            detected_lines = f.read().strip().splitlines()

        anchor_speaker = detected_lines[0].split(":")[1].strip()
        pradip_speaker = detected_lines[1].split(":")[1].strip()

        print(f"✅ Speaker Mapping:")
        print(f"   Anchor = {anchor_speaker}")
        print(f"   Pradip = {pradip_speaker}\n")

        # Step 2: Load transcript
        print("📖 Reading filtered transcription...")
        with open(filtered_transcript_file, 'r', encoding='utf-8') as f:
            transcript_content = f.read().strip()

        print(
            f"✅ Transcript length: {len(transcript_content.splitlines())} lines\n"
        )

        # Step 3: Fetch OpenAI API key from DB
        print("🔑 Fetching OpenAI API key...")
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key_value FROM api_keys WHERE LOWER(provider) = 'openai' LIMIT 1"
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            return {
                'status': 'failed',
                'message': 'OpenAI API key not found in database.'
            }
        openai_api_key = result[0]

        client = OpenAI(api_key=openai_api_key)

        # Step 4: Filter transcript to Pradip's lines only (HUGE speed boost)
        print(f"🔍 Filtering transcript to {pradip_speaker}'s lines only...")
        pradip_lines = []
        for line in transcript_content.splitlines():
            if line.strip().startswith(f"[{pradip_speaker}]"):
                pradip_lines.append(line.strip())
        
        filtered_content = "\n".join(pradip_lines)
        print(f"✅ Filtered from {len(transcript_content.splitlines())} to {len(pradip_lines)} lines\n")

        # Step 5: Build OPTIMIZED prompt (simplified, compact)
        print("🤖 Preparing optimized prompt...")

        prompt = f"""Extract stock names mentioned by {pradip_speaker} from this transcript.

For each stock:
- Find exact NSE/BSE symbol (e.g., Reliance Industries → RELIANCE)
- First mention timestamp only
- Exclude mutual funds, indices, unlisted companies

Output CSV format:
STOCK NAME,STOCK SYMBOL,START TIME

Transcript:
{filtered_content}
"""

        # Step 6: Call gpt-4o-mini (FAST + CHEAP)
        print("🚀 Calling gpt-4o-mini for stock extraction...\n")

        response = client.with_options(timeout=30.0).chat.completions.create(
            model="gpt-4o-mini",  # Fast & cost-effective
            messages=[{
                "role": "system",
                "content": "You are a financial analyst. Extract stock symbols and timestamps from transcripts. Output plain CSV only, no markdown."
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0.1  # Low temperature for consistent output
        )

        csv_content = response.choices[0].message.content.strip()

        # Clean up potential markdown
        if csv_content.startswith("```"):
            csv_content = "\n".join(line for line in csv_content.splitlines()
                                    if not line.startswith("```"))

        # Step 6: Save CSV
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        with open(output_csv, "w", encoding="utf-8") as f:
            f.write(csv_content)

        stock_count = len(csv_content.strip().splitlines()) - 1
        print(f"✅ Extracted {stock_count} stock(s)\n")

        return {
            "status": "success",
            "message": f"Extracted {stock_count} stocks using gpt-4o-mini",
            "output_files": ["analysis/extracted_stocks.csv"]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "failed", "message": f"Stock extraction failed: {e}"}


if __name__ == "__main__":
    import sys
    test_folder = sys.argv[1] if len(
        sys.argv) > 1 else "backend/job_files/test_job"
    result = run(test_folder)
    print(f"\n{'='*60}")
    print(f"Result: {result['status'].upper()}")
    print(f"Message: {result['message']}")
    if 'output_files' in result:
        print(f"Output Files: {result['output_files']}")
    print(f"{'='*60}")
