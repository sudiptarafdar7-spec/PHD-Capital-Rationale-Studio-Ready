import os
import pandas as pd
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict
from backend.utils.database import get_db_cursor

def fetch_cmp_from_dhan(api_key: str, security_id: str, exchange: str, instrument: str, call_datetime: datetime) -> float:
    url = "https://api.dhan.co/v2/charts/intraday"
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access-token": api_key
    }
    
    try:
        from_date = call_datetime.strftime("%Y-%m-%d %H:%M:00")
        to_date = (call_datetime + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:00")
        
        exchange = str(exchange).upper()
        instrument = str(instrument).upper()
        
        if instrument == "EQUITY":
            exchange_segment = f"{exchange}_EQ"
        else:
            exchange_segment = f"{exchange}_EQ"
        
        security_id_str = str(security_id).split(".")[0]
        
        payload = {
            "securityId": security_id_str,
            "exchangeSegment": exchange_segment,
            "instrument": "EQUITY",
            "interval": "5",
            "oi": False,
            "fromDate": from_date,
            "toDate": to_date
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code != 200:
            print(f"    ⚠️ API error ({response.status_code}): {response.text}")
            return None
        
        data = response.json()
        
        if "close" in data and len(data["close"]) > 0:
            return data["close"][0]
        else:
            return None
            
    except Exception as e:
        print(f"    ⚠️ API error: {str(e)}")
        return None

def fetch_cmp_for_stocks(job_id: str, job_folder: str) -> List[Dict]:
    print("\n" + "=" * 60)
    print("MANUAL RATIONALE STEP 1: FETCH CMP")
    print("=" * 60 + "\n")
    
    with get_db_cursor() as cursor:
        cursor.execute("SELECT payload FROM jobs WHERE id = %s", (job_id,))
        job = cursor.fetchone()
        if not job or not job['payload']:
            raise ValueError("Job payload not found")
        
        stocks = job['payload'].get('stocks', [])
        call_time_str = job['payload'].get('call_time', '')
        
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'dhan'")
        api_key_row = cursor.fetchone()
        dhan_api_key = api_key_row['key_value'] if api_key_row else None
    
    if not dhan_api_key:
        raise ValueError("Dhan API key not found. Please add it in API Keys settings.")
    
    if not call_time_str:
        call_datetime = datetime.now()
    else:
        try:
            call_datetime = datetime.strptime(call_time_str, "%Y-%m-%d %H:%M")
        except:
            call_datetime = datetime.now()
    
    print(f"🔑 Dhan API key found")
    print(f"📅 Call time: {call_datetime.strftime('%Y-%m-%d %H:%M')}")
    print(f"📊 Fetching CMP for {len(stocks)} stocks\n")
    
    def safe_float(value, default=0.0):
        """Safely convert value to float with fallback"""
        if value is None or value == '':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    for idx, stock in enumerate(stocks, 1):
        symbol = stock.get('symbol', '')
        security_id = stock.get('security_id', '')
        exchange = stock.get('exchange', 'NSE')
        instrument = stock.get('instrument', 'EQUITY')
        
        print(f"{idx}. {symbol}... ", end='', flush=True)
        
        cmp = fetch_cmp_from_dhan(dhan_api_key, security_id, exchange, instrument, call_datetime)
        
        if cmp is not None:
            stock['cmp'] = round(cmp, 2)
            entry = safe_float(stock.get('entry'))
            if entry > 0:
                change = ((cmp - entry) / entry) * 100
                stock['change_percent'] = round(change, 2)
            else:
                stock['change_percent'] = 0.0
            print(f"✓ CMP: ₹{cmp:.2f}")
        else:
            stock['cmp'] = 0.0
            stock['change_percent'] = 0.0
            print("✗ Failed")
    
    output_csv = os.path.join(job_folder, 'analysis', 'stocks_with_cmp.csv')
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    df = pd.DataFrame(stocks)
    df.to_csv(output_csv, index=False)
    
    print(f"\n✅ CMP data saved to: {output_csv}")
    
    return stocks
