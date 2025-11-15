"""
Step 2: Fetch Current Market Price for stocks
Creates stocks_with_cmp.csv by adding CMP column
"""
import os
import csv
from backend.pipeline.premium.step03_fetch_cmp import fetch_cmp_from_dhan

def run(job_folder, dhan_api_key):
    """
    Fetch CMP for all stocks from mapped CSV
    
    Args:
        job_folder: Path to job folder
        dhan_api_key: Dhan API key
    
    Returns:
        dict: {success: bool, error: str (optional)}
    """
    try:
        if not dhan_api_key:
            return {'success': False, 'error': 'Dhan API key not configured'}
        
        # Read mapped master file
        input_path = os.path.join(job_folder, 'analysis', 'mapped_master_file.csv')
        if not os.path.exists(input_path):
            return {'success': False, 'error': 'Mapped master file not found'}
        
        stocks_data = []
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stocks_data.append(row)
        
        # Fetch CMP for each stock
        for stock in stocks_data:
            security_id = stock['SECURITY ID']
            if security_id:
                cmp = fetch_cmp_from_dhan(security_id, dhan_api_key)
                stock['CMP'] = cmp if cmp else 'N/A'
            else:
                stock['CMP'] = 'N/A'
        
        # Write output CSV
        output_path = os.path.join(job_folder, 'analysis', 'stocks_with_cmp.csv')
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = list(stocks_data[0].keys()) if stocks_data else []
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(stocks_data)
        
        print(f"✓ Fetched CMP for {len(stocks_data)} stocks")
        return {'success': True}
        
    except Exception as e:
        print(f"Error in step02_fetch_cmp: {str(e)}")
        return {'success': False, 'error': str(e)}
