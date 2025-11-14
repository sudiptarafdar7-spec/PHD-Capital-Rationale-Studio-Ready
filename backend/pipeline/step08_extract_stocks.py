import os
import re
import psycopg2
from openai import OpenAI
from .nse_bse_stocks import NSE_BSE_STOCK_MASTER, get_stock_symbol, fuzzy_match_stock


def parse_transcript_turns(transcript_content, anchor_speaker, pradip_speaker):
    """
    Parse transcript into structured turns with speaker, time range, and text.
    Returns: list of {speaker, start_time, end_time, text}
    """
    turns = []
    lines = transcript_content.strip().splitlines()
    
    for line in lines:
        match = re.match(r'\[(.+?)\]\s*(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})\s*\|\s*(.+)', line)
        if match:
            speaker, start_time, end_time, text = match.groups()
            turns.append({
                "speaker": speaker.strip(),
                "start_time": start_time.strip(),
                "end_time": end_time.strip(),
                "text": text.strip()
            })
    
    return turns


def pair_anchor_pradip_turns(turns, anchor_speaker, pradip_speaker):
    """
    Pair anchor questions with Pradip's responses.
    Returns: list of {anchor_turn, pradip_turns}
    """
    pairs = []
    i = 0
    
    while i < len(turns):
        if turns[i]["speaker"] == anchor_speaker:
            anchor_turn = turns[i]
            pradip_turns = []
            
            j = i + 1
            while j < len(turns) and turns[j]["speaker"] == pradip_speaker:
                pradip_turns.append(turns[j])
                j += 1
            
            if pradip_turns:
                pairs.append({
                    "anchor_turn": anchor_turn,
                    "pradip_turns": pradip_turns
                })
            
            i = j
        else:
            i += 1
    
    return pairs


def has_analytical_cues(text):
    """
    Check if Pradip's text contains analytical cues (buy/sell/hold/target/price/stop loss)
    """
    analytical_keywords = [
        r'\bbuy\b', r'\bsell\b', r'\bhold\b', r'\btarget\b', r'\bprice\b',
        r'\bstop.?loss\b', r'\bexit\b', r'\baccumulate\b', r'\bbook.*profit\b',
        r'\baverage\b', r'\bzone\b', r'\blevels?\b', r'\bmomentum\b',
        r'\bbreakout\b', r'\bsupport\b', r'\bresistance\b', r'\btrading\b',
        r'\bview\b', r'\ballocation\b', r'\bportfolio\b'
    ]
    
    text_lower = text.lower()
    for pattern in analytical_keywords:
        if re.search(pattern, text_lower):
            return True
    
    return False


def extract_stocks_deterministic(pairs, anchor_speaker, pradip_speaker):
    """
    Deterministically extract stocks from anchor-pradip pairs.
    Returns: list of {stock_name, stock_symbol, start_time}
    """
    extracted_stocks = {}
    
    for pair in pairs:
        anchor_text = pair["anchor_turn"]["text"]
        pradip_combined = " ".join([t["text"] for t in pair["pradip_turns"]])
        first_pradip_time = pair["pradip_turns"][0]["start_time"] if pair["pradip_turns"] else None
        
        anchor_stocks = fuzzy_match_stock(anchor_text)
        pradip_stocks = fuzzy_match_stock(pradip_combined)
        
        if pradip_stocks:
            for stock_name, symbol, confidence in pradip_stocks:
                if stock_name not in extracted_stocks and has_analytical_cues(pradip_combined):
                    extracted_stocks[stock_name] = {
                        "stock_name": stock_name,
                        "stock_symbol": symbol,
                        "start_time": first_pradip_time
                    }
        
        elif anchor_stocks and has_analytical_cues(pradip_combined):
            for stock_name, symbol, confidence in anchor_stocks:
                if stock_name not in extracted_stocks:
                    extracted_stocks[stock_name] = {
                        "stock_name": stock_name,
                        "stock_symbol": symbol,
                        "start_time": first_pradip_time
                    }
    
    return list(extracted_stocks.values())


def run(job_folder):
    """
    Step 8: Extract Stock Mentions (Deterministic with GPT-4o fallback)
    """

    print("\n" + "=" * 60)
    print("STEP 8: Extract Stock Mentions (Deterministic)")
    print(f"{'='*60}\n")

    try:
        detected_speakers_file = os.path.join(job_folder, "analysis",
                                              "detected_speakers.txt")
        filtered_transcript_file = os.path.join(job_folder, "transcripts",
                                                "filtered_transcription.txt")
        output_csv = os.path.join(job_folder, "analysis",
                                  "extracted_stocks.csv")

        if not os.path.exists(detected_speakers_file):
            return {
                'status': 'failed',
                'message': f'Detected speakers file not found: {detected_speakers_file}'
            }
        if not os.path.exists(filtered_transcript_file):
            return {
                'status': 'failed',
                'message': f'Filtered transcript file not found: {filtered_transcript_file}'
            }

        print("📖 Reading detected speakers...")
        with open(detected_speakers_file, 'r', encoding='utf-8') as f:
            detected_lines = f.read().strip().splitlines()

        anchor_speaker = detected_lines[0].split(":")[1].strip()
        pradip_speaker = detected_lines[1].split(":")[1].strip()

        print(f"✅ Speaker Mapping:")
        print(f"   Anchor = {anchor_speaker}")
        print(f"   Pradip = {pradip_speaker}\n")

        print("📖 Reading filtered transcription...")
        with open(filtered_transcript_file, 'r', encoding='utf-8') as f:
            transcript_content = f.read().strip()

        print(f"✅ Transcript length: {len(transcript_content.splitlines())} lines\n")

        print("🔍 Parsing transcript into structured turns...")
        turns = parse_transcript_turns(transcript_content, anchor_speaker, pradip_speaker)
        print(f"✅ Parsed {len(turns)} turns\n")

        print("🔗 Pairing anchor questions with Pradip responses...")
        pairs = pair_anchor_pradip_turns(turns, anchor_speaker, pradip_speaker)
        print(f"✅ Found {len(pairs)} anchor-pradip conversation pairs\n")

        print("🎯 Extracting stocks deterministically...")
        stocks = extract_stocks_deterministic(pairs, anchor_speaker, pradip_speaker)
        print(f"✅ Deterministically extracted {len(stocks)} stock(s)\n")

        if len(stocks) == 0:
            print("⚠️  No stocks found using deterministic method")
            print("🤖 Falling back to GPT-4o for edge case extraction...\n")
            
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

            prompt = f"""
You are a financial transcript analyzer using updated (2025) NSE and BSE stock listings.

Task:
1. Identify all *STOCK NAMES or COMPANY NAMES* discussed by {pradip_speaker} (not {anchor_speaker}).
2. For each stock:
   - Find its **exact NSE or BSE trading symbol** (example: Reliance Industries → RELIANCE.NS).
   - Verify that the symbol is **actually listed on NSE or BSE** (no assumptions).
   - If a stock name appears multiple times, take only the first mention.
   - Capture the START TIME from the line where {pradip_speaker} first discusses it.
3. IMPORTANT: If {anchor_speaker} asks about a stock and {pradip_speaker} gives analysis WITHOUT repeating the stock name, include it.
4. Exclude:
   - Any company not publicly listed in India (NSE/BSE).
   - Mutual funds, sectors, or indices (e.g., Nifty 50, Bank Nifty).
5. Output strictly as a CSV (no markdown, no commentary) with the header:

STOCK NAME,STOCK SYMBOL,START TIME

Examples:
Tata Steel,TATASTEEL.NS,00:03:12  
HDFC Bank,HDFCBANK.NS,00:07:45

Transcript:
{transcript_content}
"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "system",
                    "content": ("You are a precise financial transcript analyst. "
                               "Your job is to extract *accurate NSE/BSE stock symbols* and timestamps "
                               "from a conversation, outputting only valid, listed Indian equities. "
                               "Respond strictly as plain CSV without markdown or extra text.")
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0,
                timeout=30
            )

            csv_content = (response.choices[0].message.content or "").strip()
            
            if csv_content.startswith("```"):
                csv_content = "\n".join(line for line in csv_content.splitlines()
                                        if not line.startswith("```"))
        else:
            print("📝 Converting to CSV format...")
            csv_rows = ["STOCK NAME,STOCK SYMBOL,START TIME"]
            for stock in sorted(stocks, key=lambda x: x["start_time"]):
                csv_rows.append(f"{stock['stock_name']},{stock['stock_symbol']},{stock['start_time']}")
            csv_content = "\n".join(csv_rows)

        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        with open(output_csv, "w", encoding="utf-8") as f:
            f.write(csv_content)

        stock_count = len(csv_content.strip().splitlines()) - 1
        print(f"✅ Final output: {stock_count} stock(s)\n")

        for stock in stocks[:5]:
            print(f"   • {stock['stock_name']} ({stock['stock_symbol']}) @ {stock['start_time']}")
        
        if len(stocks) > 5:
            print(f"   ... and {len(stocks) - 5} more")

        return {
            "status": "success",
            "message": f"Extracted {stock_count} stocks deterministically",
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
