"""
Transcript Rationale Step 4: Map Master File
Maps GPT SYMBOL from Step 3 to the master reference file

Matching Logic (Priority Order):
1. EXACT match (normalized): GPT SYMBOL → SEM_TRADING_SYMBOL
2. EXACT match (normalized): GPT SYMBOL → SEM_CUSTOM_SYMBOL
3. EXACT match (normalized): GPT SYMBOL → SM_SYMBOL_NAME
4. FUZZY match with RapidFuzz on SEM_TRADING_SYMBOL
5. FUZZY match with RapidFuzz on SEM_CUSTOM_SYMBOL
6. FUZZY match with RapidFuzz on SM_SYMBOL_NAME

Output: mapped_master_file.csv with STOCK SYMBOL, LISTED NAME, SHORT NAME, SECURITY ID, EXCHANGE, INSTRUMENT
"""

import os
import re
import pandas as pd
import psycopg2
from backend.utils.path_utils import resolve_uploaded_file_path

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


def normalize_for_exact_match(s):
    """Normalize text for EXACT matching - removes all spaces and special chars"""
    if not isinstance(s, str):
        s = str(s) if s is not None else ""
    s = s.upper().strip()
    s = re.sub(r'[^A-Z0-9]', '', s)
    return s


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
            print(f"Master file path from DB: {db_path}")
            print(f"Resolved to: {resolved_path}")
            return resolved_path
        else:
            raise ValueError("Master file not found in database. Please upload it first in Settings.")
    
    except Exception as e:
        raise Exception(f"Failed to fetch master file path: {str(e)}")


def find_exact_match(input_norm, df_master, column_norm):
    """Find exact match in normalized column"""
    matches = df_master[df_master[column_norm] == input_norm]
    return matches


def find_fuzzy_match(input_value, df_master, column, threshold=80):
    """Find best fuzzy match using RapidFuzz"""
    if not RAPIDFUZZ_AVAILABLE:
        return None, 0
    
    choices = df_master[column].dropna().unique().tolist()
    if not choices:
        return None, 0
    
    result = process.extractOne(input_value, choices, scorer=fuzz.ratio)
    if result and result[1] >= threshold:
        match_value = result[0]
        match_row = df_master[df_master[column] == match_value].iloc[0]
        return match_row, result[1]
    
    return None, 0


def run(job_folder):
    """Map stocks to master file and add symbol/exchange data"""
    print("\n" + "="*60)
    print("TRANSCRIPT STEP 4: MAP MASTER FILE (SYMBOL MAPPING)")
    print("="*60 + "\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        input_csv = os.path.join(analysis_folder, 'final-stocks.csv')
        output_csv = os.path.join(analysis_folder, 'mapped_master_file.csv')
        
        if not os.path.exists(input_csv):
            return {
                'success': False,
                'error': f'Final stocks CSV not found: {input_csv}'
            }
        
        print(f"Using input file: final-stocks.csv")
        
        print("\nRetrieving master file path from database...")
        master_file_path = get_master_file_path()
        
        if not os.path.exists(master_file_path):
            return {
                'success': False,
                'error': f'Master file not found at: {master_file_path}'
            }
        
        print(f"Master file found\n")
        
        print("Loading master file...")
        df_master = pd.read_csv(master_file_path, low_memory=False)
        print(f"Loaded {len(df_master)} records from master file\n")
        
        print("Filtering for EQUITY instruments...")
        df_master = df_master[df_master["SEM_INSTRUMENT_NAME"].astype(str).str.upper() == "EQUITY"].copy()
        print(f"{len(df_master)} EQUITY records found\n")
        
        print("Normalizing master file fields...")
        for col in ["SEM_TRADING_SYMBOL", "SEM_CUSTOM_SYMBOL", "SM_SYMBOL_NAME", "SEM_EXM_EXCH_ID"]:
            if col in df_master.columns:
                df_master[col] = df_master[col].astype(str).str.strip().str.upper()
            else:
                df_master[col] = ""
        
        df_master["SEM_TRADING_SYMBOL_NORM"] = df_master["SEM_TRADING_SYMBOL"].apply(normalize_for_exact_match)
        df_master["SEM_CUSTOM_SYMBOL_NORM"] = df_master["SEM_CUSTOM_SYMBOL"].apply(normalize_for_exact_match)
        df_master["SM_SYMBOL_NAME_NORM"] = df_master["SM_SYMBOL_NAME"].apply(normalize_for_exact_match)
        
        df_master["exchange_priority"] = df_master["SEM_EXM_EXCH_ID"].apply(
            lambda x: 1 if x == "NSE" else (2 if x == "BSE" else 3)
        )
        print("Master file normalized\n")
        
        print("Loading final stocks...")
        df_input = pd.read_csv(input_csv)
        df_input.columns = df_input.columns.str.strip().str.upper()
        
        if 'GPT SYMBOL' not in df_input.columns:
            return {
                'success': False,
                'error': 'GPT SYMBOL column not found in final-stocks.csv'
            }
        
        print(f"Loaded {len(df_input)} stocks to map\n")
        
        print("Starting stock matching process...")
        print("-" * 100)
        print(f"{'INPUT STOCK':<25} {'GPT SYMBOL':<18} {'MATCHED SYMBOL':<18} {'METHOD':<35}")
        print("-" * 100)
        
        results = []
        matched_count = 0
        
        for idx, row in df_input.iterrows():
            input_stock = row.get('INPUT STOCK', '')
            gpt_symbol = row.get('GPT SYMBOL', '')
            gpt_symbol_norm = normalize_for_exact_match(gpt_symbol)
            
            match = None
            match_source = ""
            candidates = pd.DataFrame()
            
            candidates = find_exact_match(gpt_symbol_norm, df_master, "SEM_TRADING_SYMBOL_NORM")
            if not candidates.empty:
                match_source = "SEM_TRADING_SYMBOL (exact)"
            
            if candidates.empty:
                candidates = find_exact_match(gpt_symbol_norm, df_master, "SEM_CUSTOM_SYMBOL_NORM")
                if not candidates.empty:
                    match_source = "SEM_CUSTOM_SYMBOL (exact)"
            
            if candidates.empty:
                candidates = find_exact_match(gpt_symbol_norm, df_master, "SM_SYMBOL_NAME_NORM")
                if not candidates.empty:
                    match_source = "SM_SYMBOL_NAME (exact)"
            
            if candidates.empty and RAPIDFUZZ_AVAILABLE:
                fuzzy_match, score = find_fuzzy_match(gpt_symbol, df_master, "SEM_TRADING_SYMBOL", threshold=80)
                if fuzzy_match is not None:
                    candidates = pd.DataFrame([fuzzy_match])
                    match_source = f"SEM_TRADING_SYMBOL (fuzzy {score:.0f}%)"
            
            if candidates.empty and RAPIDFUZZ_AVAILABLE:
                fuzzy_match, score = find_fuzzy_match(gpt_symbol, df_master, "SEM_CUSTOM_SYMBOL", threshold=80)
                if fuzzy_match is not None:
                    candidates = pd.DataFrame([fuzzy_match])
                    match_source = f"SEM_CUSTOM_SYMBOL (fuzzy {score:.0f}%)"
            
            if candidates.empty and RAPIDFUZZ_AVAILABLE:
                fuzzy_match, score = find_fuzzy_match(gpt_symbol, df_master, "SM_SYMBOL_NAME", threshold=80)
                if fuzzy_match is not None:
                    candidates = pd.DataFrame([fuzzy_match])
                    match_source = f"SM_SYMBOL_NAME (fuzzy {score:.0f}%)"
            
            if not candidates.empty:
                candidates = candidates.sort_values(by="exchange_priority")
                match = candidates.iloc[0]
            
            if match is not None:
                matched_count += 1
                result = {
                    'INPUT STOCK': input_stock,
                    'GPT SYMBOL': gpt_symbol,
                    'STOCK SYMBOL': match.get('SEM_TRADING_SYMBOL', ''),
                    'LISTED NAME': match.get('SM_SYMBOL_NAME', ''),
                    'SHORT NAME': match.get('SEM_CUSTOM_SYMBOL', ''),
                    'SECURITY ID': match.get('SEM_SMST_SECURITY_ID', ''),
                    'EXCHANGE': match.get('SEM_EXM_EXCH_ID', ''),
                    'INSTRUMENT': match.get('SEM_INSTRUMENT_NAME', ''),
                    'MATCH METHOD': match_source
                }
                print(f"{input_stock:<25} {gpt_symbol:<18} {result['STOCK SYMBOL']:<18} {match_source:<35}")
            else:
                result = {
                    'INPUT STOCK': input_stock,
                    'GPT SYMBOL': gpt_symbol,
                    'STOCK SYMBOL': gpt_symbol,
                    'LISTED NAME': '',
                    'SHORT NAME': '',
                    'SECURITY ID': '',
                    'EXCHANGE': '',
                    'INSTRUMENT': '',
                    'MATCH METHOD': 'NOT FOUND'
                }
                print(f"{input_stock:<25} {gpt_symbol:<18} {'NOT MATCHED':<18} {'---':<35}")
            
            results.append(result)
        
        print("-" * 100)
        print(f"\nMatched: {matched_count}/{len(df_input)} stocks")
        
        df_output = pd.DataFrame(results)
        output_columns = ['INPUT STOCK', 'GPT SYMBOL', 'STOCK SYMBOL', 'LISTED NAME', 'SHORT NAME', 
                         'SECURITY ID', 'EXCHANGE', 'INSTRUMENT', 'MATCH METHOD']
        df_output = df_output[output_columns]
        df_output.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        print(f"Saved mapped stocks to: {output_csv}")
        
        return {
            'success': True,
            'output_file': output_csv,
            'matched_count': matched_count,
            'total_count': len(df_input)
        }
        
    except Exception as e:
        print(f"Error in Step 4: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
