"""
Bulk Rationale Step 2: Convert to CSV
Converts bulk-input-english.txt to structured CSV
- Reads line by line (stock name, then analysis)
- Splits multi-stock entries into separate rows
- Validates and fixes stock name spelling against master file
"""

import os
import re
import pandas as pd
import psycopg2
from rapidfuzz import fuzz, process
from backend.utils.database import get_db_cursor
from backend.utils.path_utils import resolve_uploaded_file_path


def get_master_file_path():
    """Fetch master file path from database and resolve to current system path"""
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path 
            FROM uploaded_files 
            WHERE file_type = 'masterFile'
            ORDER BY uploaded_at DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            db_path = result[0]
            resolved_path = resolve_uploaded_file_path(db_path)
            return resolved_path
        else:
            return None
    
    except Exception as e:
        print(f"⚠️ Could not fetch master file: {str(e)}")
        return None


def load_stock_names_from_master(master_path):
    """Load all stock names from master file for spelling validation"""
    if not master_path or not os.path.exists(master_path):
        return []
    
    try:
        df = pd.read_csv(master_path, low_memory=False)
        df = df[df["SEM_INSTRUMENT_NAME"].astype(str).str.upper() == "EQUITY"]
        
        stock_names = set()
        for col in ["SEM_CUSTOM_SYMBOL", "SEM_TRADING_SYMBOL", "SM_SYMBOL_NAME"]:
            if col in df.columns:
                names = df[col].dropna().astype(str).str.strip().str.upper().tolist()
                stock_names.update(names)
        
        return list(stock_names)
    except Exception as e:
        print(f"⚠️ Error loading master file: {str(e)}")
        return []


def normalize_text(s):
    """Clean text for matching"""
    if not isinstance(s, str):
        s = str(s)
    s = re.sub(r"[^A-Z0-9\s]", "", s.upper())
    return s.strip()


def fix_stock_spelling(stock_name, master_names, threshold=80):
    """
    Check and fix stock name spelling against master file
    Returns the corrected name if a close match is found
    """
    if not master_names:
        return stock_name
    
    stock_upper = stock_name.strip().upper()
    
    if stock_upper in master_names:
        return stock_upper
    
    stock_norm = normalize_text(stock_upper)
    
    result = process.extractOne(
        stock_norm, 
        [normalize_text(n) for n in master_names],
        scorer=fuzz.token_sort_ratio
    )
    
    if result and result[1] >= threshold:
        matched_norm = result[0]
        for name in master_names:
            if normalize_text(name) == matched_norm:
                return name
    
    return stock_upper


def parse_bulk_input(input_text):
    """
    Parse the bulk input text line by line.
    Format: Stock name line, then analysis line, then empty line, repeat.
    
    Returns list of tuples: [(stock_names_list, analysis_text), ...]
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
                    if len(next_peek) < 100 and not any(c in next_peek.lower() for c in ['should', 'can', 'will', 'the', 'is', 'are', 'has', 'have', 'target', 'stop', 'hold']):
                        break
                break
            
            analysis_lines.append(next_line)
            i += 1
        
        analysis_text = ' '.join(analysis_lines)
        
        if analysis_text:
            stock_names = [s.strip() for s in stock_line.split(',')]
            stock_names = [re.sub(r'\s*\((?:CALL|BUY|SELL|HOLD)\)\s*$', '', s, flags=re.IGNORECASE).strip() for s in stock_names]
            stock_names = [s for s in stock_names if s]
            
            if stock_names:
                entries.append((stock_names, analysis_text))
    
    return entries


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
        
        print(f"📖 Reading input file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        print(f"📝 Text length: {len(input_text)} characters")
        print(f"📅 Call Date: {call_date}, Time: {call_time}")
        
        print("\n🔑 Loading master file for stock name validation...")
        master_path = get_master_file_path()
        master_names = []
        if master_path:
            master_names = load_stock_names_from_master(master_path)
            print(f"✅ Loaded {len(master_names)} stock names from master file")
        else:
            print("⚠️ Master file not found, skipping spelling validation")
        
        print("\n🔄 Parsing input text line by line...")
        entries = parse_bulk_input(input_text)
        print(f"✅ Found {len(entries)} stock entries")
        
        print("\n📋 Processing stocks and fixing spelling...")
        print("-" * 60)
        
        rows = []
        spelling_fixes = []
        
        for stock_names, analysis in entries:
            for original_name in stock_names:
                corrected_name = fix_stock_spelling(original_name, master_names)
                
                if corrected_name.upper() != original_name.upper():
                    spelling_fixes.append((original_name, corrected_name))
                    print(f"  🔧 Spelling fix: {original_name} → {corrected_name}")
                else:
                    print(f"  ✅ {corrected_name}")
                
                rows.append({
                    "DATE": call_date,
                    "TIME": call_time,
                    "STOCK NAME": corrected_name,
                    "ANALYSIS": analysis
                })
        
        print("-" * 60)
        
        if spelling_fixes:
            print(f"\n📝 Fixed {len(spelling_fixes)} spelling errors")
        
        if not rows:
            return {
                'success': False,
                'error': 'No stocks extracted from input text'
            }
        
        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ Created {len(df)} stock entries")
        print(f"💾 Saved to: {output_file}")
        
        multi_stock_count = sum(1 for names, _ in entries if len(names) > 1)
        if multi_stock_count > 0:
            print(f"📊 Split {multi_stock_count} multi-stock entries into separate rows")
        
        print("\n📋 Final Stock List:")
        print("-" * 40)
        for i, row in df.iterrows():
            print(f"  {i+1}. {row['STOCK NAME']}")
        
        return {
            'success': True,
            'output_file': output_file,
            'stock_count': len(df),
            'spelling_fixes': len(spelling_fixes)
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
