"""
Transcript Rationale Step 5: Extract Analysis
For each stock, extract Pradip's analysis from the transcript, polish it,
and detect chart type (daily/weekly/monthly)
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


def extract_and_polish_analysis(client, transcript_text, stock_name, stock_symbol):
    """
    Extract Pradip's analysis for a specific stock and polish it
    Also detect chart type mentioned
    """
    prompt = f"""Analyze this transcript to find what MR. PRADIP said about the stock: {stock_name} (Symbol: {stock_symbol})

TASK 1: EXTRACT PRADIP'S ANALYSIS
- Find ONLY what Pradip said about this stock
- Include his views, recommendations, targets, stop loss levels
- Ignore what the anchor or other analysts said

TASK 2: POLISH THE ANALYSIS
- Convert the extracted analysis into professional investment rationale
- Format like a SEBI-registered Research Analyst would write
- Include price targets if mentioned
- Include stop loss if mentioned
- Keep it concise but comprehensive (2-4 sentences)

TASK 3: DETECT CHART TYPE
- If Pradip mentions "daily chart" or "daily timeframe" → DAILY
- If Pradip mentions "weekly chart" or "weekly timeframe" → WEEKLY
- If Pradip mentions "monthly chart" or "monthly timeframe" → MONTHLY
- If not specifically mentioned → DAILY (default)

OUTPUT FORMAT (use exactly this format):
ANALYSIS: [Your polished analysis here]
CHART TYPE: [DAILY/WEEKLY/MONTHLY]

TRANSCRIPT:
{transcript_text[:8000]}

EXTRACT AND POLISH PRADIP'S ANALYSIS FOR {stock_name}:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a SEBI-registered Research Analyst with 15+ years of experience.
You extract stock analysis from transcripts and polish them into professional investment rationales.
Always be accurate and preserve the original recommendations and price targets."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content.strip()
        
        analysis = ""
        chart_type = "DAILY"
        
        lines = result.split('\n')
        for line in lines:
            line = line.strip()
            if line.upper().startswith('ANALYSIS:'):
                analysis = line[9:].strip()
            elif line.upper().startswith('CHART TYPE:'):
                chart_type_raw = line[11:].strip().upper()
                if chart_type_raw in ['DAILY', 'WEEKLY', 'MONTHLY']:
                    chart_type = chart_type_raw
        
        if not analysis:
            analysis = result.replace('CHART TYPE:', '').replace('ANALYSIS:', '').strip()
            if 'WEEKLY' in result.upper():
                chart_type = 'WEEKLY'
            elif 'MONTHLY' in result.upper():
                chart_type = 'MONTHLY'
        
        return analysis, chart_type
        
    except Exception as e:
        print(f"Error extracting analysis for {stock_name}: {str(e)}")
        return f"Analysis pending for {stock_name}", "DAILY"


def run(job_folder):
    """Extract and polish analysis for each stock"""
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 5: EXTRACT & POLISH ANALYSIS")
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
        
        print(f"Reading transcript: {transcript_file}")
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        print(f"Reading mapped stocks: {input_csv}")
        df_input = pd.read_csv(input_csv)
        df_input.columns = df_input.columns.str.strip().str.upper()
        
        print(f"Found {len(df_input)} stocks to process\n")
        
        client = openai.OpenAI(api_key=openai_key)
        
        analyses = []
        chart_types = []
        
        for idx, row in df_input.iterrows():
            stock_name = row.get('INPUT STOCK', row.get('STOCK SYMBOL', ''))
            stock_symbol = row.get('STOCK SYMBOL', row.get('GPT SYMBOL', ''))
            
            print(f"  [{idx+1}/{len(df_input)}] Extracting analysis for: {stock_name} ({stock_symbol})")
            
            analysis, chart_type = extract_and_polish_analysis(
                client, transcript_text, stock_name, stock_symbol
            )
            
            analyses.append(analysis)
            chart_types.append(chart_type)
            
            print(f"    Chart Type: {chart_type}")
            print(f"    Analysis: {analysis[:100]}...")
            
            if idx < len(df_input) - 1:
                time.sleep(0.5)
        
        df_input['ANALYSIS'] = analyses
        df_input['CHART TYPE'] = chart_types
        
        df_input.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        print(f"\nSaved stocks with analysis to: {output_csv}")
        
        return {
            'success': True,
            'output_file': output_csv,
            'stock_count': len(df_input)
        }
        
    except Exception as e:
        print(f"Error in Step 5: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
