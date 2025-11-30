"""
Bulk Rationale Step 2: Convert to CSV
Converts bulk-input-english.txt to structured CSV
- Reads line by line (stock name, then analysis)
- Splits multi-stock entries into separate rows
- Uses OpenAI to validate and fix stock name spelling
"""

import os
import re
import json
import openai
import pandas as pd
from rapidfuzz import fuzz
from backend.utils.database import get_db_cursor


def get_openai_key():
    """Get OpenAI API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'openai'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def parse_bulk_input(input_text):
    """
    Parse the bulk input text line by line.
    Format: Stock name line, then analysis line(s), then empty line, repeat.
    
    Returns list of tuples: [(stock_names_string, analysis_text), ...]
    """
    lines = input_text.strip().split('\n')
    entries = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        stock_line = line
        
        analysis_lines = []
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            
            if not next_line:
                i += 1
                if i < len(lines) and lines[i].strip():
                    next_peek = lines[i].strip()
                    if len(next_peek) < 100 and not any(c in next_peek.lower() for c in ['should', 'can', 'will', 'the', 'is', 'are', 'has', 'have', 'target', 'stop', 'hold', 'buy', 'sell', 'trading']):
                        break
                break
            
            analysis_lines.append(next_line)
            i += 1
        
        analysis_text = ' '.join(analysis_lines)
        
        if analysis_text:
            entries.append((stock_line, analysis_text))
    
    return entries


def deduplicate_stocks(corrected_entries, entries):
    """
    Remove duplicate stocks, keeping the single entry version.
    Example: If "HYUNDAI MOTORS" (grouped) and "HYUNDAI MOTOR INDIA LTD" (single) exist,
    keep "HYUNDAI MOTOR INDIA LTD" and remove the grouped version.
    
    Args:
        corrected_entries: List of validated stock entries with index
        entries: Original entries list to check if stock was single or grouped
        
    Returns:
        List of deduplicated entries
    """
    from difflib import SequenceMatcher
    
    def similarity(a, b):
        return SequenceMatcher(None, a.upper(), b.upper()).ratio()
    
    # Track which entries were single vs grouped
    single_entries = set()
    grouped_entries = set()
    
    for idx, (stock_line, _) in enumerate(entries):
        stock_names = [s.strip() for s in stock_line.split(',')]
        if len(stock_names) == 1:
            single_entries.add(idx)
        else:
            grouped_entries.add(idx)
    
    # Build a map of stock names to their entries
    stock_map = {}
    for entry in corrected_entries:
        idx = entry['index']
        stock_name = entry['stock_name']
        if stock_name not in stock_map:
            stock_map[stock_name] = {'entry': entry, 'is_single': idx in single_entries}
        else:
            # If this stock already exists
            existing = stock_map[stock_name]
            # Prefer single entries over grouped entries
            if (idx in single_entries) and not existing['is_single']:
                stock_map[stock_name] = {'entry': entry, 'is_single': True}
    
    # Find similar stocks (potential duplicates)
    unique_stocks = list(stock_map.keys())
    duplicates_to_remove = set()
    
    for i, stock1 in enumerate(unique_stocks):
        if stock1 in duplicates_to_remove:
            continue
        for stock2 in unique_stocks[i+1:]:
            if stock2 in duplicates_to_remove:
                continue
            
            sim_score = similarity(stock1, stock2)
            if sim_score >= 0.85:  # High similarity threshold
                # Keep the correct/longer one, remove the shorter one
                existing1 = stock_map[stock1]
                existing2 = stock_map[stock2]
                
                # Prefer single entries
                if existing1['is_single'] and not existing2['is_single']:
                    duplicates_to_remove.add(stock2)
                elif existing2['is_single'] and not existing1['is_single']:
                    duplicates_to_remove.add(stock1)
                # If both single or both grouped, keep the longer name
                elif len(stock1) > len(stock2):
                    duplicates_to_remove.add(stock2)
                else:
                    duplicates_to_remove.add(stock1)
    
    # Return only non-duplicate entries
    result = []
    seen_stocks = set()
    for entry in corrected_entries:
        stock_name = entry['stock_name']
        if stock_name not in duplicates_to_remove and stock_name not in seen_stocks:
            result.append(entry)
            seen_stocks.add(stock_name)
    
    return result, duplicates_to_remove


def validate_stocks_with_openai(client, entries):
    """
    Use OpenAI to validate and fix stock names.
    Also splits multi-stock entries into separate rows.
    
    Args:
        client: OpenAI client
        entries: List of (stock_line, analysis) tuples
        
    Returns:
        List of dicts with corrected stock names
    """
    entries_for_ai = []
    for idx, (stock_line, analysis) in enumerate(entries):
        entries_for_ai.append({
            "index": idx,
            "stock_line": stock_line,
            "analysis_preview": analysis[:200] + "..." if len(analysis) > 200 else analysis
        })
    
    prompt = f"""You are an expert in Indian stock markets (NSE/BSE). 
Your task is to validate and correct stock names from a list of entries.

INPUT ENTRIES:
{json.dumps(entries_for_ai, indent=2)}

CRITICAL RULES:
1. **FIX SPELLING ERRORS**: If a stock name has a spelling error, correct it to the official NSE/BSE name.
   Examples: "Suzuelon" → "SUZLON", "INFOSIS" → "INFOSYS", "Maruthi" → "MARUTI"
   
2. **USE CORRECT FULL NAMES**: 
   - "UNION BANK" → "UNION BANK OF INDIA" (NOT "CITY UNION BANK" - that's a different bank!)
   - "CANARA BANK" → "CANARA BANK"
   - "PNB" → "PUNJAB NATIONAL BANK"
   - "SBI" → "STATE BANK OF INDIA"
   - "PUNJAB AND SIND BANK" → "PUNJAB AND SIND BANK"
   
3. **SPLIT MULTI-STOCK ENTRIES**: If stock_line contains multiple stocks separated by comma:
   - "HFCL, PUNJAB AND SIND BANK" → Two separate entries: "HFCL" and "PUNJAB AND SIND BANK"
   - Each stock should be its own entry with the same index (to map back to same analysis)
   
4. **REMOVE SUFFIXES**: Remove (CALL), (BUY), (SELL), (HOLD) from stock names
   - "MARKSANS PHARMA (CALL)" → "MARKSANS PHARMA"

5. **USE NSE SYMBOLS**: Convert to standard NSE trading symbols where possible
   - "PUNJAB AND SIND BANK" → "PSB" 
   - "HFCL" stays "HFCL"

6. **DO NOT INVENT STOCKS**: Only process stocks that are mentioned. Don't add new ones.

7. **DO NOT SKIP STOCKS**: Process ALL entries, don't skip any.

Return a JSON array with corrected entries:
[
  {{"index": 0, "stock_name": "CORRECTED_NAME"}},
  {{"index": 0, "stock_name": "SECOND_STOCK_IF_MULTI"}},
  {{"index": 1, "stock_name": "CORRECTED_NAME"}}
]

Return ONLY valid JSON, no other text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an Indian stock market expert. Your task is to validate stock names against NSE/BSE listings and fix any spelling errors. CRITICAL: UNION BANK means UNION BANK OF INDIA, NOT City Union Bank. Always return valid JSON arrays only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=4096
        )
        
        response_text = response.choices[0].message.content.strip()
        
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        corrected_entries = json.loads(response_text)
        return corrected_entries
        
    except Exception as e:
        print(f"⚠️ OpenAI validation error: {e}")
        return None


def run(job_folder, call_date, call_time):
    """
    Convert translated text to structured CSV
    
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
        
        print(f"📖 Reading input file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        print(f"📝 Text length: {len(input_text)} characters")
        print(f"📅 Call Date: {call_date}, Time: {call_time}")
        
        print("\n🔄 Parsing input text line by line...")
        entries = parse_bulk_input(input_text)
        print(f"✅ Found {len(entries)} raw entries")
        
        print("\n📋 Raw stock lines found:")
        print("-" * 60)
        for idx, (stock_line, _) in enumerate(entries):
            print(f"  {idx+1}. {stock_line}")
        print("-" * 60)
        
        print("\n🤖 Validating stock names with OpenAI...")
        client = openai.OpenAI(api_key=openai_key)
        corrected_entries = validate_stocks_with_openai(client, entries)
        
        if not corrected_entries:
            print("⚠️ OpenAI validation failed, using original names with basic cleanup")
            corrected_entries = []
            for idx, (stock_line, _) in enumerate(entries):
                stock_names = [s.strip() for s in stock_line.split(',')]
                for name in stock_names:
                    clean_name = re.sub(r'\s*\((?:CALL|BUY|SELL|HOLD)\)\s*$', '', name, flags=re.IGNORECASE).strip().upper()
                    if clean_name:
                        corrected_entries.append({"index": idx, "stock_name": clean_name})
        
        print("\n🔍 Removing duplicate stocks...")
        corrected_entries, duplicates_removed = deduplicate_stocks(corrected_entries, entries)
        if duplicates_removed:
            print(f"✅ Removed {len(duplicates_removed)} duplicate(s):")
            for dup in duplicates_removed:
                print(f"  - {dup}")
        
        print("\n📋 Validated stock names:")
        print("-" * 60)
        
        rows = []
        for entry in corrected_entries:
            idx = entry['index']
            stock_name = entry['stock_name']
            _, analysis = entries[idx]
            
            print(f"  ✅ {stock_name}")
            
            rows.append({
                "DATE": call_date,
                "TIME": call_time,
                "STOCK NAME": stock_name,
                "ANALYSIS": analysis
            })
        
        print("-" * 60)
        
        if not rows:
            return {
                'success': False,
                'error': 'No stocks extracted from input text'
            }
        
        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ Created {len(df)} stock entries")
        print(f"💾 Saved to: {output_file}")
        
        multi_stock_entries = len([e for e in entries if ',' in e[0]])
        if multi_stock_entries > 0:
            print(f"📊 Split {multi_stock_entries} multi-stock entries into separate rows")
        
        print("\n📋 Final Stock List:")
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
        import traceback
        traceback.print_exc()
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
