"""
Step 8: Extract Stock Mentions - Intelligent Chunk-Based Detection with Gemini

This step uses a multi-phase approach:
1. Split transcript into 4 chunks (ending at Pradip's lines for context preservation)
2. For each chunk, Gemini reads line-by-line, word-by-word to detect stocks
3. Handle transcription spelling errors intelligently
4. Exclude indices (Nifty, Bank Nifty, Sensex, etc.)
5. Merge all chunks and run final Gemini for accurate NSE symbols
6. Output final CSV with STOCK NAME, STOCK SYMBOL, START TIME
"""

import os
import re
import psycopg2
import google.generativeai as genai
from backend.utils.gemini_config import get_gemini_model

NUM_CHUNKS = 4

INDICES_TO_EXCLUDE = [
    "nifty", "bank nifty", "banknifty", "sensex", "nifty50", "nifty 50",
    "finnifty", "fin nifty", "midcap nifty", "nifty midcap", "nifty it",
    "nifty bank", "index", "indices", "bse", "nse", "market"
]

SPELLING_CORRECTIONS = {
    "sujour energy": "Suzlon Energy",
    "sujour": "Suzlon Energy",
    "sujalan": "Suzlon Energy",
    "sujolon": "Suzlon Energy",
    "sujlon": "Suzlon Energy",
    "c bank": "ICICI Bank",
    "cbank": "ICICI Bank",
    "cera bank": None,
    "cerabank": None,
    "adan power": "Adani Power",
    "adanpower": "Adani Power",
    "adan": "Adani Power",
    "adanipower": "Adani Power",
    "adani power": "Adani Power",
    "tatta power": "Tata Power",
    "tata power": "Tata Power",
    "tatapower": "Tata Power",
    "td power": "TD Power Systems",
    "tdpower": "TD Power Systems",
    "swigee": "Swiggy",
    "swigi": "Swiggy",
    "zometo": "Zomato",
    "zomatto": "Zomato",
    "relayance": "Reliance",
    "infosis": "Infosys",
    "bharti airtal": "Bharti Airtel",
    "airtal": "Bharti Airtel",
    "vodafone idea": "Vodafone Idea",
    "vodafone": "Vodafone Idea",
    "vi": "Vodafone Idea",
    "idea": "Vodafone Idea",
    "suzlon energy": "Suzlon Energy",
    "suzlon": "Suzlon Energy",
    "city union bank": "City Union Bank",
    "city union": "City Union Bank",
    "cub": "City Union Bank",
    "indus tower": "Indus Towers",
    "indus towers": "Indus Towers",
    "industower": "Indus Towers",
    "shipping corp": "Shipping Corporation",
    "shipping corporation": "Shipping Corporation",
    "sci": "Shipping Corporation",
    "supriya life": "Supriya Life Sciences",
    "supriya lifesciences": "Supriya Life Sciences",
    "supriya life sciences": "Supriya Life Sciences",
    "apollo tyre": "Apollo Tyres",
    "apollo tyres": "Apollo Tyres",
    "titan": "Titan",
    "mrpl": "MRPL",
    "cdsl": "CDSL",
    "hitachi": None,
}

INVALID_STOCKS = [
    "cera bank", "cerabank", "sujalan", "hitachi", 
    "c bank", "cbank", "adan", "td power"
]

SYMBOL_NORMALIZATION = {
    "ADANPOWER": "ADANIPOWER",
    "TATAPOWER": "TATAPOWER",
    "INDUSTOWER": "INDUSTOWER",
    "SUZLON": "SUZLON",
    "IDEA": "IDEA",
    "BHARTIARTL": "BHARTIARTL",
    "CUB": "CUB",
    "MRPL": "MRPL",
    "SCI": "SCI",
    "TITAN": "TITAN",
    "APOLLOTYRE": "APOLLOTYRE",
    "SUPRIYA": "SUPRIYA",
    "SWIGGY": "SWIGGY",
    "ZOMATO": "ZOMATO",
    "CDSL": "CDSL",
    "TDPOWERSYS": "TDPOWERSYS",
}


def parse_transcript_lines(transcript_content):
    """Parse transcript into structured lines with speaker, time, and text."""
    lines = []
    raw_lines = transcript_content.strip().splitlines()

    for line in raw_lines:
        match = re.match(
            r'\[(.+?)\]\s*(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})\s*\|\s*(.+)',
            line)
        if match:
            speaker, start_time, end_time, text = match.groups()
            lines.append({
                "speaker": speaker.strip(),
                "start_time": start_time.strip(),
                "end_time": end_time.strip(),
                "text": text.strip(),
                "raw_line": line.strip()
            })

    return lines


def split_into_chunks(lines, pradip_speaker, num_chunks=NUM_CHUNKS):
    """
    Split transcript lines into chunks, ensuring each chunk ends at a Pradip line.
    Uses case-insensitive comparison with the actual detected Pradip speaker name.
    Falls back to even splits if Pradip turns are sparse.
    """
    if len(lines) < num_chunks:
        return [lines] if lines else []
    
    pradip_lower = pradip_speaker.lower().strip()
    target_size = len(lines) // num_chunks
    chunks = []
    current_chunk = []
    chunk_count = 0
    
    for i, line in enumerate(lines):
        current_chunk.append(line)
        
        is_pradip = line["speaker"].lower().strip() == pradip_lower
        reached_target = len(current_chunk) >= target_size
        not_last_chunk = chunk_count < num_chunks - 1
        
        if is_pradip and reached_target and not_last_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            chunk_count += 1
    
    if current_chunk:
        if chunks and len(current_chunk) < target_size // 2:
            chunks[-1].extend(current_chunk)
        else:
            chunks.append(current_chunk)
    
    if len(chunks) < num_chunks and len(lines) >= num_chunks:
        chunks = []
        chunk_size = len(lines) // num_chunks
        for i in range(num_chunks):
            start_idx = i * chunk_size
            if i == num_chunks - 1:
                chunks.append(lines[start_idx:])
            else:
                chunks.append(lines[start_idx:start_idx + chunk_size])
    
    return chunks


def format_chunk_for_analysis(chunk_lines):
    """Format chunk lines as JSON array for structured OpenAI analysis."""
    import json
    formatted = []
    for line in chunk_lines:
        formatted.append({
            "time": line['start_time'],
            "speaker": line['speaker'],
            "text": line['text']
        })
    return json.dumps(formatted, indent=2)


def extract_stocks_from_chunk(chunk_lines, chunk_num, model):
    """
    Extract stocks from a single chunk using Gemini with word-by-word analysis.
    Uses structured JSON input/output for reliable parsing.
    Returns list of (time, stock_name) tuples.
    """
    import json
    
    chunk_json = []
    for line in chunk_lines:
        chunk_json.append({
            "time": line['start_time'],
            "speaker": line['speaker'],
            "text": line['text']
        })
    
    prompt = f"""**CRITICAL TASK: Stock Name Detection in Financial TV Transcript - Chunk {chunk_num}**

You are an expert at identifying Indian stock names in financial transcripts.
You have deep knowledge of:
- All NSE/BSE listed companies and their common abbreviations
- Common transcription errors and how to correct them
- The difference between company names and market indices

You are analyzing a transcript from an Indian financial TV show where an analyst discusses stocks.
Your task is to read EVERY LINE, WORD BY WORD, and identify ALL stock names mentioned.

**IMPORTANT INSTRUCTIONS:**
1. Read each line carefully, word by word
2. Detect ALL company/stock names mentioned by BOTH speakers (Anchor and Analyst)
3. Include these RECENT IPO STOCKS (often discussed):
   - Swiggy (food delivery)
   - Zomato (food delivery)
   - Paytm / One97 Communications
   - Nykaa / FSN E-Commerce
   - PolicyBazaar / PB Fintech
   - Delhivery
   - CarTrade
   - Ola Electric
   - FirstCry / Brainbees
   
4. Use INTELLIGENCE to understand misspelled stock names due to transcription errors:
   - "Swigee" / "Swigi" → Swiggy
   - "Zometo" / "Zomatto" → Zomato
   - "Relayance" → Reliance
   - "Infosis" → Infosys
   - "Tatta Motors" → Tata Motors
   - "HDFC Benk" → HDFC Bank
   - "Bajaj Finanse" → Bajaj Finance
   - "Maruti Suzuky" → Maruti Suzuki
   - "Shriram Finence" → Shriram Finance
   - "Vedenta" → Vedanta
   - "Bharti Airtal" → Bharti Airtel
   - "Coil India" → Coal India
   - "Adani Ent" → Adani Enterprises
   - "L&T" → Larsen & Toubro
   - "SBI" → State Bank of India
   - "ICICI" → ICICI Bank
   - "TCS" → Tata Consultancy Services
   - "M&M" → Mahindra & Mahindra
   - "BEL" → Bharat Electronics
   - "HAL" → Hindustan Aeronautics
   - "ITC" → ITC
   - Similar phonetic/spelling variations

5. EXCLUDE these indices (NOT stocks):
   - Nifty, Bank Nifty, Sensex, Nifty 50, Finnifty
   - Any index references

6. DO NOT skip any stock - even if mentioned briefly or in a question
7. DO NOT add stocks that were NOT discussed
8. Use the EXACT timestamp from the input line where the stock is mentioned

**TRANSCRIPT DATA (JSON format):**
{json.dumps(chunk_json, indent=2)}

**OUTPUT FORMAT - Return a JSON array:**
[
  {{"time": "HH:MM:SS", "stock": "Stock Name"}},
  {{"time": "HH:MM:SS", "stock": "Stock Name"}}
]

**IMPORTANT:** Return ONLY the JSON array, no other text. Use exact timestamps from input."""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2000,
            )
        )
        
        content = (response.text or "").strip()
        
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
        
        stocks = []
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "time" in item and "stock" in item:
                        time_str = item["time"].strip()
                        stock_name = item["stock"].strip()
                        
                        is_index = any(idx in stock_name.lower() for idx in INDICES_TO_EXCLUDE)
                        if not is_index and len(stock_name) > 1:
                            stocks.append((time_str, stock_name))
                
                print(f"      📋 OpenAI detected stocks: {[s[1] for s in stocks]}")
        except json.JSONDecodeError as e:
            print(f"      ⚠️ JSON parse error: {e}")
            print(f"      📄 Raw response: {content[:500]}...")
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                match = re.match(r'(\d{2}:\d{2}:\d{2})\s*[-–—]\s*(.+)', line)
                if match:
                    time_str, stock_name = match.groups()
                    stock_name = stock_name.strip()
                    is_index = any(idx in stock_name.lower() for idx in INDICES_TO_EXCLUDE)
                    if not is_index and len(stock_name) > 1:
                        stocks.append((time_str, stock_name))

        return stocks

    except Exception as e:
        print(f"   ⚠️ Chunk {chunk_num} extraction failed: {e}")
        return []


def merge_and_deduplicate_stocks(all_chunk_stocks):
    """Merge stocks from all chunks and remove duplicates, keeping earliest time."""
    stock_dict = {}
    
    for time_str, stock_name in all_chunk_stocks:
        stock_key = stock_name.lower().strip()
        
        if stock_key not in stock_dict:
            stock_dict[stock_key] = (time_str, stock_name)
        else:
            existing_time = stock_dict[stock_key][0]
            if time_str < existing_time:
                stock_dict[stock_key] = (time_str, stock_name)
    
    merged = [(v[0], v[1]) for v in stock_dict.values()]
    merged.sort(key=lambda x: x[0])
    
    return merged


def get_accurate_symbols(merged_stocks, model):
    """
    Final Gemini call to get accurate NSE stock symbols for all detected stocks.
    Uses JSON input/output for reliable parsing.
    """
    import json
    
    if not merged_stocks:
        return []
    
    input_stocks = []
    for i, (time_str, name) in enumerate(merged_stocks):
        input_stocks.append({
            "id": i + 1,
            "time": time_str,
            "name": name
        })
    
    prompt = f"""You are an expert at mapping Indian stock names to their NSE trading symbols.
You must process EVERY stock in the input - do not skip any.
Always return valid JSON array format with all stocks.

**CRITICAL TASK: Convert ALL Stock Names to NSE Symbols**

You MUST process ALL {len(merged_stocks)} stocks listed below. Do NOT skip any.

**INPUT STOCKS (JSON):**
{json.dumps(input_stocks, indent=2)}

**YOUR TASK:**
For EACH stock in the input, provide the correct NSE trading symbol.

**SYMBOL MAPPING RULES:**
- Swiggy → SWIGGY
- Zomato → ZOMATO
- Paytm → PAYTM
- Nykaa → NYKAA
- PolicyBazaar → POLICYBZR
- Delhivery → DELHIVERY
- Vedanta → VEDL
- Vodafone Idea / VI → IDEA
- Shriram Finance → SHRIRAMFIN
- Supriya Life Sciences → SUPRIYA
- Apollo Tyres → APOLLOTYRE
- Shipping Corporation → SCI
- City Union Bank → CUB
- MRPL → MRPL
- Indus Towers → INDUSTOWER
- Suzlon Energy → SUZLON
- Cera Sanitaryware → CERA
- TD Power → TDPOWERSYS
- Tata Power → TATAPOWER
- Titan → TITAN
- Bharti Airtel → BHARTIARTL
- Coal India → COALINDIA
- L&T → LT
- M&M → M&M
- SBI → SBIN
- ICICI Bank → ICICIBANK
- HDFC Bank → HDFCBANK
- TCS → TCS
- Infosys → INFY
- Reliance → RELIANCE
- Tata Motors → TATAMOTORS
- Tata Steel → TATASTEEL
- Maruti Suzuki → MARUTI
- ITC → ITC
- Power Grid → POWERGRID
- NTPC → NTPC
- ONGC → ONGC
- Sun Pharma → SUNPHARMA
- Cipla → CIPLA
- Asian Paints → ASIANPAINT
- Nestle → NESTLEIND
- JSW Steel → JSWSTEEL
- Hindalco → HINDALCO
- Hero MotoCorp → HEROMOTOCO
- Bajaj Auto → BAJAJ-AUTO
- TVS Motor → TVSMOTOR
- For any other stock, use the standard NSE symbol

**NO .NS or .BO suffix - just the symbol**

**OUTPUT FORMAT - Return a JSON array with ALL {len(merged_stocks)} stocks:**
[
  {{"time": "HH:MM:SS", "name": "Stock Name", "symbol": "SYMBOL"}},
  ...
]

**IMPORTANT:** 
- Return ONLY the JSON array
- Include ALL {len(merged_stocks)} stocks - do not skip any
- Use exact timestamps from input"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                max_output_tokens=4000,
            )
        )

        content = (response.text or "").strip()
        
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
        
        print(f"   📄 OpenAI returned {len(content)} characters")
        
        results = []
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        time_str = item.get("time", "").strip()
                        stock_name = item.get("name", "").strip()
                        symbol = item.get("symbol", "").strip().upper()
                        
                        if symbol.endswith('.NS'):
                            symbol = symbol[:-3]
                        elif symbol.endswith('.BO'):
                            symbol = symbol[:-3]
                        
                        if stock_name and symbol and time_str:
                            results.append({
                                "stock_name": stock_name,
                                "stock_symbol": symbol,
                                "start_time": time_str
                            })
                
                print(f"   ✅ Parsed {len(results)} stocks from JSON response")
                
                if len(results) < len(merged_stocks):
                    print(f"   ⚠️ Warning: Only got {len(results)}/{len(merged_stocks)} stocks, using fallback mapping")
                    results = fallback_symbol_mapping(merged_stocks)
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON parse error: {e}")
            print(f"   🔄 Using fallback symbol mapping...")
            results = fallback_symbol_mapping(merged_stocks)

        return results

    except Exception as e:
        print(f"   ⚠️ Symbol extraction failed: {e}")
        print(f"   🔄 Using fallback symbol mapping...")
        return fallback_symbol_mapping(merged_stocks)


def fallback_symbol_mapping(merged_stocks):
    """
    Fallback symbol mapping using a local dictionary when OpenAI fails.
    """
    SYMBOL_MAP = {
        "swiggy": "SWIGGY",
        "swigee": "SWIGGY",
        "swigi": "SWIGGY",
        "zomato": "ZOMATO",
        "zometo": "ZOMATO",
        "paytm": "PAYTM",
        "one97": "PAYTM",
        "nykaa": "NYKAA",
        "fsn ecommerce": "NYKAA",
        "policybazaar": "POLICYBZR",
        "pb fintech": "POLICYBZR",
        "delhivery": "DELHIVERY",
        "cartrade": "CARTRADE",
        "ola electric": "OLAELEC",
        "firstcry": "FIRSTCRY",
        "brainbees": "FIRSTCRY",
        "supriya life sciences": "SUPRIYA",
        "supriya lifesciences": "SUPRIYA",
        "supriya": "SUPRIYA",
        "apollo tyres": "APOLLOTYRE",
        "apollo tyre": "APOLLOTYRE",
        "shipping corporation": "SCI",
        "shipping corp": "SCI",
        "titan": "TITAN",
        "city union bank": "CUB",
        "mrpl": "MRPL",
        "indus towers": "INDUSTOWER",
        "indus tower": "INDUSTOWER",
        "bharti airtel": "BHARTIARTL",
        "airtel": "BHARTIARTL",
        "vodafone idea": "IDEA",
        "vodafone": "IDEA",
        "vi": "IDEA",
        "idea": "IDEA",
        "suzlon energy": "SUZLON",
        "suzlon": "SUZLON",
        "cera bank": "CERA",
        "cera sanitaryware": "CERA",
        "cera": "CERA",
        "tata power": "TATAPOWER",
        "td power": "TDPOWERSYS",
        "vedanta": "VEDL",
        "shriram finance": "SHRIRAMFIN",
        "shriram": "SHRIRAMFIN",
        "coal india": "COALINDIA",
        "l&t": "LT",
        "larsen": "LT",
        "m&m": "M&M",
        "mahindra": "M&M",
        "sbi": "SBIN",
        "state bank": "SBIN",
        "icici bank": "ICICIBANK",
        "icici": "ICICIBANK",
        "hdfc bank": "HDFCBANK",
        "hdfc": "HDFCBANK",
        "axis bank": "AXISBANK",
        "kotak bank": "KOTAKBANK",
        "kotak": "KOTAKBANK",
        "bajaj finance": "BAJFINANCE",
        "bajaj finserv": "BAJAJFINSV",
        "tcs": "TCS",
        "tata consultancy": "TCS",
        "infosys": "INFY",
        "wipro": "WIPRO",
        "hcl tech": "HCLTECH",
        "tech mahindra": "TECHM",
        "reliance": "RELIANCE",
        "reliance industries": "RELIANCE",
        "tata motors": "TATAMOTORS",
        "tata steel": "TATASTEEL",
        "maruti": "MARUTI",
        "maruti suzuki": "MARUTI",
        "itc": "ITC",
        "adani enterprises": "ADANIENT",
        "adani ent": "ADANIENT",
        "adani ports": "ADANIPORTS",
        "power grid": "POWERGRID",
        "ntpc": "NTPC",
        "ongc": "ONGC",
        "bpcl": "BPCL",
        "indian oil": "IOC",
        "ioc": "IOC",
        "gail": "GAIL",
        "sun pharma": "SUNPHARMA",
        "dr reddy": "DRREDDY",
        "dr reddys": "DRREDDY",
        "cipla": "CIPLA",
        "divis labs": "DIVISLAB",
        "apollo hospitals": "APOLLOHOSP",
        "asian paints": "ASIANPAINT",
        "nestle": "NESTLEIND",
        "hindustan unilever": "HINDUNILVR",
        "hul": "HINDUNILVR",
        "britannia": "BRITANNIA",
        "ultratech cement": "ULTRACEMCO",
        "ultratech": "ULTRACEMCO",
        "grasim": "GRASIM",
        "jsw steel": "JSWSTEEL",
        "hindalco": "HINDALCO",
        "eicher motors": "EICHERMOT",
        "eicher": "EICHERMOT",
        "hero motocorp": "HEROMOTOCO",
        "hero": "HEROMOTOCO",
        "bajaj auto": "BAJAJ-AUTO",
        "tvs motor": "TVSMOTOR",
        "tvs": "TVSMOTOR",
        "bharat electronics": "BEL",
        "bel": "BEL",
        "hindustan aeronautics": "HAL",
        "hal": "HAL",
    }
    
    results = []
    for time_str, stock_name in merged_stocks:
        name_lower = stock_name.lower().strip()
        
        symbol = None
        for key, sym in SYMBOL_MAP.items():
            if key in name_lower or name_lower in key:
                symbol = sym
                break
        
        if not symbol:
            symbol = stock_name.upper().replace(" ", "").replace(".", "")[:15]
        
        results.append({
            "stock_name": stock_name,
            "stock_symbol": symbol,
            "start_time": time_str
        })
    
    return results


def correct_stock_name(stock_name):
    """
    Apply spelling corrections and validate stock names.
    Returns corrected name or None if invalid.
    """
    name_lower = stock_name.lower().strip()
    
    for invalid in INVALID_STOCKS:
        if invalid in name_lower:
            print(f"      🚫 Removing invalid stock: {stock_name}")
            return None
    
    for wrong, correct in SPELLING_CORRECTIONS.items():
        if wrong == name_lower or wrong in name_lower:
            if correct is None:
                print(f"      🚫 Removing invalid stock: {stock_name}")
                return None
            if correct.lower() != stock_name.lower():
                print(f"      🔧 Correcting: {stock_name} → {correct}")
            return correct
    
    return stock_name


def normalize_symbol(symbol):
    """Normalize stock symbols to prevent duplicates."""
    symbol_upper = symbol.upper().strip()
    
    return SYMBOL_NORMALIZATION.get(symbol_upper, symbol_upper)


def validate_and_format_csv(stocks):
    """
    Validate extracted stocks and format as CSV.
    - Apply spelling corrections
    - Remove invalid stocks
    - Deduplicate by normalized symbol
    """
    if not stocks:
        return "STOCK NAME,STOCK SYMBOL,START TIME\n"

    print("\n   🔍 Applying spelling corrections and validation...")
    
    corrected_stocks = []
    for stock in stocks:
        corrected_name = correct_stock_name(stock["stock_name"])
        if corrected_name:
            corrected_stocks.append({
                "stock_name": corrected_name,
                "stock_symbol": stock["stock_symbol"],
                "start_time": stock["start_time"]
            })
    
    print(f"\n   📊 Normalizing symbols and removing duplicates...")
    
    seen_normalized = {}
    unique_stocks = []
    
    for stock in corrected_stocks:
        normalized_symbol = normalize_symbol(stock["stock_symbol"])
        
        if normalized_symbol not in seen_normalized:
            seen_normalized[normalized_symbol] = True
            stock["stock_symbol"] = normalized_symbol
            unique_stocks.append(stock)
        else:
            print(f"      🔄 Removing duplicate: {stock['stock_name']} ({stock['stock_symbol']})")

    csv_rows = ["STOCK NAME,STOCK SYMBOL,START TIME"]
    for stock in sorted(unique_stocks, key=lambda x: x["start_time"]):
        csv_rows.append(
            f"{stock['stock_name']},{stock['stock_symbol']},{stock['start_time']}"
        )

    return "\n".join(csv_rows)


def run(job_folder):
    """
    Step 8: Extract Stock Mentions using Intelligent Chunk-Based Detection with Gemini
    
    Process:
    1. Split transcript into 4 chunks (ending at Pradip lines)
    2. For each chunk, Gemini reads word-by-word to detect stocks
    3. Handle transcription spelling errors intelligently
    4. Merge all chunks and deduplicate
    5. Final Gemini call for accurate NSE symbols
    6. Output CSV with STOCK NAME, STOCK SYMBOL, START TIME
    """

    print("\n" + "=" * 60)
    print("STEP 8: Extract Stock Mentions (Gemini AI - Chunk-Based)")
    print(f"{'='*60}\n")

    try:
        detected_speakers_file = os.path.join(job_folder, "analysis", "detected_speakers.txt")
        filtered_transcript_file = os.path.join(job_folder, "transcripts", "filtered_transcription.txt")
        output_csv = os.path.join(job_folder, "analysis", "extracted_stocks.csv")
        chunks_folder = os.path.join(job_folder, "analysis", "stock_chunks")

        if not os.path.exists(detected_speakers_file):
            return {'status': 'failed', 'message': 'Detected speakers file not found'}
        if not os.path.exists(filtered_transcript_file):
            return {'status': 'failed', 'message': 'Filtered transcript file not found'}

        print("📖 Reading detected speakers...")
        with open(detected_speakers_file, 'r', encoding='utf-8') as f:
            detected_lines = f.read().strip().splitlines()

        anchor_speaker = detected_lines[0].split(":")[1].strip()
        pradip_speaker = detected_lines[1].split(":")[1].strip()
        print(f"✅ Anchor = {anchor_speaker}, Pradip = {pradip_speaker}\n")

        print("📖 Reading filtered transcription...")
        with open(filtered_transcript_file, 'r', encoding='utf-8') as f:
            transcript_content = f.read().strip()

        lines = parse_transcript_lines(transcript_content)
        print(f"✅ Parsed {len(lines)} transcript lines\n")

        print(f"📊 Splitting transcript into {NUM_CHUNKS} chunks...")
        chunks = split_into_chunks(lines, pradip_speaker, NUM_CHUNKS)
        print(f"✅ Created {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks, 1):
            print(f"   Chunk {i}: {len(chunk)} lines ({chunk[0]['start_time']} - {chunk[-1]['end_time']})")
        print()

        print("🔑 Fetching Gemini API key...")
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key_value FROM api_keys WHERE LOWER(provider) = 'gemini' LIMIT 1"
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            return {'status': 'failed', 'message': 'Gemini API key not found. Please add it in Settings → API Keys → Gemini'}

        genai.configure(api_key=result[0])
        model = genai.GenerativeModel(get_gemini_model())
        print(f"✅ Using Gemini model: {get_gemini_model()}\n")

        os.makedirs(chunks_folder, exist_ok=True)

        print("🔍 Phase 1: Extracting stocks from each chunk (word-by-word analysis)...\n")
        all_chunk_stocks = []

        for i, chunk in enumerate(chunks, 1):
            print(f"   📝 Processing Chunk {i}/{len(chunks)}...")
            
            stocks = extract_stocks_from_chunk(chunk, i, model)
            
            chunk_file = os.path.join(chunks_folder, f"chunk_{i}_stocks.txt")
            with open(chunk_file, 'w', encoding='utf-8') as f:
                for time_str, stock_name in stocks:
                    f.write(f"{time_str} - {stock_name}\n")
            
            print(f"      ✅ Found {len(stocks)} stocks in chunk {i}")
            for time_str, stock_name in stocks[:3]:
                print(f"         • {time_str} - {stock_name}")
            if len(stocks) > 3:
                print(f"         ... and {len(stocks) - 3} more")
            
            all_chunk_stocks.extend(stocks)
            print()

        print(f"\n📊 Total stocks from all chunks: {len(all_chunk_stocks)}")

        print("\n🔄 Phase 2: Merging and deduplicating stocks...")
        merged_stocks = merge_and_deduplicate_stocks(all_chunk_stocks)
        print(f"✅ Unique stocks after merge: {len(merged_stocks)}")

        merged_file = os.path.join(chunks_folder, "merged_stocks.txt")
        with open(merged_file, 'w', encoding='utf-8') as f:
            for time_str, stock_name in merged_stocks:
                f.write(f"{time_str} - {stock_name}\n")

        print("\n🎯 Phase 3: Getting accurate NSE symbols...")
        final_stocks = get_accurate_symbols(merged_stocks, model)
        print(f"✅ Final stocks with symbols: {len(final_stocks)}")

        print("\n📝 Phase 4: Validating and formatting final CSV...")
        csv_content = validate_and_format_csv(final_stocks)

        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        with open(output_csv, "w", encoding="utf-8") as f:
            f.write(csv_content)

        stock_count = max(0, len(csv_content.strip().splitlines()) - 1)
        print(f"✅ Final unique stocks: {stock_count}\n")

        if stock_count > 0:
            print("📋 Final Extracted Stocks:")
            lines = csv_content.strip().splitlines()[1:]
            for line in lines[:10]:
                print(f"   • {line}")
            if stock_count > 10:
                print(f"   ... and {stock_count - 10} more\n")

        return {
            "status": "success",
            "message": f"Extracted {stock_count} stocks using intelligent chunk-based detection",
            "output_files": ["analysis/extracted_stocks.csv", "analysis/stock_chunks/"]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "failed", "message": f"Stock extraction failed: {e}"}


if __name__ == "__main__":
    import sys
    test_folder = sys.argv[1] if len(sys.argv) > 1 else "backend/job_files/test_job"
    result = run(test_folder)
    print(f"\n{'='*60}")
    print(f"Result: {result['status'].upper()}")
    print(f"Message: {result['message']}")
    if 'output_files' in result:
        print(f"Output Files: {result['output_files']}")
    print(f"{'='*60}")
