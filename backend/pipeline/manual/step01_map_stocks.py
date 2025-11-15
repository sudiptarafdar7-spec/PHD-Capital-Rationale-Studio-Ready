"""
Step 1: Map stocks with master CSV file
Creates mapped_master_file.csv with stock details from input
"""
import os
import csv
from rapidfuzz import process, fuzz

def run(job_folder, input_data):
    """
    Map stocks from input with master CSV file
    
    Args:
        job_folder: Path to job folder
        input_data: Dict with stocks array [{stockName, time, chartType, analysis}]
    
    Returns:
        dict: {success: bool, error: str (optional)}
    """
    try:
        stocks = input_data.get('stocks', [])
        call_date = input_data.get('callDate')
        
        if not stocks:
            return {'success': False, 'error': 'No stocks provided'}
        
        # Find master CSV file
        uploaded_files_dir = os.path.join('backend', 'uploaded_files')
        master_csv_path = None
        
        # Look for stock master CSV file
        for filename in os.listdir(uploaded_files_dir):
            if filename.endswith('.csv') and 'master' in filename.lower():
                master_csv_path = os.path.join(uploaded_files_dir, filename)
                break
        
        if not master_csv_path or not os.path.exists(master_csv_path):
            return {'success': False, 'error': 'Master CSV file not found'}
        
        # Read master CSV and map by trading symbol
        master_data = {}
        with open(master_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Filter EQUITY instruments with ES exchange type
                if row.get('SEM_INSTRUMENT_NAME', '').upper() != 'EQUITY':
                    continue
                if row.get('SEM_EXCH_INSTRUMENT_TYPE', '').upper() != 'ES':
                    continue
                
                # Map by trading symbol (SEM_TRADING_SYMBOL)
                trading_symbol = row.get('SEM_TRADING_SYMBOL', '')
                if trading_symbol:
                    master_data[trading_symbol.lower()] = {
                        'symbol': trading_symbol,
                        'listed_name': row.get('SM_SYMBOL_NAME', ''),
                        'short_name': row.get('SEM_CUSTOM_SYMBOL', trading_symbol),
                        'security_id': row.get('SEM_SMST_SECURITY_ID', ''),
                        'exchange': row.get('SEM_EXM_EXCH_ID', 'BSE'),
                        'instrument': row.get('SEM_INSTRUMENT_NAME', 'EQUITY')
                    }
        
        # Map stocks and create output CSV
        output_path = os.path.join(job_folder, 'analysis', 'mapped_master_file.csv')
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['DATE', 'TIME', 'STOCK SYMBOL', 'CHART TYPE', 
                          'LISTED NAME', 'SHORT NAME', 'SECURITY ID', 'EXCHANGE', 'INSTRUMENT', 'ANALYSIS']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for stock in stocks:
                stock_symbol = stock['stockName']  # Now contains trading symbol from autocomplete
                
                # Try exact match first (by trading symbol)
                match_data = master_data.get(stock_symbol.lower())
                
                # If no exact match, use fuzzy matching
                if not match_data:
                    matches = process.extract(
                        stock_symbol.lower(),
                        master_data.keys(),
                        scorer=fuzz.WRatio,
                        limit=1
                    )
                    if matches and matches[0][1] > 70:  # 70% confidence threshold
                        match_data = master_data[matches[0][0]]
                    else:
                        # No good match found - use stock symbol as is
                        match_data = {
                            'symbol': stock_symbol.upper(),
                            'listed_name': stock_symbol,
                            'short_name': stock_symbol,
                            'security_id': '',
                            'exchange': 'NSE',
                            'instrument': 'EQUITY'
                        }
                
                writer.writerow({
                    'DATE': call_date,
                    'TIME': stock['time'],
                    'STOCK SYMBOL': stock_symbol,
                    'CHART TYPE': stock['chartType'],
                    'LISTED NAME': match_data['listed_name'],
                    'SHORT NAME': match_data['short_name'],
                    'SECURITY ID': match_data['security_id'],
                    'EXCHANGE': match_data['exchange'],
                    'INSTRUMENT': match_data['instrument'],
                    'ANALYSIS': stock['analysis']
                })
        
        print(f"✓ Mapped {len(stocks)} stocks successfully")
        return {'success': True}
        
    except Exception as e:
        print(f"Error in step01_map_stocks: {str(e)}")
        return {'success': False, 'error': str(e)}
