"""
Transcript Rationale Step 7: Generate Charts
Generates premium stock charts using Dhan API (same design as Bulk Rationale)
"""

import os
import time
import json
import requests
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from backend.utils.database import get_db_cursor

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf

IST = pytz.timezone("Asia/Kolkata")
BASE_URL = "https://api.dhan.co/v2"
MARKET_OPEN_TIME = (9, 15)
MARKET_CLOSE_TIME = (15, 30)


def sanitize_value(value, default=''):
    """Convert NaN/None/nan values to empty string for JSON serialization"""
    if value is None:
        return default
    if isinstance(value, float) and (pd.isna(value) or np.isnan(value)):
        return default
    if pd.isna(value):
        return default
    return str(value) if value else default


def get_dhan_api_key():
    """Get Dhan API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'dhan'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def get_last_trading_day_close(dt_local: datetime) -> datetime:
    """Find the last trading day's closing time (3:30 PM)."""
    market_close_minutes = MARKET_CLOSE_TIME[0] * 60 + MARKET_CLOSE_TIME[1]
    requested_minutes = dt_local.hour * 60 + dt_local.minute
    
    if requested_minutes < market_close_minutes:
        search_date = dt_local.date() - timedelta(days=1)
    else:
        search_date = dt_local.date()
    
    while search_date.weekday() >= 5:
        search_date = search_date - timedelta(days=1)
    
    last_close = IST.localize(datetime(
        search_date.year, 
        search_date.month, 
        search_date.day,
        MARKET_CLOSE_TIME[0],
        MARKET_CLOSE_TIME[1],
        0
    ))
    
    return last_close


def parse_date(s: str) -> datetime.date:
    """Accept YYYY-MM-DD or DD-MM-YYYY or DD/MM/YYYY"""
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized DATE format: {s!r}")


def parse_time(s: str):
    """Accept HH:MM:SS, HH:MM or HH.MM.SS"""
    s = str(s).strip().replace(".", ":")
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.hour, dt.minute, getattr(dt, "second", 0)
        except ValueError:
            continue
    return 15, 30, 0


def _post(path: str, payload: dict, headers: dict, max_retries: int = 4) -> dict:
    """POST with retry on typical transient errors"""
    for attempt in range(max_retries):
        try:
            r = requests.post(f"{BASE_URL}{path}", headers=headers, json=payload, timeout=30)
            if r.ok:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
                continue
            raise
    raise RuntimeError("Max retries exceeded")


def _is_empty_payload(d: dict) -> bool:
    """Detect if Dhan returned empty arrays payload"""
    if not isinstance(d, dict) or not d:
        return True
    for key in ("open", "high", "low", "close", "volume", "timestamp"):
        arr = d.get(key, [])
        if isinstance(arr, list) and len(arr) > 0:
            return False
    return True


def zip_candles(d: dict) -> pd.DataFrame:
    """Convert Dhan arrays to DataFrame with IST index"""
    if _is_empty_payload(d):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    cols = ["open", "high", "low", "close", "volume", "timestamp"]
    n = min(len(d.get(c, [])) for c in cols if c in d)
    if n == 0:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    records = []
    for i in range(n):
        ts = d["timestamp"][i]
        dt_utc = datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.utc)
        dt_ist = dt_utc.astimezone(IST)
        records.append({
            "Date": dt_ist,
            "open": float(d["open"][i]),
            "high": float(d["high"][i]),
            "low": float(d["low"][i]),
            "close": float(d["close"][i]),
            "volume": int(d["volume"][i]),
        })

    df = pd.DataFrame(records)
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)
    return df


def fetch_daily_candles(sec_id: str, exch_seg: str, from_date: str, to_date: str, headers: dict) -> pd.DataFrame:
    """Fetch daily candles"""
    payload = {
        "securityId": sec_id,
        "exchangeSegment": exch_seg,
        "instrument": "EQUITY",
        "expiryCode": 0,
        "fromDate": from_date,
        "toDate": to_date,
    }
    data = _post("/charts/historical", payload, headers)
    return zip_candles(data)


def fetch_weekly_candles(sec_id: str, exch_seg: str, headers: dict, months: int = 24) -> pd.DataFrame:
    """Fetch weekly candles by aggregating daily data"""
    end_date = datetime.now(IST).date()
    start_date = end_date - relativedelta(months=months)
    
    df_daily = fetch_daily_candles(
        sec_id, exch_seg,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        headers
    )
    
    if df_daily.empty:
        return pd.DataFrame()
    
    df_weekly = df_daily.resample('W').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    return df_weekly


def fetch_monthly_candles(sec_id: str, exch_seg: str, headers: dict, months: int = 60) -> pd.DataFrame:
    """Fetch monthly candles by aggregating daily data"""
    end_date = datetime.now(IST).date()
    start_date = end_date - relativedelta(months=months)
    
    df_daily = fetch_daily_candles(
        sec_id, exch_seg,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        headers
    )
    
    if df_daily.empty:
        return pd.DataFrame()
    
    df_monthly = df_daily.resample('ME').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    return df_monthly


def render_chart(df: pd.DataFrame, symbol: str, chart_type: str, output_path: str):
    """Render and save chart using mplfinance"""
    if df.empty or len(df) < 5:
        return False
    
    mc = mpf.make_marketcolors(
        up='#26a69a',
        down='#ef5350',
        edge='inherit',
        wick='inherit',
        volume='#7f7f7f'
    )
    
    s = mpf.make_mpf_style(
        marketcolors=mc,
        gridcolor='#e0e0e0',
        gridstyle='-',
        facecolor='white',
        edgecolor='#333333',
        figcolor='white'
    )
    
    title = f"{symbol} - {chart_type.upper()} Chart"
    
    kwargs = {
        'type': 'candle',
        'style': s,
        'volume': True,
        'title': title,
        'figratio': (16, 9),
        'figscale': 1.2,
        'tight_layout': True,
        'savefig': dict(fname=output_path, dpi=150, bbox_inches='tight')
    }
    
    if len(df) >= 20:
        df['MA20'] = df['close'].rolling(window=20).mean()
        kwargs['addplot'] = [mpf.make_addplot(df['MA20'], color='orange', width=1)]
    
    mpf.plot(df, **kwargs)
    plt.close('all')
    
    return True


def run(job_folder, call_date=None, call_time=None):
    """Generate charts for all stocks"""
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 7: GENERATE CHARTS")
    print(f"{'='*60}\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        charts_folder = os.path.join(job_folder, 'charts')
        os.makedirs(charts_folder, exist_ok=True)
        
        input_csv = os.path.join(analysis_folder, 'stocks_with_cmp.csv')
        output_csv = os.path.join(analysis_folder, 'stocks_with_charts.csv')
        
        if not os.path.exists(input_csv):
            return {
                'success': False,
                'error': f'Stocks with CMP file not found: {input_csv}'
            }
        
        dhan_key = get_dhan_api_key()
        if not dhan_key:
            return {
                'success': False,
                'error': 'Dhan API key not found. Please add it in Settings → API Keys.'
            }
        
        headers = {
            'access-token': dhan_key,
            'Content-Type': 'application/json'
        }
        
        print(f"Reading stocks: {input_csv}")
        df = pd.read_csv(input_csv)
        df.columns = df.columns.str.strip().str.upper()
        
        print(f"Found {len(df)} stocks to process\n")
        
        chart_paths = []
        failed_charts = []
        success_count = 0
        
        for idx, row in df.iterrows():
            stock_symbol = row.get('STOCK SYMBOL', row.get('GPT SYMBOL', ''))
            security_id = row.get('SECURITY ID', '')
            exchange = row.get('EXCHANGE', 'NSE')
            chart_type = row.get('CHART TYPE', 'DAILY').upper()
            
            print(f"  [{idx+1}/{len(df)}] Generating {chart_type} chart for: {stock_symbol}")
            
            if not security_id or pd.isna(security_id) or str(security_id).strip() == '':
                print(f"    No security ID, skipping...")
                chart_paths.append('')
                failed_charts.append({
                    'index': int(idx),
                    'stock_name': sanitize_value(row.get('INPUT STOCK', stock_symbol)),
                    'symbol': sanitize_value(stock_symbol),
                    'short_name': sanitize_value(row.get('SHORT NAME', '')),
                    'security_id': '',
                    'error': 'No security ID'
                })
                continue
            
            exch_seg = "NSE_EQ" if exchange == "NSE" else "BSE_EQ"
            chart_filename = f"{stock_symbol.replace(' ', '_')}_{chart_type.lower()}_chart.png"
            chart_path = os.path.join(charts_folder, chart_filename)
            
            try:
                if chart_type == 'WEEKLY':
                    df_candles = fetch_weekly_candles(str(security_id), exch_seg, headers)
                elif chart_type == 'MONTHLY':
                    df_candles = fetch_monthly_candles(str(security_id), exch_seg, headers)
                else:
                    end_date = datetime.now(IST).date()
                    start_date = end_date - timedelta(days=180)
                    df_candles = fetch_daily_candles(
                        str(security_id), exch_seg,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"),
                        headers
                    )
                
                if df_candles.empty:
                    raise ValueError("No candle data received")
                
                success = render_chart(df_candles, stock_symbol, chart_type, chart_path)
                
                if success:
                    chart_paths.append(chart_path)
                    success_count += 1
                    print(f"    Chart saved: {chart_filename}")
                else:
                    chart_paths.append('')
                    failed_charts.append({
                        'index': int(idx),
                        'stock_name': sanitize_value(row.get('INPUT STOCK', stock_symbol)),
                        'symbol': sanitize_value(stock_symbol),
                        'short_name': sanitize_value(row.get('SHORT NAME', '')),
                        'security_id': sanitize_value(security_id),
                        'error': 'Chart rendering failed'
                    })
                    
            except Exception as e:
                print(f"    Error: {str(e)}")
                chart_paths.append('')
                failed_charts.append({
                    'index': int(idx),
                    'stock_name': sanitize_value(row.get('INPUT STOCK', stock_symbol)),
                    'symbol': sanitize_value(stock_symbol),
                    'short_name': sanitize_value(row.get('SHORT NAME', '')),
                    'security_id': sanitize_value(security_id),
                    'error': str(e)
                })
            
            if idx < len(df) - 1:
                time.sleep(0.5)
        
        df['CHART PATH'] = chart_paths
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        print(f"\nGenerated {success_count}/{len(df)} charts")
        print(f"Saved to: {output_csv}")
        
        if failed_charts:
            print(f"Failed charts: {len(failed_charts)}")
        
        return {
            'success': True,
            'output_file': output_csv,
            'success_count': success_count,
            'total_count': len(df),
            'failed_charts': failed_charts
        }
        
    except Exception as e:
        print(f"Error in Step 7: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
