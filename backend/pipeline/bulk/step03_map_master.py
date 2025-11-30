"""
Bulk Rationale Step 4: Map Master File

Maps stock names from Step 2/3 CSV to the master reference file to get:
- Stock Symbol (SEM_TRADING_SYMBOL)
- Listed Name (SM_SYMBOL_NAME)
- Short Name (SEM_CUSTOM_SYMBOL)
- Security ID (SEM_SMST_SECURITY_ID)
- Exchange (SEM_EXM_EXCH_ID)
- Instrument (SEM_INSTRUMENT_NAME)

Matching Logic (same as Media Rationale):
1. Filter master data → only EQUITY rows
2. Match STOCK NAME sequentially:
   - Primary: Short name column (SEM_CUSTOM_SYMBOL) exact match
   - Secondary: Symbol column (SEM_TRADING_SYMBOL) exact match
   - Tertiary: Name column (SM_SYMBOL_NAME) exact match
   - Fuzzy on SEM_CUSTOM_SYMBOL (>= 80%)
   - Fuzzy on SEM_TRADING_SYMBOL (>= 80%)
   - Fuzzy on SM_SYMBOL_NAME (>= 80%)
   - Word matching on SEM_TRADING_SYMBOL
   - Word matching on SM_SYMBOL_NAME
3. If both NSE and BSE found → Prefer NSE

Input:
  - analysis/bulk-input-analysis.csv (from Step 3) or analysis/bulk-input.csv (from Step 2)
  - Master CSV from uploaded_files
Output:
  - analysis/mapped_master_file.csv
"""

import os
import re
import pandas as pd
import psycopg2
from rapidfuzz import fuzz, process
from backend.utils.path_utils import resolve_uploaded_file_path


def normalize_text(s):
    """Clean text for matching (remove special chars, multiple spaces)."""
    if not isinstance(s, str):
        s = str(s)
    s = re.sub(r"[^A-Z0-9]", "", s.upper())
    return s.strip()


def get_words(s):
    """Extract meaningful words from stock name for word matching."""
    if not isinstance(s, str):
        s = str(s)
    words = re.sub(r"[^A-Z0-9\s]", "", s.upper()).split()
    stop_words = {'LTD', 'LIMITED', 'PVT', 'PRIVATE', 'INC', 'CORP', 'CORPORATION', 'AND', 'THE', 'OF', 'INDIA'}
    return [w for w in words if w and w not in stop_words and len(w) > 1]


def word_match_score(search_words, target_words):
    """
    Calculate word match score between two word lists.
    IMPORTANT: First word must match for a valid score.
    This prevents "SERVOTECH POWER SYSTEMS" matching "SMARTEN POWER SYSTEMS"
    just because they share "POWER SYSTEMS".
    """
    if not search_words or not target_words:
        return 0
    
    # First word (company name) MUST match
    first_word = search_words[0]
    first_word_matched = False
    
    # Check if first word matches any target word at the beginning
    # or is a substring of the first target word (for abbreviations)
    if first_word in target_words:
        first_word_matched = True
    elif target_words and (first_word.startswith(target_words[0]) or target_words[0].startswith(first_word)):
        first_word_matched = True
    
    # If first word doesn't match, return 0 (no match)
    if not first_word_matched:
        return 0
    
    # Count total matched words
    matched = sum(1 for w in search_words if w in target_words)
    return matched / max(len(search_words), 1) * 100


def fuzzy_match(value, target_series, threshold=80):
    """Return best fuzzy match index or None if below threshold."""
    if not value or not isinstance(value, str):
        return None
    value_norm = normalize_text(value)
    choices = target_series.tolist()
    result = process.extractOne(value_norm, choices, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        matched_value = result[0]
        idx_list = target_series[target_series == matched_value].index
        if len(idx_list) > 0:
            return idx_list[0]
    return None


def word_match(search_name, df_master, column, threshold=60):
    """Find best word-based match in a column."""
    search_words = get_words(search_name)
    if not search_words:
        return None
    
    best_score = 0
    best_idx = None
    
    for idx, row in df_master.iterrows():
        target_value = row.get(column, "")
        if not target_value:
            continue
        target_words = get_words(target_value)
        score = word_match_score(search_words, target_words)
        
        if score > best_score and score >= threshold:
            best_score = score
            best_idx = idx
    
    return best_idx


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
            print(f"📂 Master file path from DB: {db_path}")
            print(f"📂 Resolved to: {resolved_path}")
            return resolved_path
        else:
            raise ValueError("Master file not found in database. Please upload it first in Settings.")
    
    except Exception as e:
        raise Exception(f"Failed to fetch master file path: {str(e)}")


def run(job_folder):
    """
    Match stocks to master file and add symbol/exchange data
    
    Args:
        job_folder: Path to job folder
    
    Returns:
        dict: Status, message, and output files
    """
    print("\n" + "="*60)
    print("BULK STEP 4: MAP MASTER FILE (SYMBOL MAPPING)")
    print(f"{'='*60}\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        polished_csv = os.path.join(analysis_folder, 'bulk-input-analysis.csv')
        original_csv = os.path.join(analysis_folder, 'bulk-input.csv')
        input_csv = polished_csv if os.path.exists(polished_csv) else original_csv
        output_csv = os.path.join(analysis_folder, 'mapped_master_file.csv')
        
        if not os.path.exists(input_csv):
            return {
                'success': False,
                'error': f'Bulk input CSV not found: {input_csv}'
            }
        
        print("🔑 Retrieving master file path from database...")
        master_file_path = get_master_file_path()
        
        if not os.path.exists(master_file_path):
            return {
                'success': False,
                'error': f'Master file not found at: {master_file_path}'
            }
        
        print(f"✅ Master file found: {master_file_path}\n")
        
        print("📖 Loading master file...")
        df_master = pd.read_csv(master_file_path, low_memory=False)
        print(f"✅ Loaded {len(df_master)} records from master file\n")
        
        print("🔍 Filtering for EQUITY instruments...")
        df_master = df_master[df_master["SEM_INSTRUMENT_NAME"].astype(str).str.upper() == "EQUITY"].copy()
        print(f"✅ {len(df_master)} EQUITY records found\n")
        
        print("🔧 Normalizing master file fields...")
        for col in ["SEM_TRADING_SYMBOL", "SEM_CUSTOM_SYMBOL", "SM_SYMBOL_NAME", "SEM_EXM_EXCH_ID"]:
            if col in df_master.columns:
                df_master[col] = df_master[col].astype(str).str.strip().str.upper()
            else:
                df_master[col] = ""
        
        df_master["SEM_CUSTOM_SYMBOL_NORM"] = df_master["SEM_CUSTOM_SYMBOL"].apply(normalize_text)
        df_master["SEM_TRADING_SYMBOL_NORM"] = df_master["SEM_TRADING_SYMBOL"].apply(normalize_text)
        df_master["SM_SYMBOL_NAME_NORM"] = df_master["SM_SYMBOL_NAME"].apply(normalize_text)
        
        df_master["exchange_priority"] = df_master["SEM_EXM_EXCH_ID"].apply(
            lambda x: 1 if x == "NSE" else (2 if x == "BSE" else 3)
        )
        print("✅ Master file normalized\n")
        
        print("📖 Loading bulk input stocks...")
        df_input = pd.read_csv(input_csv)
        df_input.columns = df_input.columns.str.strip().str.upper()
        
        if 'STOCK NAME' not in df_input.columns:
            return {
                'success': False,
                'error': 'STOCK NAME column not found in bulk-input.csv'
            }
        
        df_input['STOCK NAME'] = df_input['STOCK NAME'].astype(str).str.strip().str.upper()
        df_input["STOCK_NAME_NORM"] = df_input['STOCK NAME'].apply(normalize_text)
        
        print(f"✅ Loaded {len(df_input)} stocks to map\n")
        
        print("🔗 Starting stock matching process...")
        print("-" * 60)
        
        results = []
        matched_count = 0
        
        for idx, row in df_input.iterrows():
            stock_name = row['STOCK NAME']
            stock_name_norm = row['STOCK_NAME_NORM']
            date = row.get('DATE', '')
            time = row.get('TIME', '')
            analysis = row.get('ANALYSIS', row.get('RATIONALE', ''))
            chart_type = row.get('CHART TYPE', 'Daily')
            
            match = None
            match_source = ""
            candidates = pd.DataFrame()
            
            # 1. Exact match on SEM_CUSTOM_SYMBOL (short name)
            candidates = df_master[df_master["SEM_CUSTOM_SYMBOL"] == stock_name]
            if not candidates.empty:
                match_source = "SEM_CUSTOM_SYMBOL (exact)"
            
            # 2. Exact match on SEM_TRADING_SYMBOL
            if candidates.empty:
                candidates = df_master[df_master["SEM_TRADING_SYMBOL"] == stock_name]
                if not candidates.empty:
                    match_source = "SEM_TRADING_SYMBOL (exact)"
            
            # 3. Exact match on SM_SYMBOL_NAME
            if candidates.empty:
                candidates = df_master[df_master["SM_SYMBOL_NAME"] == stock_name]
                if not candidates.empty:
                    match_source = "SM_SYMBOL_NAME (exact)"
            
            # 4. Fuzzy match on SEM_CUSTOM_SYMBOL
            if candidates.empty:
                idx_match = fuzzy_match(stock_name, df_master["SEM_CUSTOM_SYMBOL_NORM"], threshold=80)
                if idx_match is not None:
                    candidates = df_master.loc[[idx_match]]
                    match_source = "SEM_CUSTOM_SYMBOL (fuzzy >= 80%)"
            
            # 5. Fuzzy match on SEM_TRADING_SYMBOL
            if candidates.empty:
                idx_match = fuzzy_match(stock_name, df_master["SEM_TRADING_SYMBOL_NORM"], threshold=80)
                if idx_match is not None:
                    candidates = df_master.loc[[idx_match]]
                    match_source = "SEM_TRADING_SYMBOL (fuzzy >= 80%)"
            
            # 6. Fuzzy match on SM_SYMBOL_NAME
            if candidates.empty:
                idx_match = fuzzy_match(stock_name, df_master["SM_SYMBOL_NAME_NORM"], threshold=80)
                if idx_match is not None:
                    candidates = df_master.loc[[idx_match]]
                    match_source = "SM_SYMBOL_NAME (fuzzy >= 80%)"
            
            # 7. Word matching on SEM_TRADING_SYMBOL
            if candidates.empty:
                idx_match = word_match(stock_name, df_master, "SEM_TRADING_SYMBOL", threshold=60)
                if idx_match is not None:
                    candidates = df_master.loc[[idx_match]]
                    match_source = "SEM_TRADING_SYMBOL (word match)"
            
            # 8. Word matching on SM_SYMBOL_NAME
            if candidates.empty:
                idx_match = word_match(stock_name, df_master, "SM_SYMBOL_NAME", threshold=60)
                if idx_match is not None:
                    candidates = df_master.loc[[idx_match]]
                    match_source = "SM_SYMBOL_NAME (word match)"
            
            # 9. Normalized exact match fallback
            if candidates.empty:
                idx_list = df_master[df_master["SEM_TRADING_SYMBOL_NORM"] == stock_name_norm].index
                if len(idx_list) > 0:
                    candidates = df_master.loc[idx_list]
                    match_source = "SEM_TRADING_SYMBOL (normalized fallback)"
            
            # Pick best match (NSE preferred)
            if not candidates.empty:
                candidates = candidates.sort_values(by="exchange_priority")
                match = candidates.iloc[0]
            
            if match is not None:
                stock_symbol = match.get("SEM_TRADING_SYMBOL", "")
                listed_name = match.get("SM_SYMBOL_NAME", "")
                short_name = match.get("SEM_CUSTOM_SYMBOL", "")
                security_id = match.get("SEM_SMST_SECURITY_ID", "")
                exchange = match.get("SEM_EXM_EXCH_ID", "")
                instrument = match.get("SEM_INSTRUMENT_NAME", "")
                
                results.append({
                    "DATE": date,
                    "TIME": time,
                    "STOCK NAME": stock_name,
                    "ANALYSIS": analysis,
                    "CHART TYPE": chart_type,
                    "STOCK SYMBOL": stock_symbol,
                    "LISTED NAME": listed_name,
                    "SHORT NAME": short_name,
                    "SECURITY ID": security_id,
                    "EXCHANGE": exchange,
                    "INSTRUMENT": instrument
                })
                matched_count += 1
                print(f"✅ {stock_name:30} → {stock_symbol:15} | {match_source:35} ({exchange})")
            else:
                print(f"❌ {stock_name:30} → No match found")
                results.append({
                    "DATE": date,
                    "TIME": time,
                    "STOCK NAME": stock_name,
                    "ANALYSIS": analysis,
                    "CHART TYPE": chart_type,
                    "STOCK SYMBOL": "",
                    "LISTED NAME": "",
                    "SHORT NAME": "",
                    "SECURITY ID": "",
                    "EXCHANGE": "",
                    "INSTRUMENT": ""
                })
        
        print("-" * 60)
        print(f"\n📊 Mapping Summary:")
        print(f"   Total stocks: {len(df_input)}")
        print(f"   Matched: {matched_count}")
        print(f"   Unmatched: {len(df_input) - matched_count}\n")
        
        print(f"💾 Saving mapped data to: {output_csv}")
        final_df = pd.DataFrame(results)
        
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        
        final_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        print(f"✅ Saved {len(final_df)} records")
        print(f"✅ Output: analysis/mapped_master_file.csv\n")
        
        return {
            'success': True,
            'output_file': output_csv,
            'matched_count': matched_count,
            'total_stocks': len(df_input),
            'error': None
        }
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
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
    
    result = run(test_folder)
    print(f"\n{'='*60}")
    print(f"Result: {'SUCCESS' if result.get('success') else 'FAILED'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print(f"{'='*60}")
