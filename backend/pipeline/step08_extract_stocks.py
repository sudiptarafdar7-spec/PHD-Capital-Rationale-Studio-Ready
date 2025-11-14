import os
import psycopg2
from openai import OpenAI


def run(job_folder):
    """
    Step 8: Extract Stock Mentions (using GPT-4o for maximum accuracy)
    """

    print("\n" + "=" * 60)
    print("STEP 8: Extract Stock Mentions (GPT-4o - Accurate NSE/BSE Verification)")
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

        # Step 4: Build GPT-4o prompt with NSE/BSE verification
        print("🤖 Preparing GPT-4o prompt for accurate stock extraction...")

        prompt = f"""
You are a financial transcript analyzer using updated (2025) NSE and BSE stock listings.

Task:
1. Identify all *STOCK NAMES or COMPANY NAMES* mentioned by {pradip_speaker} (not {anchor_speaker}).
2. For each stock:
   - Find its **exact NSE or BSE trading symbol** (example: Reliance Industries → RELIANCE.NS or RELIANCE.BO).
   - **VERIFY** that the symbol is **actually listed on NSE or BSE** - no assumptions allowed.
   - If a stock name appears multiple times, take only the **first mention** by {pradip_speaker}.
   - Capture the **START TIME** from the line where {pradip_speaker} first mentions it.
3. **Exclude:**
   - Any company not publicly listed in India (NSE/BSE).
   - Mutual funds, sectors, or indices (e.g., Nifty 50, Bank Nifty, sectoral funds).
4. **Output strictly as CSV** (no markdown, no commentary) with this exact header:

STOCK NAME,STOCK SYMBOL,START TIME

Examples:
Tata Steel,TATASTEEL,00:03:12  
HDFC Bank,HDFCBANK,00:07:45
Reliance Industries,RELIANCE,00:12:30

**Full Transcript:**
{transcript_content}
"""

        # Step 5: Call GPT-4o (MOST ACCURATE MODEL)
        print("🚀 Calling GPT-4o for accurate stock extraction with NSE/BSE verification...\n")

        response = client.with_options(timeout=120.0).chat.completions.create(
            model="gpt-4o",  # Most accurate model for verification
            messages=[{
                "role": "system",
                "content": ("You are a precise financial transcript analyst with deep knowledge of Indian stock markets. "
                           "Your job is to extract *accurate NSE/BSE stock symbols* and timestamps from conversations. "
                           "You must verify each symbol against actual NSE/BSE listings before including it. "
                           "Output only publicly listed Indian equities as plain CSV without markdown or extra text.")
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0.0  # Zero temperature for maximum accuracy
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
        print(f"✅ Extracted {stock_count} stock(s) with NSE/BSE verification\n")

        return {
            "status": "success",
            "message": f"Extracted {stock_count} stocks using GPT-4o with NSE/BSE verification",
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
