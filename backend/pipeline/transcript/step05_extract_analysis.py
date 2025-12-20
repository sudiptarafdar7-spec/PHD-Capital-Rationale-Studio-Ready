"""
Transcript Rationale Step 5: Extract Analysis
For each stock, search the entire transcript for the INPUT STOCK,
extract ONLY Pradip's analysis (not other speakers), polish it,
and detect chart type (daily/weekly/monthly)
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


def search_stock_in_transcript(transcript_text, stock_name, stock_symbol):
    """
    Search for stock mentions in the entire transcript.
    Returns True if found, along with relevant context.
    """
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


def extract_pradip_analysis(client, transcript_text, stock_name, stock_symbol):
    """
    Extract STRICTLY Pradip's analysis for a specific stock.
    Searches the ENTIRE transcript and only extracts what Pradip said.
    """
    prompt = f"""You are analyzing a financial transcript to extract stock analysis.

STOCK TO FIND: {stock_name} (Symbol: {stock_symbol})

CRITICAL RULES:
1. Search the ENTIRE transcript for mentions of "{stock_name}" or "{stock_symbol}"
2. Extract ONLY what MR. PRADIP said about this stock
3. DO NOT include analysis from anchors, hosts, or other speakers
4. DO NOT include what callers or other analysts said
5. If Pradip did not speak about this stock, return "NOT FOUND"

EXTRACTION REQUIREMENTS:
- Entry price/levels if Pradip mentioned
- Target prices if Pradip mentioned  
- Stop loss levels if Pradip mentioned
- Holding period if Pradip mentioned
- His view/recommendation if Pradip mentioned
- Chart timeframe (daily/weekly/monthly) if Pradip mentioned

OUTPUT FORMAT:
PRADIP_ANALYSIS: [Extract exactly what Pradip said about this stock, or "NOT FOUND" if he didn't mention it]
CHART_TYPE: [DAILY/WEEKLY/MONTHLY - based on what Pradip mentioned, default DAILY if not specified]

FULL TRANSCRIPT:
{transcript_text}

NOW EXTRACT PRADIP'S ANALYSIS FOR {stock_name}:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are analyzing financial transcripts. Your ONLY job is to find and extract what MR. PRADIP specifically said about a given stock.
NEVER include analysis from other speakers like anchors, callers, or other analysts.
If Pradip did not mention the stock, clearly state "NOT FOUND".
Be accurate and preserve all price targets, stop losses, and recommendations exactly as Pradip stated them."""
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
        
        pradip_analysis = ""
        chart_type = "DAILY"
        
        lines = result.split('\n')
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.upper().startswith('PRADIP_ANALYSIS:'):
                pradip_analysis = line_stripped[16:].strip()
            elif line_stripped.upper().startswith('CHART_TYPE:'):
                chart_type_raw = line_stripped[11:].strip().upper()
                if chart_type_raw in ['DAILY', 'WEEKLY', 'MONTHLY']:
                    chart_type = chart_type_raw
        
        if not pradip_analysis:
            for line in lines:
                if 'NOT FOUND' in line.upper():
                    return "NOT FOUND", "DAILY"
            pradip_analysis = result
        
        return pradip_analysis, chart_type
        
    except Exception as e:
        print(f"    Error extracting Pradip's analysis: {str(e)}")
        return "ERROR", "DAILY"


def polish_analysis(client, stock_name, original_analysis):
    """
    Polish Pradip's extracted analysis into professional format.
    Uses the user-specified formatting rules.
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


def run(job_folder):
    """Extract and polish Pradip's analysis for each stock"""
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 5: EXTRACT PRADIP'S ANALYSIS")
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
        
        analyses = []
        chart_types = []
        found_in_transcript = []
        
        print("=" * 100)
        print(f"{'#':<4} {'INPUT STOCK':<30} {'FOUND':<8} {'PRADIP ANALYSIS':<55}")
        print("=" * 100)
        
        for idx, row in df_input.iterrows():
            stock_name = str(row.get('INPUT STOCK', row.get('STOCK SYMBOL', ''))).strip()
            stock_symbol = str(row.get('STOCK SYMBOL', row.get('GPT SYMBOL', ''))).strip()
            
            is_found = search_stock_in_transcript(transcript_text, stock_name, stock_symbol)
            found_in_transcript.append("YES" if is_found else "NO")
            
            if is_found:
                pradip_analysis, chart_type = extract_pradip_analysis(
                    client, transcript_text, stock_name, stock_symbol
                )
                
                if pradip_analysis and pradip_analysis not in ["NOT FOUND", "ERROR"]:
                    polished_analysis = polish_analysis(client, stock_name, pradip_analysis)
                    analyses.append(polished_analysis)
                    chart_types.append(chart_type)
                    status = polished_analysis[:50] + "..." if len(polished_analysis) > 50 else polished_analysis
                else:
                    analyses.append(f"Analysis pending for {stock_name}")
                    chart_types.append("DAILY")
                    status = "Pradip did not discuss"
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
        print(f"   Total stocks: {len(df_input)}")
        print(f"   Found in transcript: {found_count}")
        print(f"   With Pradip's analysis: {with_analysis}")
        print(f"\n💾 Saved to: {output_csv}")
        
        return {
            'success': True,
            'output_file': output_csv,
            'stock_count': len(df_input),
            'found_count': found_count,
            'analysis_count': with_analysis
        }
        
    except Exception as e:
        print(f"❌ Error in Step 5: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
