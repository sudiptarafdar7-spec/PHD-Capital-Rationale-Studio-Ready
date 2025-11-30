"""
Bulk Rationale Step 2: Convert to CSV
Converts bulk-input-english.txt to structured CSV using OpenAI
"""

import os
import json
import openai
import pandas as pd
from backend.utils.database import get_db_cursor


def get_openai_key():
    """Get OpenAI API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'openai'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def run(job_folder, call_date, call_time):
    """
    Convert translated text to structured CSV using OpenAI
    
    Args:
        job_folder: Path to job directory
        call_date: Date of the call (YYYY-MM-DD format)
        call_time: Time of the call (HH:MM:SS format)
        
    Returns:
        dict: {
            'success': bool,
            'output_file': str,
            'error': str or None
        }
    """
    print("\n" + "=" * 60)
    print("BULK STEP 2: CONVERT TO CSV")
    print(f"{'='*60}\n")
    
    try:
        input_file = os.path.join(job_folder, 'bulk-input-english.txt')
        analysis_folder = os.path.join(job_folder, 'analysis')
        os.makedirs(analysis_folder, exist_ok=True)
        output_file = os.path.join(analysis_folder, 'bulk-input.csv')
        
        if not os.path.exists(input_file):
            return {
                'success': False,
                'error': f'Translated file not found: {input_file}'
            }
        
        openai_key = get_openai_key()
        if not openai_key:
            return {
                'success': False,
                'error': 'OpenAI API key not found. Please add it in Settings → API Keys.'
            }
        
        print(f"📖 Reading translated text: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        print(f"📝 Text length: {len(input_text)} characters")
        print(f"📅 Call Date: {call_date}, Time: {call_time}")
        
        print("🔄 Converting to structured CSV using OpenAI...")
        
        client = openai.OpenAI(api_key=openai_key)
        
        prompt = f"""You are a SEBI-registered Research Analyst expert. Extract stock calls from this text and convert to structured data.

INPUT TEXT:
{input_text}

CALL DATE: {call_date}
CALL TIME: {call_time}

The input text is structured as:
- Each entry starts with a STOCK NAME line (header) followed by an ANALYSIS paragraph
- Some headers may contain MULTIPLE STOCKS separated by comma (e.g., "UNION BANK, CANARA BANK")

CRITICAL RULES:
1. **MULTI-STOCK HEADERS**: If a header contains multiple stocks separated by comma (e.g., "UNION BANK, CANARA BANK"), create SEPARATE entries for EACH stock. Each stock gets its own row with the SAME EXACT analysis text.
2. **PRESERVE EXACT ANALYSIS**: Copy the analysis paragraph EXACTLY as written - do not modify, summarize, or paraphrase.
3. **CLEAN STOCK NAMES**: Remove suffixes like "(CALL)", "(BUY)", "(SELL)" from stock names. Keep only the clean stock name.
   - Example: "MARKSANS PHARMA (CALL)" → "MARKSANS PHARMA"
   - Example: "UNION BANK, CANARA BANK" → Create 2 separate entries: "UNION BANK" and "CANARA BANK"
4. Use the provided DATE and TIME for all entries.
5. Return ONLY a valid JSON array, no other text.

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "DATE": "{call_date}",
    "TIME": "{call_time}",
    "STOCK NAME": "clean stock name only",
    "ANALYSIS": "EXACT analysis text copied verbatim from input"
  }}
]

EXAMPLE - For input:
```
UNION BANK, CANARA BANK
We gave a call on Union Bank and Canara Bank. Both are looking good.

VEDANTA
The trend is positive for Vedanta.
```

Output should be 3 entries:
[
  {{"DATE": "...", "TIME": "...", "STOCK NAME": "UNION BANK", "ANALYSIS": "We gave a call on Union Bank and Canara Bank. Both are looking good."}},
  {{"DATE": "...", "TIME": "...", "STOCK NAME": "CANARA BANK", "ANALYSIS": "We gave a call on Union Bank and Canara Bank. Both are looking good."}},
  {{"DATE": "...", "TIME": "...", "STOCK NAME": "VEDANTA", "ANALYSIS": "The trend is positive for Vedanta."}}
]"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial data extraction expert. Your task is to parse structured stock call data. CRITICAL: 1) If a header line contains multiple stocks separated by comma, create SEPARATE entries for each stock with the SAME analysis. 2) Preserve analysis text EXACTLY as written - copy verbatim, no modifications. 3) Clean stock names by removing suffixes like (CALL), (BUY), (SELL). Always return valid JSON arrays only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=8192
        )
        
        response_text = response.choices[0].message.content.strip()
        
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        try:
            stocks_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
            print(f"Response: {response_text[:500]}")
            return {
                'success': False,
                'error': f'Failed to parse OpenAI response as JSON: {str(e)}'
            }
        
        if not stocks_data:
            return {
                'success': False,
                'error': 'No stocks extracted from input text'
            }
        
        df = pd.DataFrame(stocks_data)
        
        required_cols = ['DATE', 'TIME', 'STOCK NAME', 'ANALYSIS']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''
        
        df = df[required_cols]
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"✅ Extracted {len(df)} stocks")
        print(f"💾 Saved to: {output_file}")
        
        print("\n📋 Extracted Stocks:")
        print("-" * 40)
        for i, row in df.iterrows():
            print(f"  {i+1}. {row['STOCK NAME']}")
        
        return {
            'success': True,
            'output_file': output_file,
            'stock_count': len(df)
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_folder = sys.argv[1]
    else:
        test_folder = "backend/job_files/test_bulk_job"
    
    result = run(test_folder, "2025-01-01", "10:00:00")
    print(f"\n{'='*60}")
    print(f"Result: {'SUCCESS' if result.get('success') else 'FAILED'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print(f"{'='*60}")
