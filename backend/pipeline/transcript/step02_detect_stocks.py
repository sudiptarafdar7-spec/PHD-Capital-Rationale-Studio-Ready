"""
Transcript Rationale Step 2: Detect Stocks
Detects stocks discussed ONLY by Mr. Pradip (ignores other speakers)

Logic:
1. First analyze transcript to identify all speakers
2. If only Pradip OR Pradip+Anchor: include ALL stocks discussed
3. If Pradip+Anchor+Other speakers: line-by-line extraction of Pradip's stocks only
4. Validate all stocks against NSE/BSE
5. Fix transcription spelling errors

Output: detected_stocks.csv with INPUT STOCK column
"""

import os
import openai
import pandas as pd
import re
from backend.utils.database import get_db_cursor


COMMON_TRANSCRIPTION_ERRORS = {
    "SUZUELON": "SUZLON",
    "SUJALAN": "SUZLON",
    "SUZALON": "SUZLON",
    "SUZLON ENERGY": "SUZLON",
    "ADANI POWER": "ADANIPOWER",
    "ADANI GREEN": "ADANIGREEN",
    "ADANI ENTERPRISE": "ADANIENT",
    "ADANI ENTERPRISES": "ADANIENT",
    "TATA MOTOR": "TATAMOTORS",
    "TATA MOTORS": "TATAMOTORS",
    "TATA STEEL": "TATASTEEL",
    "TATA POWER": "TATAPOWER",
    "HDFC BANK": "HDFCBANK",
    "ICICI BANK": "ICICIBANK",
    "AXIS BANK": "AXISBANK",
    "KOTAK BANK": "KOTAKBANK",
    "KOTAK MAHINDRA": "KOTAKBANK",
    "SBI BANK": "SBIN",
    "STATE BANK": "SBIN",
    "STATE BANK OF INDIA": "SBIN",
    "RELIANCE INDUSTRIES": "RELIANCE",
    "RELIANCE IND": "RELIANCE",
    "RIL": "RELIANCE",
    "INFOSYS LTD": "INFY",
    "INFOSYS TECHNOLOGIES": "INFY",
    "TCS": "TCS",
    "WIPRO LTD": "WIPRO",
    "HCL TECH": "HCLTECH",
    "TECH MAHINDRA": "TECHM",
    "L&T": "LT",
    "LARSEN": "LT",
    "LARSEN AND TOUBRO": "LT",
    "LARSEN & TOUBRO": "LT",
    "BHEL": "BHEL",
    "NTPC LTD": "NTPC",
    "POWER GRID": "POWERGRID",
    "COAL INDIA": "COALINDIA",
    "ONGC": "ONGC",
    "IOC": "IOC",
    "BPCL": "BPCL",
    "HPCL": "HPCL",
    "GAIL": "GAIL",
    "ITC LTD": "ITC",
    "HINDUSTAN UNILEVER": "HINDUNILVR",
    "HUL": "HINDUNILVR",
    "BAJAJ FINANCE": "BAJFINANCE",
    "BAJAJ FINSERV": "BAJAJFINSV",
    "MARUTI SUZUKI": "MARUTI",
    "MARUTI": "MARUTI",
    "M&M": "M&M",
    "MAHINDRA": "M&M",
    "HERO MOTOCORP": "HEROMOTOCO",
    "HERO MOTOR": "HEROMOTOCO",
    "BAJAJ AUTO": "BAJAJ-AUTO",
    "EICHER MOTORS": "EICHERMOT",
    "EICHER": "EICHERMOT",
    "BHARTI AIRTEL": "BHARTIARTL",
    "AIRTEL": "BHARTIARTL",
    "VODAFONE IDEA": "IDEA",
    "VODAFONE": "IDEA",
    "PUNJAB NATIONAL": "PNB",
    "PUNJAB NATIONAL BANK": "PNB",
    "CANARA BANK": "CANBK",
    "BANK OF BARODA": "BANKBARODA",
    "INDIAN BANK": "INDIANB",
    "INDIAN OVERSEAS": "IOB",
    "UCO BANK": "UCOBANK",
    "CENTRAL BANK": "CENTRALBK",
    "UNION BANK": "UNIONBANK",
    "ZOMATO": "ZOMATO",
    "PAYTM": "PAYTM",
    "NYKAA": "NYKAA",
    "FSN E-COMMERCE": "NYKAA",
    "POLYCAB": "POLYCAB",
    "POLYCAB INDIA": "POLYCAB",
    "DIXON": "DIXON",
    "DIXON TECHNOLOGIES": "DIXON",
    "HAL": "HAL",
    "HINDUSTAN AERONAUTICS": "HAL",
    "BEL": "BEL",
    "BHARAT ELECTRONICS": "BEL",
    "MAZAGON DOCK": "MAZDOCK",
    "COCHIN SHIPYARD": "COCHINSHIP",
    "GARDEN REACH": "GRSE",
    "RAILWAYS": "IRFC",
    "IRFC": "IRFC",
    "RVNL": "RVNL",
    "RAIL VIKAS": "RVNL",
    "IRCTC": "IRCTC",
    "CERA BANK": "CERA",
    "CERA SANITARYWARE": "CERA",
    "JSW STEEL": "JSWSTEEL",
    "JSW ENERGY": "JSWENERGY",
    "SAIL": "SAIL",
    "STEEL AUTHORITY": "SAIL",
    "HINDALCO": "HINDALCO",
    "VEDANTA": "VEDL",
    "VEDANTA LTD": "VEDL",
    "TATA ELXSI": "TATAELXSI",
    "PERSISTENT": "PERSISTENT",
    "PERSISTENT SYSTEMS": "PERSISTENT",
    "HAPPIEST MINDS": "HAPPSTMNDS",
    "MPHASIS": "MPHASIS",
    "COFORGE": "COFORGE",
    "LTIM": "LTIM",
    "LTI MINDTREE": "LTIM",
    "CYIENT": "CYIENT",
    "ZENSAR": "ZENSARTECH",
    "BIRLASOFT": "BSOFT",
    "SONATA SOFTWARE": "SONATSOFTW",
    "INTELLECT DESIGN": "INTELLECT",
    "HFCL": "HFCL",
    "PUNJAB AND SIND": "PSB",
    "PUNJAB SIND BANK": "PSB",
    "PUNJAB SIND": "PSB",
    "OLECTRA": "OLECTRA",
    "OLECTRA GREENTECH": "OLECTRA",
    "JBM AUTO": "JBMA",
    "TATA COMMUNICATIONS": "TATACOMM",
    "TATA COMM": "TATACOMM",
    "VODAFONE": "IDEA",
    "JIOFINANCIAL": "JIOFIN",
    "JIO FINANCIAL": "JIOFIN",
}


def get_openai_key():
    """Get OpenAI API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'openai'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def fix_transcription_error(stock_name):
    """Fix common transcription errors in stock names"""
    stock_upper = stock_name.upper().strip()
    if stock_upper in COMMON_TRANSCRIPTION_ERRORS:
        return COMMON_TRANSCRIPTION_ERRORS[stock_upper]
    return stock_upper


def analyze_speakers(client, transcript_text):
    """
    Analyze transcript to identify all speakers
    Returns: dict with speaker_count, has_other_speakers, speaker_list
    """
    prompt = f"""Analyze this financial transcript to identify ALL speakers.

TASK: List all the speakers/participants in this transcript.

Common patterns:
- "ANCHOR" or "HOST" - the interviewer
- "PRADIP" or "MR. PRADIP" or "PRADIP HOTCHANDANI" - the main analyst
- "CALLER" - phone callers asking questions
- Other analyst names

OUTPUT FORMAT:
SPEAKERS: [comma-separated list of speaker names/roles]
HAS_OTHER_SPEAKERS: [YES if there are speakers other than Pradip and Anchor, NO otherwise]

TRANSCRIPT (first 5000 chars):
{transcript_text[:5000]}

ANALYZE SPEAKERS:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You analyze transcripts to identify speakers. Be accurate in identifying all participants."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        result = response.choices[0].message.content.strip()
        
        speakers = []
        has_other_speakers = False
        
        for line in result.split('\n'):
            line = line.strip()
            if line.upper().startswith('SPEAKERS:'):
                speakers_str = line[9:].strip()
                speakers = [s.strip() for s in speakers_str.split(',')]
            elif line.upper().startswith('HAS_OTHER_SPEAKERS:'):
                has_other = line[19:].strip().upper()
                has_other_speakers = 'YES' in has_other
        
        return {
            'speakers': speakers,
            'has_other_speakers': has_other_speakers,
            'speaker_count': len(speakers)
        }
        
    except Exception as e:
        print(f"Error analyzing speakers: {str(e)}")
        return {
            'speakers': ['PRADIP', 'ANCHOR'],
            'has_other_speakers': False,
            'speaker_count': 2
        }


def detect_stocks_simple_mode(client, transcript_text):
    """
    Simple mode: Only Pradip or Pradip+Anchor
    Include ALL stocks discussed in the transcript
    """
    prompt = f"""You are analyzing a financial transcript where the ONLY participants are:
- An Anchor/Host who asks questions
- Mr. Pradip (Pradip Hotchandani) who provides stock analysis

Since there are NO other speakers, ALL stocks discussed in this transcript are relevant.

TASK: Extract ALL stock names mentioned in this transcript.

CRITICAL RULES:
1. Extract every single stock/company name mentioned
2. Include stocks the anchor asks about AND stocks Pradip discusses
3. Only include REAL NSE/BSE listed Indian stocks
4. DO NOT include fake/invalid/made-up stock names
5. Fix any obvious transcription spelling errors (e.g., "Suzuelon" → "Suzlon")
6. Include indices like NIFTY, BANK NIFTY if discussed

VALIDATION:
- Each stock must be a real company listed on NSE or BSE
- Common stocks: RELIANCE, TATA MOTORS, HDFC BANK, INFOSYS, TCS, ICICI BANK, etc.
- If unsure about a stock name, DO NOT include it

OUTPUT FORMAT:
Return ONLY a comma-separated list of valid stock names.
Example: RELIANCE, TATAMOTORS, HDFCBANK, SUZLON, POLYCAB

If no valid stocks found, return: NONE

FULL TRANSCRIPT:
{transcript_text}

VALID STOCKS MENTIONED:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert at identifying Indian stock names from transcripts.
You ONLY return REAL NSE/BSE listed stocks.
You NEVER return fake, invalid, or made-up stock names.
You fix common transcription spelling errors (Suzuelon→Suzlon, etc.)."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=3000
        )
        
        result = response.choices[0].message.content.strip()
        
        if result.upper() == 'NONE' or not result:
            return []
        
        stocks = [s.strip().upper() for s in result.split(',')]
        stocks = [s for s in stocks if s and s != 'NONE' and len(s) > 1]
        
        return stocks
        
    except Exception as e:
        print(f"Error detecting stocks (simple mode): {str(e)}")
        return []


def detect_stocks_strict_mode(client, transcript_text):
    """
    Strict mode: Pradip + Anchor + Other speakers
    Go line by line, only include stocks Pradip discusses
    Understand anchor questions directed at Pradip and include those stocks
    """
    prompt = f"""You are analyzing a financial transcript with MULTIPLE speakers including:
- An Anchor/Host who asks questions
- Mr. Pradip (Pradip Hotchandani) who is the main analyst
- OTHER speakers (callers, other analysts, etc.)

CRITICAL: We ONLY want stocks that MR. PRADIP discussed or analyzed.

EXTRACTION LOGIC:
1. Go through the transcript LINE BY LINE
2. Identify who is speaking in each segment
3. When the Anchor asks Pradip about a stock → Include that stock
4. When Pradip gives his view/analysis on a stock → Include that stock
5. IGNORE stocks mentioned by other analysts, callers, or speakers
6. IGNORE stocks discussed by speakers other than Pradip

VALIDATION RULES:
1. Only include REAL NSE/BSE listed Indian stocks
2. DO NOT include fake/invalid/made-up stock names
3. Fix transcription spelling errors (e.g., "Suzuelon" → "Suzlon")
4. If unsure if a name is a valid stock, DO NOT include it

EXAMPLES OF WHAT TO INCLUDE:
- Anchor: "Pradip, what about Reliance?" → Pradip responds → INCLUDE RELIANCE
- Pradip: "I like Tata Motors here..." → INCLUDE TATAMOTORS
- Pradip: "Suzlon looks good for..." → INCLUDE SUZLON

EXAMPLES OF WHAT TO EXCLUDE:
- Other Analyst: "I think HDFC is good" → EXCLUDE (not Pradip)
- Caller: "What about Infosys?" → Pradip says "Not my area" → EXCLUDE
- Random mention by caller with no Pradip analysis → EXCLUDE

OUTPUT FORMAT:
Return ONLY a comma-separated list of valid stock names that PRADIP discussed.
Example: RELIANCE, TATAMOTORS, SUZLON, POLYCAB

If no stocks discussed by Pradip, return: NONE

FULL TRANSCRIPT:
{transcript_text}

STOCKS DISCUSSED BY PRADIP ONLY:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert at analyzing financial transcripts with multiple speakers.
Your job is to extract ONLY stocks discussed by MR. PRADIP, ignoring other speakers.
You ONLY return REAL NSE/BSE listed stocks.
You fix transcription spelling errors.
You NEVER include stocks from other analysts or callers."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=3000
        )
        
        result = response.choices[0].message.content.strip()
        
        if result.upper() == 'NONE' or not result:
            return []
        
        stocks = [s.strip().upper() for s in result.split(',')]
        stocks = [s for s in stocks if s and s != 'NONE' and len(s) > 1]
        
        return stocks
        
    except Exception as e:
        print(f"Error detecting stocks (strict mode): {str(e)}")
        return []


def validate_and_fix_stocks(client, stocks_list):
    """
    Validate stocks against NSE/BSE and fix any remaining errors
    """
    if not stocks_list:
        return []
    
    fixed_stocks = []
    for stock in stocks_list:
        fixed = fix_transcription_error(stock)
        fixed_stocks.append(fixed)
    
    stocks_str = ', '.join(fixed_stocks)
    
    prompt = f"""You are a stock market expert. Validate these stock names and fix any errors.

STOCKS TO VALIDATE:
{stocks_str}

TASK:
1. Check each stock name - is it a REAL NSE/BSE listed company?
2. Fix any spelling errors or transcription mistakes
3. Convert to proper NSE trading symbol format
4. REMOVE any fake/invalid/non-existent stocks
5. REMOVE indices like NIFTY, BANK NIFTY, SENSEX (we only want stocks)

COMMON FIXES:
- TATA MOTORS → TATAMOTORS
- HDFC BANK → HDFCBANK
- RELIANCE INDUSTRIES → RELIANCE
- STATE BANK → SBIN
- L&T → LT
- Suzuelon/Sujalan → SUZLON

OUTPUT FORMAT:
Return ONLY valid NSE trading symbols, comma-separated.
Example: RELIANCE, TATAMOTORS, HDFCBANK, SUZLON

VALIDATED STOCKS:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an NSE/BSE stock market expert. You validate and fix stock symbols. You ONLY return real, valid trading symbols."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        
        if not result or result.upper() == 'NONE':
            return fixed_stocks
        
        validated = [s.strip().upper() for s in result.split(',')]
        validated = [s for s in validated if s and s != 'NONE' and len(s) > 1]
        
        return validated if validated else fixed_stocks
        
    except Exception as e:
        print(f"Error validating stocks: {str(e)}")
        return fixed_stocks


def run(job_folder):
    """
    Detect all stocks discussed by Mr. Pradip in the transcript
    
    Logic:
    1. Analyze speakers in transcript
    2. If only Pradip/Anchor: include all stocks (simple mode)
    3. If other speakers present: extract only Pradip's stocks (strict mode)
    4. Validate and fix all stock names
    """
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 2: DETECT PRADIP'S STOCKS")
    print(f"{'='*60}\n")
    
    try:
        input_file = os.path.join(job_folder, 'transcript-input-english.txt')
        analysis_folder = os.path.join(job_folder, 'analysis')
        os.makedirs(analysis_folder, exist_ok=True)
        output_file = os.path.join(analysis_folder, 'detected_stocks.csv')
        
        if not os.path.exists(input_file):
            return {
                'success': False,
                'error': f'Translated input file not found: {input_file}'
            }
        
        openai_key = get_openai_key()
        if not openai_key:
            return {
                'success': False,
                'error': 'OpenAI API key not found. Please add it in Settings → API Keys.'
            }
        
        print(f"📄 Reading transcript: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        print(f"   Transcript length: {len(transcript_text)} characters\n")
        
        client = openai.OpenAI(api_key=openai_key)
        
        print("🔍 Step 1: Analyzing speakers in transcript...")
        speaker_info = analyze_speakers(client, transcript_text)
        print(f"   Speakers found: {speaker_info['speakers']}")
        print(f"   Has other speakers (besides Pradip/Anchor): {speaker_info['has_other_speakers']}\n")
        
        if speaker_info['has_other_speakers']:
            print("📋 Step 2: Using STRICT MODE (multiple speakers detected)")
            print("   Only extracting stocks discussed by Mr. Pradip...\n")
            raw_stocks = detect_stocks_strict_mode(client, transcript_text)
        else:
            print("📋 Step 2: Using SIMPLE MODE (only Pradip/Anchor)")
            print("   Extracting all stocks from transcript...\n")
            raw_stocks = detect_stocks_simple_mode(client, transcript_text)
        
        print(f"   Raw stocks detected: {len(raw_stocks)}")
        if raw_stocks:
            print(f"   {raw_stocks[:10]}{'...' if len(raw_stocks) > 10 else ''}\n")
        
        print("✅ Step 3: Validating and fixing stock names...")
        validated_stocks = validate_and_fix_stocks(client, raw_stocks)
        
        unique_stocks = []
        seen = set()
        for stock in validated_stocks:
            stock_clean = stock.upper().strip()
            stock_clean = re.sub(r'[^A-Z0-9&-]', '', stock_clean)
            if stock_clean and stock_clean not in seen and len(stock_clean) > 1:
                seen.add(stock_clean)
                unique_stocks.append(stock_clean)
        
        print(f"   Validated stocks: {len(unique_stocks)}")
        print(f"   Final list: {unique_stocks}\n")
        
        df = pd.DataFrame({'INPUT STOCK': unique_stocks})
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"💾 Saved to: {output_file}")
        
        return {
            'success': True,
            'output_file': output_file,
            'stock_count': len(unique_stocks),
            'mode': 'strict' if speaker_info['has_other_speakers'] else 'simple',
            'speakers': speaker_info['speakers']
        }
        
    except Exception as e:
        print(f"❌ Error in Step 2: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
