"""
Bulk Rationale Step 3: Map Master File
Maps stock names to master file data for symbols and security IDs
"""

import os
import pandas as pd
from rapidfuzz import fuzz, process
from backend.utils.database import get_db_cursor
from backend.utils.path_utils import resolve_uploaded_file_path


def get_master_file_path():
    """Get master file path from database"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT file_path FROM uploaded_files 
            WHERE file_type = 'masterFile' 
            ORDER BY uploaded_at DESC LIMIT 1
        """)
        result = cursor.fetchone()
        if result and result['file_path']:
            return resolve_uploaded_file_path(result['file_path'])
    return None


def fuzzy_match_stock(stock_name, master_df, threshold=75):
    """
    Match stock name against master file using fuzzy matching
    """
    stock_name_clean = str(stock_name).strip().upper()
    
    search_columns = ['STOCK NAME', 'LISTED NAME', 'SHORT NAME', 'STOCK SYMBOL']
    available_cols = [col for col in search_columns if col in master_df.columns]
    
    if not available_cols:
        return None
    
    all_candidates = []
    for col in available_cols:
        candidates = master_df[col].dropna().astype(str).str.upper().tolist()
        all_candidates.extend([(c, col, i) for i, c in enumerate(candidates)])
    
    if not all_candidates:
        return None
    
    best_match = None
    best_score = 0
    best_idx = None
    
    for candidate, col, idx in all_candidates:
        score = fuzz.ratio(stock_name_clean, candidate)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate
            col_values = master_df[col].astype(str).str.upper().tolist()
            if candidate in col_values:
                best_idx = col_values.index(candidate)
    
    if best_idx is not None:
        return master_df.iloc[best_idx].to_dict()
    
    return None


def run(job_folder):
    """
    Map stocks to master file data
    
    Args:
        job_folder: Path to job directory
        
    Returns:
        dict: {
            'success': bool,
            'output_file': str,
            'error': str or None
        }
    """
    print("\n" + "=" * 60)
    print("BULK STEP 3: MAP MASTER FILE")
    print(f"{'='*60}\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        input_file = os.path.join(analysis_folder, 'bulk-input.csv')
        output_file = os.path.join(analysis_folder, 'mapped_master_file.csv')
        
        if not os.path.exists(input_file):
            return {
                'success': False,
                'error': f'Input CSV not found: {input_file}'
            }
        
        master_path = get_master_file_path()
        if not master_path or not os.path.exists(master_path):
            return {
                'success': False,
                'error': 'Master file not found. Please upload a master file in Settings.'
            }
        
        print(f"📖 Loading input CSV: {input_file}")
        df = pd.read_csv(input_file)
        print(f"✅ Loaded {len(df)} stocks")
        
        print(f"📖 Loading master file: {master_path}")
        master_df = pd.read_csv(master_path)
        print(f"✅ Master file has {len(master_df)} entries")
        
        new_columns = ['STOCK SYMBOL', 'SHORT NAME', 'LISTED NAME', 'SECURITY ID', 'EXCHANGE', 'INSTRUMENT']
        for col in new_columns:
            df[col] = ''
        
        print("\n🔄 Mapping stocks to master file...")
        print("-" * 60)
        
        matched = 0
        unmatched = 0
        
        for i, row in df.iterrows():
            stock_name = row.get('STOCK NAME', '')
            if not stock_name:
                unmatched += 1
                continue
            
            match = fuzzy_match_stock(stock_name, master_df)
            
            if match:
                df.at[i, 'STOCK SYMBOL'] = match.get('STOCK SYMBOL', match.get('SYMBOL', ''))
                df.at[i, 'SHORT NAME'] = match.get('SHORT NAME', '')
                df.at[i, 'LISTED NAME'] = match.get('LISTED NAME', match.get('STOCK NAME', ''))
                df.at[i, 'SECURITY ID'] = match.get('SECURITY ID', match.get('SECURITYID', ''))
                df.at[i, 'EXCHANGE'] = match.get('EXCHANGE', 'NSE')
                df.at[i, 'INSTRUMENT'] = match.get('INSTRUMENT', 'EQUITY')
                matched += 1
                print(f"  ✓ {stock_name:30} → {df.at[i, 'STOCK SYMBOL']} ({df.at[i, 'LISTED NAME']})")
            else:
                unmatched += 1
                print(f"  ✗ {stock_name:30} → No match found")
        
        final_columns = ['DATE', 'TIME', 'STOCK NAME', 'STOCK SYMBOL', 'SHORT NAME', 
                        'LISTED NAME', 'SECURITY ID', 'EXCHANGE', 'INSTRUMENT', 'ANALYSIS']
        
        for col in final_columns:
            if col not in df.columns:
                df[col] = ''
        
        df = df[final_columns]
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n📊 Mapping Results:")
        print(f"   ✓ Matched: {matched}")
        print(f"   ✗ Unmatched: {unmatched}")
        print(f"\n💾 Saved to: {output_file}")
        
        return {
            'success': True,
            'output_file': output_file,
            'matched': matched,
            'unmatched': unmatched
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
    
    result = run(test_folder)
    print(f"\n{'='*60}")
    print(f"Result: {'SUCCESS' if result.get('success') else 'FAILED'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print(f"{'='*60}")
