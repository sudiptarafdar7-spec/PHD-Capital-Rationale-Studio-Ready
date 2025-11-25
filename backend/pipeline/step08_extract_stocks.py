import os
import re
import psycopg2
from openai import OpenAI
from backend.utils.openai_config import get_model, get_stock_extraction_prompt

# Custom symbol corrections for commonly confused stocks (keys must be UPPERCASE)
SYMBOL_CORRECTIONS = {
    "VEDANTA": "VEDL",
    "ZOMATO": "ETERNAL",
    "VODAFONE": "IDEA",
    "VI": "IDEA",
    "SHRIRAM": "SHRIRAMFIN",
    "SHREE FINANCE": "SHRIRAMFIN",
    "SHRIRAMFINANCE": "SHRIRAMFIN",
}


def parse_transcript_turns(transcript_content):
    """Parse transcript into structured turns with speaker, time, and text."""
    turns = []
    lines = transcript_content.strip().splitlines()

    for line in lines:
        match = re.match(
            r'\[(.+?)\]\s*(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})\s*\|\s*(.+)',
            line)
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
    """Pair anchor questions with Pradip's responses."""
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
                    "anchor_text":
                    anchor_turn["text"],
                    "pradip_text":
                    " ".join([t["text"] for t in pradip_turns]),
                    "start_time":
                    pradip_turns[0]["start_time"]
                })

            i = j
        else:
            i += 1

    return pairs


def has_analytical_cues(text):
    """Check if text contains market analysis language."""
    analytical_patterns = [
        r'\b(buy|sell|hold|exit|accumulate|book)\b',
        r'\b(target|price|level|support|resistance)\b',
        r'\b(stop.?loss|trailing|breakout|momentum)\b',
        r'\b(trading|rally|correction|positive|negative)\b',
        r'\b\d+\s*(rupees?|rs\.?|₹)\b', r'\b(view|recommend|advise|suggest)\b'
    ]

    text_lower = text.lower()
    return any(
        re.search(pattern, text_lower) for pattern in analytical_patterns)


def extract_stocks_from_pair(anchor_text, pradip_text, start_time, client):
    """Extract stocks from a single anchor-pradip conversation pair using GPT-4o Expert Analyst."""

    if not has_analytical_cues(pradip_text):
        return []

    prompt = f"""**Financial TV Conversation Analysis**

ANCHOR Question: "{anchor_text}"
ANALYST Response: "{pradip_text}"

**Extraction Rules:**
1. ONLY extract stocks where the ANALYST provides actionable analysis (price targets, stop-loss, recommendations, technical/fundamental view)
2. Include stocks mentioned by ANCHOR if the ANALYST subsequently analyzes them
3. Ignore casual mentions without analytical content
4. Ignore index/market references (Nifty, Sensex, Bank Nifty)

**Symbol Mapping (MANDATORY):**
- Vedanta → VEDL
- Zomato → ETERNAL
- Vodafone Idea / VI → IDEA
- Shriram Finance / Shree Finance → SHRIRAMFIN
- Bharat Electronics / BEL Defence → BEL
- Tata Motors DVR → TATAMTRDVR

**Output Format:** STOCK NAME|SYMBOL (one per line, NSE symbols only, no suffix)

**Examples:**
- HDFC Bank|HDFCBANK
- Reliance Industries|RELIANCE
- Infosys|INFY
- Tata Steel|TATASTEEL

Extract stocks now:"""

    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=[{
                "role": "system",
                "content": get_stock_extraction_prompt()
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0,
            max_tokens=300,
            timeout=20)

        content = (response.choices[0].message.content or "").strip()
        stocks = []

        for line in content.splitlines():
            line = line.strip()
            if '|' in line and line.count('|') == 1:
                parts = line.split('|')
                if len(parts) == 2:
                    stock_name = parts[0].strip()
                    symbol = parts[1].strip().upper()

                    # Strip .NS and .BO suffixes
                    if symbol.endswith('.NS'):
                        symbol = symbol[:-3]
                    elif symbol.endswith('.BO'):
                        symbol = symbol[:-3]

                    # Apply custom symbol corrections
                    symbol_upper = symbol.upper()
                    if symbol_upper in SYMBOL_CORRECTIONS:
                        symbol = SYMBOL_CORRECTIONS[symbol_upper]

                    # Only add if we have a valid symbol
                    if symbol:
                        stocks.append({
                            "stock_name": stock_name,
                            "stock_symbol": symbol,
                            "start_time": start_time
                        })

        return stocks

    except Exception as e:
        print(f"   ⚠️ GPT extraction failed for pair: {e}")
        return []


def validate_and_format_csv(stocks):
    """Validate extracted stocks and format as CSV - deduplicate by symbol."""
    if not stocks:
        return "STOCK NAME,STOCK SYMBOL,START TIME\n"

    seen_symbols = set()
    unique_stocks = []

    for stock in stocks:
        symbol = stock["stock_symbol"]
        if symbol not in seen_symbols:
            seen_symbols.add(symbol)
            unique_stocks.append(stock)

    csv_rows = ["STOCK NAME,STOCK SYMBOL,START TIME"]
    for stock in sorted(unique_stocks, key=lambda x: x["start_time"]):
        csv_rows.append(
            f"{stock['stock_name']},{stock['stock_symbol']},{stock['start_time']}"
        )

    return "\n".join(csv_rows)


def run(job_folder):
    """
    Step 8: Extract Stock Mentions (Hybrid: Deterministic pairing + GPT-4o + Symbol validation)
    """

    print("\n" + "=" * 60)
    print("STEP 8: Extract Stock Mentions (Hybrid Approach)")
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
                'message': f'Detected speakers file not found'
            }
        if not os.path.exists(filtered_transcript_file):
            return {
                'status': 'failed',
                'message': f'Filtered transcript file not found'
            }

        print("📖 Reading detected speakers...")
        with open(detected_speakers_file, 'r', encoding='utf-8') as f:
            detected_lines = f.read().strip().splitlines()

        anchor_speaker = detected_lines[0].split(":")[1].strip()
        pradip_speaker = detected_lines[1].split(":")[1].strip()

        print(f"✅ Anchor = {anchor_speaker}, Pradip = {pradip_speaker}\n")

        print("📖 Reading filtered transcription...")
        with open(filtered_transcript_file, 'r', encoding='utf-8') as f:
            transcript_content = f.read().strip()

        print(f"✅ Transcript: {len(transcript_content.splitlines())} lines\n")

        print("🔍 Parsing transcript into structured turns...")
        turns = parse_transcript_turns(transcript_content)
        print(f"✅ Parsed {len(turns)} turns\n")

        print("🔗 Pairing anchor questions with Pradip responses...")
        pairs = pair_anchor_pradip_turns(turns, anchor_speaker, pradip_speaker)
        print(f"✅ Found {len(pairs)} conversation pairs\n")

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
            return {'status': 'failed', 'message': 'OpenAI API key not found'}

        client = OpenAI(api_key=result[0])

        print("🎯 Extracting stocks from each pair (GPT-4o + validation)...\n")
        all_stocks = []

        for i, pair in enumerate(pairs, 1):
            stocks = extract_stocks_from_pair(pair["anchor_text"],
                                              pair["pradip_text"],
                                              pair["start_time"], client)
            all_stocks.extend(stocks)

            if stocks:
                print(
                    f"   Pair {i}/{len(pairs)}: Found {len(stocks)} stock(s)")

        print(f"\n✅ Total extracted: {len(all_stocks)} stock mentions\n")

        print("📝 Validating and formatting CSV...")
        csv_content = validate_and_format_csv(all_stocks)

        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        with open(output_csv, "w", encoding="utf-8") as f:
            f.write(csv_content)

        stock_count = max(0, len(csv_content.strip().splitlines()) - 1)
        print(f"✅ Final unique stocks: {stock_count}\n")

        if stock_count > 0:
            lines = csv_content.strip().splitlines()[1:]
            for line in lines[:5]:
                print(f"   • {line}")
            if stock_count > 5:
                print(f"   ... and {stock_count - 5} more\n")

        return {
            "status": "success",
            "message": f"Extracted {stock_count} stocks using hybrid approach",
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
