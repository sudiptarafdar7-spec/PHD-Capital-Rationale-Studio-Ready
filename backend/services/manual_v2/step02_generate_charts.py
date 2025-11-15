import os
import pandas as pd
from datetime import datetime
from typing import List, Dict
from backend.utils.database import get_db_cursor

try:
    from backend.pipeline.premium.step04_generate_charts import (
        get_daily_history, get_intraday_1m, add_indicators, resample_to,
        make_premium_chart, parse_date, parse_time, IST
    )
    CHART_GENERATION_AVAILABLE = True
except ImportError:
    CHART_GENERATION_AVAILABLE = False
    print("⚠️  Premium chart generation functions not available")

def generate_charts_for_stocks(job_id: str, job_folder: str, stocks: List[Dict]) -> List[Dict]:
    print("\n" + "=" * 60)
    print("MANUAL RATIONALE STEP 2: GENERATE CHARTS")
    print("=" * 60 + "\n")
    
    if not CHART_GENERATION_AVAILABLE:
        print("⚠️  Skipping chart generation - premium functions not available")
        return stocks
    
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'dhan'")
        api_key_row = cursor.fetchone()
        dhan_api_key = api_key_row['key_value'] if api_key_row else None
        
        cursor.execute("SELECT payload FROM jobs WHERE id = %s", (job_id,))
        job = cursor.fetchone()
        call_time_str = job['payload'].get('call_time', '') if job and job['payload'] else ''
    
    if not dhan_api_key:
        raise ValueError("Dhan API key not found")
    
    if not call_time_str:
        call_datetime = datetime.now()
    else:
        try:
            call_datetime = datetime.strptime(call_time_str, "%Y-%m-%d %H:%M")
        except:
            call_datetime = datetime.now()
    
    call_datetime_ist = IST.localize(call_datetime.replace(tzinfo=None))
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access-token": dhan_api_key
    }
    
    charts_folder = os.path.join(job_folder, 'charts')
    os.makedirs(charts_folder, exist_ok=True)
    
    print(f"📊 Generating charts for {len(stocks)} stocks\n")
    
    for idx, stock in enumerate(stocks, 1):
        symbol = stock.get('symbol', '')
        security_id = stock.get('security_id', '')
        exchange = stock.get('exchange', 'NSE')
        cmp = stock.get('cmp', 0)
        
        print(f"{idx}. {symbol}... ", end='', flush=True)
        
        try:
            exchange_segment = f"{exchange.upper()}_EQ"
            
            from datetime import timedelta
            from dateutil.relativedelta import relativedelta
            
            end_date = call_datetime.date() + timedelta(days=1)
            start_date = end_date - relativedelta(months=8)
            
            df_daily = get_daily_history(
                security_id, start_date, end_date, headers, exchange_segment
            )
            
            call_date = call_datetime_ist.date()
            market_open = IST.localize(datetime.combine(call_date, datetime.strptime("09:15", "%H:%M").time()))
            market_close = call_datetime_ist
            
            df_1m = get_intraday_1m(security_id, market_open, market_close, headers, exchange_segment)
            
            df_resampled = resample_to(df_daily, "Daily", df_1m)
            df_with_indicators = add_indicators(df_resampled)
            
            chart_filename = f"{symbol}_chart.png"
            chart_path = os.path.join(charts_folder, chart_filename)
            
            meta = {
                "symbol": symbol,
                "listed_name": stock.get('listed_name', symbol)
            }
            
            make_premium_chart(
                df_with_indicators, meta, chart_path,
                cmp_value=cmp, cmp_datetime=call_datetime_ist
            )
            
            stock['chart_path'] = chart_filename
            print(f"✓ Chart saved")
            
        except Exception as e:
            print(f"✗ Failed: {str(e)}")
            stock['chart_path'] = ''
    
    output_csv = os.path.join(job_folder, 'analysis', 'stocks_with_charts.csv')
    df = pd.DataFrame(stocks)
    df.to_csv(output_csv, index=False)
    
    print(f"\n✅ Charts saved to: {charts_folder}")
    print(f"✅ Data saved to: {output_csv}")
    
    return stocks
