"""
Transcript Rationale Step 5: Extract Analysis
For each stock, extract analysis based on speaker detection:
- If only Pradip/Anchor: directly take analysis from transcript
- If other speakers present: line-by-line, only Pradip's analysis
Output: stocks_with_analysis.csv
"""

import os
import re
import openai
import pandas as pd
import time
from backend.utils.database import get_db_cursor


def get_openai_key():
    """Get OpenAI API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'openai'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def analyze_speakers(client, transcript_text):
    """
    Analyze transcript to identify all speakers
    Returns: dict with has_other_speakers flag
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
            'has_other_speakers': has_other_speakers
        }
        
    except Exception as e:
        print(f"Error analyzing speakers: {str(e)}")
        return {
            'speakers': ['PRADIP', 'ANCHOR'],
            'has_other_speakers': False
        }


def extract_analysis_simple_mode(client, transcript_text, stock_name, stock_symbol):
    """
    Simple mode: Only Pradip or Pradip+Anchor
    Directly extract analysis for the stock from the entire transcript
    """
    prompt = f"""You are analyzing a financial transcript where the ONLY participants are an Anchor and Mr. Pradip.
Since there are NO other speakers, all analysis in the transcript is from Pradip.

STOCK TO FIND: {stock_name} (Symbol: {stock_symbol})

TASK: Extract the complete analysis for this stock from the transcript.

EXTRACTION REQUIREMENTS:
- Entry price/levels mentioned
- Target prices mentioned
- Stop loss levels mentioned
- Holding period if mentioned
- Views and recommendations
- Chart timeframe (daily/weekly/monthly) if mentioned

OUTPUT FORMAT:
ANALYSIS: [Complete analysis for this stock]
CHART_TYPE: [DAILY/WEEKLY/MONTHLY - default DAILY if not specified]

If the stock is not discussed in the transcript, return:
ANALYSIS: NOT FOUND
CHART_TYPE: DAILY

FULL TRANSCRIPT:
{transcript_text}

EXTRACT ANALYSIS FOR {stock_name}:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You extract stock analysis from financial transcripts.
Be accurate and preserve all price targets, stop losses, and recommendations exactly as stated.
If the stock is not discussed, clearly state "NOT FOUND"."""
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
        return parse_analysis_response(result)
        
    except Exception as e:
        print(f"    Error extracting analysis (simple): {str(e)}")
        return "ERROR", "DAILY"


def extract_analysis_strict_mode(client, transcript_text, stock_name, stock_symbol):
    """
    Strict mode: Pradip + Anchor + Other speakers
    Go line by line, understand questions, extract ONLY Pradip's analysis
    """
    prompt = f"""You are analyzing a financial transcript with MULTIPLE speakers including:
- An Anchor/Host who asks questions
- Mr. Pradip (Pradip Hotchandani) who is the main analyst
- OTHER speakers (callers, other analysts, etc.)

STOCK TO FIND: {stock_name} (Symbol: {stock_symbol})

CRITICAL: We ONLY want analysis from MR. PRADIP for this stock.

EXTRACTION LOGIC:
1. Go through the transcript LINE BY LINE
2. Identify who is speaking in each segment
3. Find where the Anchor asks about this stock
4. Extract ONLY what Pradip says in response
5. IGNORE analysis from other analysts, callers, or speakers

WHAT TO INCLUDE:
- Pradip's entry levels for this stock
- Pradip's target prices for this stock
- Pradip's stop loss levels for this stock
- Pradip's holding period recommendation
- Pradip's views and analysis
- Chart timeframe Pradip mentions

WHAT TO EXCLUDE:
- Any analysis from other analysts
- Caller's opinions
- Anchor's personal views
- Generic market commentary not about this stock

OUTPUT FORMAT:
ANALYSIS: [Pradip's complete analysis for this stock, or "NOT FOUND" if he didn't discuss it]
CHART_TYPE: [DAILY/WEEKLY/MONTHLY - based on what Pradip mentioned, default DAILY]

FULL TRANSCRIPT:
{transcript_text}

EXTRACT PRADIP'S ANALYSIS FOR {stock_name}:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You analyze financial transcripts with multiple speakers.
Your job is to extract ONLY what MR. PRADIP said about a specific stock.
NEVER include analysis from other speakers.
Be accurate and preserve all price targets and recommendations."""
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
        return parse_analysis_response(result)
        
    except Exception as e:
        print(f"    Error extracting analysis (strict): {str(e)}")
        return "ERROR", "DAILY"


def parse_analysis_response(result):
    """Parse the GPT response to extract analysis and chart type"""
    analysis = ""
    chart_type = "DAILY"
    
    lines = result.split('\n')
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.upper().startswith('ANALYSIS:'):
            analysis = line_stripped[9:].strip()
        elif line_stripped.upper().startswith('CHART_TYPE:'):
            chart_type_raw = line_stripped[11:].strip().upper()
            if chart_type_raw in ['DAILY', 'WEEKLY', 'MONTHLY']:
                chart_type = chart_type_raw
    
    if not analysis:
        for line in lines:
            if 'NOT FOUND' in line.upper():
                return "NOT FOUND", "DAILY"
        analysis = result
    
    return analysis, chart_type


def polish_analysis(client, stock_name, original_analysis):
    """
    Polish extracted analysis into professional format.
    """
    if not original_analysis or original_analysis in ["NOT FOUND", "ERROR", ""]:
        return original_analysis
    
    prompt = f"""You are a SEBI-registered Research Analyst with 15+ years of experience in Indian equity markets. 
Polish the following stock analysis to make it professional and well-structured.

STOCK NAME: {stock_name}

ORIGINAL ANALYSIS:
{original_analysis}

FORMATTING RULES:
1. Start with "For {stock_name}, ..." 
2. Include entry point, target prices, and stop-loss levels if mentioned for THIS STOCK
3. Include holding period recommendation if mentioned
4. Include risk factors or caveats if mentioned
5. Use ₹ symbol for all prices (e.g., ₹150, ₹1,250)
6. Convert spoken numbers to digits (e.g., "one fifty" → ₹150, "twelve hundred" → ₹1,200)
7. Minimum 100 words
8. Simple, professional English
9. NO first-person pronouns (I, We, Our) - use passive voice or "the view is..."
10. NO speaker names in the analysis

CRITICAL RULES:
- Do NOT change any price values, targets, stop-loss, or numerical data for {stock_name}
- Do NOT invent new information - only polish what is given
- Keep all technical levels and recommendations exactly as stated
- Just restructure and professionalize the language
- **IMPORTANT**: If the original analysis mentions MULTIPLE stocks, extract ONLY the information relevant to {stock_name}. 
  - Remove mentions of other stocks and their specific levels
  - Keep only the targets, stop-loss, and analysis that applies to {stock_name}
  - If the analysis is shared/generic, adapt it to focus on {stock_name} only

Return ONLY the polished analysis text, nothing else."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional financial writer. Polish stock analyses to be professional, clear, and well-structured. Never change numerical values or invent information. Always use ₹ for Indian Rupee prices."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        polished = response.choices[0].message.content.strip()
        return polished
        
    except Exception as e:
        print(f"    Error polishing analysis: {str(e)}")
        return original_analysis


def search_stock_in_transcript(transcript_text, stock_name, stock_symbol):
    """Search for stock mentions in the transcript"""
    transcript_upper = transcript_text.upper()
    stock_name_upper = stock_name.upper().strip()
    stock_symbol_upper = stock_symbol.upper().strip()
    
    found = False
    
    if stock_name_upper and stock_name_upper in transcript_upper:
        found = True
    if stock_symbol_upper and stock_symbol_upper in transcript_upper:
        found = True
    
    name_parts = stock_name_upper.split()
    for part in name_parts:
        if len(part) >= 4 and part in transcript_upper:
            found = True
            break
    
    return found


def run(job_folder):
    """Extract and polish analysis for each stock based on speaker detection"""
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 5: EXTRACT ANALYSIS")
    print(f"{'='*60}\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        input_csv = os.path.join(analysis_folder, 'mapped_master_file.csv')
        transcript_file = os.path.join(job_folder, 'transcript-input-english.txt')
        output_csv = os.path.join(analysis_folder, 'stocks_with_analysis.csv')
        
        if not os.path.exists(input_csv):
            return {
                'success': False,
                'error': f'Mapped master file not found: {input_csv}'
            }
        
        if not os.path.exists(transcript_file):
            return {
                'success': False,
                'error': f'Translated transcript not found: {transcript_file}'
            }
        
        openai_key = get_openai_key()
        if not openai_key:
            return {
                'success': False,
                'error': 'OpenAI API key not found. Please add it in Settings → API Keys.'
            }
        
        print(f"📄 Reading transcript: {transcript_file}")
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        print(f"   Transcript length: {len(transcript_text)} characters\n")
        
        print(f"📋 Reading mapped stocks: {input_csv}")
        df_input = pd.read_csv(input_csv)
        df_input.columns = df_input.columns.str.strip().str.upper()
        print(f"   Found {len(df_input)} stocks to process\n")
        
        client = openai.OpenAI(api_key=openai_key)
        
        print("🔍 Step 1: Analyzing speakers in transcript...")
        speaker_info = analyze_speakers(client, transcript_text)
        print(f"   Speakers found: {speaker_info['speakers']}")
        print(f"   Has other speakers: {speaker_info['has_other_speakers']}\n")
        
        if speaker_info['has_other_speakers']:
            print("📋 Using STRICT MODE: Multiple speakers detected")
            print("   Will extract ONLY Pradip's analysis for each stock\n")
            extraction_mode = "strict"
        else:
            print("📋 Using SIMPLE MODE: Only Pradip/Anchor")
            print("   Will directly extract analysis from transcript\n")
            extraction_mode = "simple"
        
        analyses = []
        chart_types = []
        found_in_transcript = []
        
        print("=" * 100)
        print(f"{'#':<4} {'INPUT STOCK':<30} {'FOUND':<8} {'STATUS':<55}")
        print("=" * 100)
        
        for idx, row in df_input.iterrows():
            stock_name = str(row.get('INPUT STOCK', row.get('STOCK SYMBOL', ''))).strip()
            stock_symbol = str(row.get('STOCK SYMBOL', row.get('GPT SYMBOL', ''))).strip()
            
            is_found = search_stock_in_transcript(transcript_text, stock_name, stock_symbol)
            found_in_transcript.append("YES" if is_found else "NO")
            
            if is_found:
                if extraction_mode == "simple":
                    raw_analysis, chart_type = extract_analysis_simple_mode(
                        client, transcript_text, stock_name, stock_symbol
                    )
                else:
                    raw_analysis, chart_type = extract_analysis_strict_mode(
                        client, transcript_text, stock_name, stock_symbol
                    )
                
                if raw_analysis and raw_analysis not in ["NOT FOUND", "ERROR"]:
                    polished_analysis = polish_analysis(client, stock_name, raw_analysis)
                    analyses.append(polished_analysis)
                    chart_types.append(chart_type)
                    status = polished_analysis[:50] + "..." if len(polished_analysis) > 50 else polished_analysis
                else:
                    analyses.append(f"Analysis pending for {stock_name}")
                    chart_types.append("DAILY")
                    status = "No specific analysis found"
            else:
                analyses.append(f"Stock not found in transcript: {stock_name}")
                chart_types.append("DAILY")
                status = "Not in transcript"
            
            print(f"{idx+1:<4} {stock_name[:28]:<30} {'YES' if is_found else 'NO':<8} {status[:55]}")
            
            if idx < len(df_input) - 1:
                time.sleep(0.5)
        
        print("=" * 100)
        
        df_input['ANALYSIS'] = analyses
        df_input['CHART TYPE'] = chart_types
        df_input['FOUND IN TRANSCRIPT'] = found_in_transcript
        
        df_input.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        found_count = sum(1 for f in found_in_transcript if f == "YES")
        with_analysis = sum(1 for a in analyses if not a.startswith("Stock not found") and not a.startswith("Analysis pending"))
        
        print(f"\n📊 Summary:")
        print(f"   Mode used: {extraction_mode.upper()}")
        print(f"   Total stocks: {len(df_input)}")
        print(f"   Found in transcript: {found_count}")
        print(f"   With analysis: {with_analysis}")
        print(f"\n💾 Saved to: {output_csv}")
        
        return {
            'success': True,
            'output_file': output_csv,
            'stock_count': len(df_input),
            'found_count': found_count,
            'analysis_count': with_analysis,
            'mode': extraction_mode
        }
        
    except Exception as e:
        print(f"❌ Error in Step 5: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
