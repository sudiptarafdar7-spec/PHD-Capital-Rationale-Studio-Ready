"""
Transcript Rationale Step 6: Fetch CMP
Fetches Current Market Price using Dhan API (same as Bulk Rationale)
Uses date and time from jobs table
"""

import os
import re
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from backend.utils.database import get_db_cursor


def normalize_date_format(date_str):
    """Normalize date to YYYY-MM-DD format"""
    if not date_str or pd.isna(date_str):
        return None
    
    date_str = str(date_str).strip()
    
    if not date_str or date_str.lower() in ['nan', 'none', 'nat', '']:
        return None
    
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    try:
        num_val = float(date_str)
        if 40000 < num_val < 60000:
            excel_epoch = datetime(1899, 12, 30)
            dt = excel_epoch + timedelta(days=int(num_val))
            return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        pass
    
    date_formats = [
        '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
        '%Y/%m/%d', '%Y.%m.%d',
        '%m/%d/%Y', '%m-%d-%Y',
        '%d/%m/%y', '%d-%m-%y',
        '%d-%b-%Y', '%d %b %Y',
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year < 100:
                dt = dt.replace(year=dt.year + 2000)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    try:
        dt = pd.to_datetime(date_str, dayfirst=True)
        if not pd.isna(dt):
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


def fetch_cmp_from_dhan(security_id, exchange, date_str, time_str, api_key):
    """Fetch CMP from Dhan API with intelligent market hours handling"""
    
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return None, "Invalid date format"
    
    is_market_hours = False
    if time_str:
        try:
            time_parts = time_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            if (hour > 9 or (hour == 9 and minute >= 15)) and (hour < 15 or (hour == 15 and minute <= 30)):
                is_market_hours = True
        except:
            pass
    
    exch_segment = "NSE_EQ" if exchange == "NSE" else "BSE_EQ"
    
    headers = {
        'access-token': api_key,
        'Content-Type': 'application/json'
    }
    
    if is_market_hours:
        from_date = date_obj.strftime('%Y-%m-%d')
        to_date = from_date
        
        url = "https://api.dhan.co/v2/charts/intraday"
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exch_segment,
            "instrument": "EQUITY",
            "interval": "1",
            "fromDate": from_date,
            "toDate": to_date
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('close') and len(data['close']) > 0:
                    return data['close'][-1], None
        except Exception as e:
            print(f"Intraday API error: {str(e)}")
    
    from_date = (date_obj - timedelta(days=10)).strftime('%Y-%m-%d')
    to_date = date_obj.strftime('%Y-%m-%d')
    
    url = "https://api.dhan.co/v2/charts/historical"
    payload = {
        "securityId": str(security_id),
        "exchangeSegment": exch_segment,
        "instrument": "EQUITY",
        "expiryCode": 0,
        "fromDate": from_date,
        "toDate": to_date
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('close') and len(data['close']) > 0:
                return data['close'][-1], None
    except Exception as e:
        return None, str(e)
    
    return None, "No data available"


def run(job_folder, call_date=None, call_time=None):
    """Fetch CMP for all stocks"""
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 6: FETCH CMP")
    print(f"{'='*60}\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        input_csv = os.path.join(analysis_folder, 'stocks_with_analysis.csv')
        output_csv = os.path.join(analysis_folder, 'stocks_with_cmp.csv')
        
        if not os.path.exists(input_csv):
            return {
                'success': False,
                'error': f'Stocks with analysis file not found: {input_csv}'
            }
        
        dhan_key = get_dhan_api_key()
        if not dhan_key:
            return {
                'success': False,
                'error': 'Dhan API key not found. Please add it in Settings → API Keys.'
            }
        
        print(f"Reading stocks: {input_csv}")
        df = pd.read_csv(input_csv)
        df.columns = df.columns.str.strip().str.upper()
        
        if call_date:
            call_date = normalize_date_format(call_date)
        if not call_date:
            call_date = datetime.now().strftime('%Y-%m-%d')
        
        if not call_time:
            call_time = '15:30:00'
        
        print(f"Using date: {call_date}, time: {call_time}")
        print(f"Found {len(df)} stocks to process\n")
        
        cmps = []
        success_count = 0
        
        for idx, row in df.iterrows():
            stock_symbol = row.get('STOCK SYMBOL', row.get('GPT SYMBOL', ''))
            security_id = row.get('SECURITY ID', '')
            exchange = row.get('EXCHANGE', 'NSE')
            
            print(f"  [{idx+1}/{len(df)}] Fetching CMP for: {stock_symbol}")
            
            if not security_id or pd.isna(security_id) or str(security_id).strip() == '':
                print(f"    No security ID, skipping...")
                cmps.append('')
                continue
            
            cmp, error = fetch_cmp_from_dhan(security_id, exchange, call_date, call_time, dhan_key)
            
            if cmp is not None:
                cmps.append(round(cmp, 2))
                success_count += 1
                print(f"    CMP: {cmp}")
            else:
                cmps.append('')
                print(f"    Failed: {error}")
            
            if idx < len(df) - 1:
                time.sleep(0.3)
        
        df['CMP'] = cmps
        df['DATE'] = call_date
        df['TIME'] = call_time
        
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        print(f"\nFetched CMP for {success_count}/{len(df)} stocks")
        print(f"Saved to: {output_csv}")
        
        return {
            'success': True,
            'output_file': output_csv,
            'success_count': success_count,
            'total_count': len(df)
        }
        
    except Exception as e:
        print(f"Error in Step 6: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
