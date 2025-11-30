"""
Bulk Rationale Step 5: Generate Charts
Generates stock charts using Dhan API
"""

import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backend.utils.database import get_db_cursor

try:
    import mplfinance as mpf
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')
except ImportError:
    mpf = None


def get_dhan_api_key():
    """Get Dhan API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'dhan'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def fetch_historical_data(security_id, exchange, date_str, headers):
    """Fetch 8 months of historical daily data"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        from_date = (dt - timedelta(days=240)).strftime("%Y-%m-%d")
        to_date = dt.strftime("%Y-%m-%d")
        
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": f"{exchange}_EQ",
            "instrument": "EQUITY",
            "expiryCode": 0,
            "fromDate": from_date,
            "toDate": to_date
        }
        
        response = requests.post(
            "https://api.dhan.co/v2/charts/historical",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('open') and len(data['open']) > 0:
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['timestamp'], unit='s'),
                    'Open': data['open'],
                    'High': data['high'],
                    'Low': data['low'],
                    'Close': data['close'],
                    'Volume': data['volume']
                })
                df.set_index('Date', inplace=True)
                return df
        return None
    except Exception as e:
        print(f"      Historical data error: {str(e)}")
        return None


def calculate_indicators(df):
    """Calculate technical indicators"""
    if len(df) < 20:
        return df
    
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['MA100'] = df['Close'].rolling(window=100).mean()
    df['MA200'] = df['Close'].rolling(window=200).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df


def generate_chart(df, stock_name, symbol, cmp, chart_path):
    """Generate candlestick chart with indicators"""
    if mpf is None:
        return False
    
    try:
        df = calculate_indicators(df)
        
        mc = mpf.make_marketcolors(
            up='#26a69a', down='#ef5350',
            edge='inherit',
            wick='inherit',
            volume='in'
        )
        
        s = mpf.make_mpf_style(
            base_mpf_style='charles',
            marketcolors=mc,
            gridstyle='-',
            gridcolor='#e0e0e0',
            facecolor='white',
            figcolor='white'
        )
        
        addplots = []
        
        if 'MA20' in df.columns and df['MA20'].notna().any():
            addplots.append(mpf.make_addplot(df['MA20'], color='#2196F3', width=1, label='MA20'))
        if 'MA50' in df.columns and df['MA50'].notna().any():
            addplots.append(mpf.make_addplot(df['MA50'], color='#FF9800', width=1, label='MA50'))
        if 'MA100' in df.columns and df['MA100'].notna().any():
            addplots.append(mpf.make_addplot(df['MA100'], color='#9C27B0', width=1, label='MA100'))
        
        if cmp:
            cmp_line = pd.Series([cmp] * len(df), index=df.index)
            addplots.append(mpf.make_addplot(cmp_line, color='#1976D2', width=1.5, linestyle='--', label=f'CMP: ₹{cmp}'))
        
        if 'RSI' in df.columns and df['RSI'].notna().any():
            addplots.append(mpf.make_addplot(df['RSI'], panel=2, color='#673AB7', width=1, ylabel='RSI'))
            addplots.append(mpf.make_addplot(pd.Series([70]*len(df), index=df.index), panel=2, color='red', width=0.5, linestyle='--'))
            addplots.append(mpf.make_addplot(pd.Series([30]*len(df), index=df.index), panel=2, color='green', width=0.5, linestyle='--'))
        
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=s,
            title=f"\n{stock_name} ({symbol})",
            ylabel='Price (₹)',
            volume=True,
            addplot=addplots if addplots else None,
            figsize=(12, 8),
            panel_ratios=(6, 2, 2) if 'RSI' in df.columns else (6, 2),
            returnfig=True
        )
        
        fig.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        return True
        
    except Exception as e:
        print(f"      Chart generation error: {str(e)}")
        return False


def run(job_folder):
    """
    Generate charts for all stocks
    
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
    print("BULK STEP 5: GENERATE STOCK CHARTS")
    print(f"{'='*60}\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        charts_folder = os.path.join(job_folder, 'charts')
        input_file = os.path.join(analysis_folder, 'stocks_with_cmp.csv')
        output_file = os.path.join(analysis_folder, 'stocks_with_charts.csv')
        
        os.makedirs(charts_folder, exist_ok=True)
        
        if not os.path.exists(input_file):
            return {
                'success': False,
                'error': f'Input file not found: {input_file}'
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
        
        print(f"📖 Loading stocks: {input_file}")
        df = pd.read_csv(input_file)
        print(f"✅ Loaded {len(df)} stocks")
        
        if 'CHART PATH' not in df.columns:
            df['CHART PATH'] = ''
        
        print(f"\n📈 Generating charts...")
        print("-" * 60)
        
        success_count = 0
        failed_count = 0
        
        for i, row in df.iterrows():
            stock_name = row.get('STOCK NAME', f'Row {i}')
            symbol = row.get('STOCK SYMBOL', '')
            security_id = str(row.get('SECURITY ID', '')).strip()
            
            if '.' in security_id:
                security_id = security_id.split('.')[0]
            
            if not security_id or security_id == '' or security_id == 'nan':
                print(f"  ⚠️ [{i+1}/{len(df)}] {stock_name:25} | Skipping - No SECURITY ID")
                failed_count += 1
                continue
            
            exchange = str(row.get('EXCHANGE', 'NSE')).strip()
            date_str = str(row.get('DATE', '')).strip()
            cmp = row.get('CMP', None)
            
            if pd.isna(cmp):
                cmp = None
            
            hist_data = fetch_historical_data(security_id, exchange, date_str, headers)
            
            if hist_data is None or len(hist_data) < 20:
                print(f"  ⚠️ [{i+1}/{len(df)}] {stock_name:25} | Insufficient data")
                failed_count += 1
                continue
            
            chart_filename = f"{security_id}_{symbol}_{date_str.replace('-', '')}.png"
            chart_path = os.path.join(charts_folder, chart_filename)
            
            if generate_chart(hist_data, stock_name, symbol, cmp, chart_path):
                relative_path = os.path.join('charts', chart_filename)
                df.at[i, 'CHART PATH'] = relative_path
                success_count += 1
                print(f"  ✓ [{i+1}/{len(df)}] {stock_name:25} | Chart saved")
            else:
                failed_count += 1
                print(f"  ✗ [{i+1}/{len(df)}] {stock_name:25} | Chart failed")
            
            time.sleep(0.5)
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n📊 Chart Generation Results:")
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
