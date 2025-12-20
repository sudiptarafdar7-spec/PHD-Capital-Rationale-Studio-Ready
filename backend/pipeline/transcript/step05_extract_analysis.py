"""
Transcript Rationale Step 5: Extract Analysis
Simple approach: For each INPUT STOCK, find and extract analysis from transcript
Output: stocks_with_analysis.csv
"""

import os
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


def extract_and_polish_analysis(client, transcript_text, stock_name):
    """
    Simple extraction: Find analysis for stock and polish it
    """
    prompt = f"""You are a SEBI-registered Research Analyst with 15+ years of experience in Indian equity markets.

Search this transcript for any discussion about: {stock_name}

TASK:
1. Find ALL mentions and analysis of {stock_name} in the transcript
2. Extract the complete analysis including targets, stop-loss, recommendations
3. Polish it into professional format

FORMATTING RULES:
1. Start with "For {stock_name}, ..." 
2. Include entry point, target prices, and stop-loss levels if mentioned
3. Include holding period recommendation if mentioned
4. Include risk factors or caveats if mentioned
5. Use ₹ symbol for all prices (e.g., ₹150, ₹1,250)
6. Convert spoken numbers to digits (e.g., "one fifty" → ₹150)
7. Minimum 100 words
8. Simple, professional English
9. NO first-person pronouns (I, We, Our) - use passive voice
10. NO speaker names in the analysis

CRITICAL RULES:
- Do NOT change any price values, targets, stop-loss, or numerical data
- Do NOT invent new information - only polish what is found
- Keep all technical levels and recommendations exactly as stated
- If the stock is NOT mentioned in transcript, return exactly: NOT_FOUND

CHART TYPE DETECTION:
- If "daily chart" or "daily timeframe" mentioned → DAILY
- If "weekly chart" or "weekly timeframe" mentioned → WEEKLY  
- If "monthly chart" or "monthly timeframe" mentioned → MONTHLY
- Default → DAILY

OUTPUT FORMAT:
ANALYSIS: [Your polished analysis starting with "For {stock_name}, ..." OR "NOT_FOUND"]
CHART_TYPE: [DAILY/WEEKLY/MONTHLY]

TRANSCRIPT:
{transcript_text}

FIND AND POLISH ANALYSIS FOR {stock_name}:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional financial writer. Extract and polish stock analyses from transcripts. Never invent information. Use ₹ for prices."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=1500
        )
        
        result = response.choices[0].message.content.strip()
        
        analysis = ""
        chart_type = "DAILY"
        
        for line in result.split('\n'):
            line = line.strip()
            if line.upper().startswith('ANALYSIS:'):
                analysis = line[9:].strip()
            elif line.upper().startswith('CHART_TYPE:'):
                ct = line[11:].strip().upper()
                if ct in ['DAILY', 'WEEKLY', 'MONTHLY']:
                    chart_type = ct
        
        if not analysis:
            if 'NOT_FOUND' in result.upper():
                return "NOT_FOUND", "DAILY"
            analysis = result.replace('CHART_TYPE:', '').replace('ANALYSIS:', '').strip()
        
        return analysis, chart_type
        
    except Exception as e:
        print(f"    Error: {str(e)}")
        return "ERROR", "DAILY"


def run(job_folder):
    """Extract and polish analysis for each stock"""
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 5: EXTRACT ANALYSIS (SIMPLE)")
    print(f"{'='*60}\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        input_csv = os.path.join(analysis_folder, 'mapped_master_file.csv')
        transcript_file = os.path.join(job_folder, 'transcript-input-english.txt')
        output_csv = os.path.join(analysis_folder, 'stocks_with_analysis.csv')
        
        if not os.path.exists(input_csv):
            return {'success': False, 'error': f'Mapped master file not found: {input_csv}'}
        
        if not os.path.exists(transcript_file):
            return {'success': False, 'error': f'Transcript not found: {transcript_file}'}
        
        openai_key = get_openai_key()
        if not openai_key:
            return {'success': False, 'error': 'OpenAI API key not found'}
        
        print(f"📄 Reading transcript...")
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        print(f"   Length: {len(transcript_text)} chars\n")
        
        print(f"📋 Reading stocks...")
        df = pd.read_csv(input_csv)
        df.columns = df.columns.str.strip().str.upper()
        print(f"   {len(df)} stocks to process\n")
        
        client = openai.OpenAI(api_key=openai_key)
        
        analyses = []
        chart_types = []
        found_count = 0
        
        print("=" * 80)
        for idx, row in df.iterrows():
            stock_name = str(row.get('INPUT STOCK', row.get('STOCK SYMBOL', ''))).strip()
            
            print(f"[{idx+1}/{len(df)}] {stock_name}...", end=" ")
            
            analysis, chart_type = extract_and_polish_analysis(client, transcript_text, stock_name)
            
            if analysis and analysis != "NOT_FOUND" and analysis != "ERROR":
                analyses.append(analysis)
                chart_types.append(chart_type)
                found_count += 1
                print(f"✅ Found ({chart_type})")
            else:
                analyses.append(f"Analysis not found for {stock_name}")
                chart_types.append("DAILY")
                print("❌ Not found")
            
            time.sleep(0.3)
        
        print("=" * 80)
        
        df['ANALYSIS'] = analyses
        df['CHART TYPE'] = chart_types
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        print(f"\n📊 Results: {found_count}/{len(df)} stocks with analysis")
        print(f"💾 Saved to: {output_csv}")
        
        return {
            'success': True,
            'output_file': output_csv,
            'stock_count': len(df),
            'analysis_count': found_count
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
