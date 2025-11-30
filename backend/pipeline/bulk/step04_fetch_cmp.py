"""
Bulk Rationale Step 4: Fetch CMP
Fetches Current Market Price using Dhan API
"""

import os
import re
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from backend.utils.database import get_db_cursor


def normalize_date_format(date_str):
    """
    Normalize date to YYYY-MM-DD format.
    Handles multiple input formats:
    - YYYY-MM-DD (already correct)
    - DD/MM/YYYY
    - DD-MM-YYYY
    - MM/DD/YYYY
    - YYYY/MM/DD
    
    Returns date in YYYY-MM-DD format or None if parsing fails.
    """
    if not date_str or pd.isna(date_str):
        return None
    
    date_str = str(date_str).strip()
    
    # Already in YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # Try common date formats
    date_formats = [
        ('%d/%m/%Y', 'DD/MM/YYYY'),
        ('%d-%m-%Y', 'DD-MM-YYYY'),
        ('%Y/%m/%d', 'YYYY/MM/DD'),
        ('%m/%d/%Y', 'MM/DD/YYYY'),
        ('%d.%m.%Y', 'DD.MM.YYYY'),
    ]
    
    for fmt, name in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # Try pandas to_datetime as last resort
    try:
        dt = pd.to_datetime(date_str, dayfirst=True)
        return dt.strftime('%Y-%m-%d')
    except:
        pass
    
    return None


def get_dhan_api_key():
    """Get Dhan API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'dhan'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def fetch_cmp_for_stock(security_id, exchange, date_str, time_str, headers):
    """
    Fetch CMP for a single stock using Dhan intraday API
    """
    try:
        exchange_segment = f"{exchange}_EQ"
        
        dt_str = f"{date_str} {time_str}"
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        
        from_time = dt.replace(hour=9, minute=15, second=0)
        to_time = dt + timedelta(minutes=10)
        
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange_segment,
            "instrument": "EQUITY",
            "interval": "5",
            "fromDate": from_time.strftime("%Y-%m-%d %H:%M:%S"),
            "toDate": to_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        response = requests.post(
            "https://api.dhan.co/v2/charts/intraday",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('close') and len(data['close']) > 0:
                return data['close'][-1]
        
        historical_payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange_segment,
            "instrument": "EQUITY",
            "expiryCode": 0,
            "fromDate": (dt - timedelta(days=5)).strftime("%Y-%m-%d"),
            "toDate": dt.strftime("%Y-%m-%d")
        }
        
        response = requests.post(
            "https://api.dhan.co/v2/charts/historical",
            headers=headers,
            json=historical_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('close') and len(data['close']) > 0:
                return data['close'][-1]
        
        return None
        
    except Exception as e:
        print(f"      Error fetching CMP: {str(e)}")
        return None


def run(job_folder):
    """
    Fetch CMP for all stocks from Dhan API
    
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
    print("BULK STEP 4: FETCH CMP (CURRENT MARKET PRICE)")
    print(f"{'='*60}\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        input_file = os.path.join(analysis_folder, 'mapped_master_file.csv')
        output_file = os.path.join(analysis_folder, 'stocks_with_cmp.csv')
        
        if not os.path.exists(input_file):
            return {
                'success': False,
                'error': f'Mapped file not found: {input_file}'
            }
        
        dhan_key = get_dhan_api_key()
        if not dhan_key:
            return {
                'success': False,
                'error': 'Dhan API key not found. Please add it in Settings → API Keys.'
            }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "access-token": dhan_key
        }
        
        print(f"🔑 Dhan API key found")
        
        print(f"📖 Loading mapped stocks: {input_file}")
        df = pd.read_csv(input_file)
        print(f"✅ Loaded {len(df)} stocks")
        
        if 'CMP' not in df.columns:
            df['CMP'] = None
        
        print("\n💹 Fetching Current Market Prices...")
        print("-" * 60)
        
        success_count = 0
        failed_count = 0
        
        for i, row in df.iterrows():
            stock_name = row.get('STOCK NAME', f'Row {i}')
            security_id = str(row.get('SECURITY ID', '')).strip()
            
            if '.' in security_id:
                security_id = security_id.split('.')[0]
            
            if not security_id or security_id == '' or security_id == 'nan':
                print(f"  ⚠️ {stock_name:30} | Missing SECURITY ID, skipping")
                failed_count += 1
                continue
            
            exchange = str(row.get('EXCHANGE', 'NSE')).strip()
            raw_date = str(row.get('DATE', '')).strip()
            time_str = str(row.get('TIME', '10:00:00')).strip()
            
            # Normalize date format to YYYY-MM-DD
            date_str = normalize_date_format(raw_date)
            if not date_str:
                print(f"  ⚠️ {stock_name:30} | Invalid date format: {raw_date}, skipping")
                failed_count += 1
                continue
            
            # Log if date was converted
            if raw_date != date_str:
                print(f"  📅 Date converted: {raw_date} → {date_str}")
            
            cmp = fetch_cmp_for_stock(security_id, exchange, date_str, time_str, headers)
            
            if cmp:
                df.at[i, 'CMP'] = round(cmp, 2)
                success_count += 1
                print(f"  ✓ {stock_name:30} | CMP: ₹{cmp:.2f}")
            else:
                failed_count += 1
                print(f"  ✗ {stock_name:30} | Failed to fetch CMP")
            
            time.sleep(0.5)
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n📊 CMP Fetch Results:")
        print(f"   ✓ Success: {success_count}")
        print(f"   ✗ Failed: {failed_count}")
        print(f"\n💾 Saved to: {output_file}")
        
        return {
            'success': True,
            'output_file': output_file,
            'success_count': success_count,
            'failed_count': failed_count
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
