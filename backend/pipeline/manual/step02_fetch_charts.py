"""
Manual Step 2: Generate Stock Charts

Fetches candlestick stock charts from Dhan API and generates premium charts
with moving averages, RSI, and volume indicators.

Input: 
  - analysis/stocks_with_cmp.csv (from Step 1)
  - Dhan API key from database
Output: 
  - charts/*.png (chart images)
  - analysis/stocks_with_charts.csv
"""

import os
import time
import pandas as pd
import csv
from backend.pipeline.premium.step04_generate_charts import (
    parse_date, parse_time, get_daily_history, get_intraday_1m,
    resample_to, add_indicators, make_premium_chart, IST
)
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def normalize_chart_type(chart_type_value: str) -> str:
    """Normalize and validate CHART TYPE value (Daily/Weekly/Monthly)"""
    if pd.isna(chart_type_value) or not chart_type_value:
        return 'Daily'
    
    # Normalize: strip, uppercase for comparison
    normalized = str(chart_type_value).strip()
    normalized_upper = normalized.upper()
    
    # Map to valid values (case-insensitive)
    valid_chart_types = {'DAILY': 'Daily', 'WEEKLY': 'Weekly', 'MONTHLY': 'Monthly'}
    
    return valid_chart_types.get(normalized_upper, 'Daily')  # Default to Daily if invalid


def run(job_folder, dhan_api_key):
    """
    Generate candlestick charts for each stock using Dhan API
    
    Args:
        job_folder: Path to job directory
        dhan_api_key: Dhan API access token
        
    Returns:
        dict: {success: bool, error: str (optional)}
    """
    print("\n" + "=" * 60)
    print("MANUAL STEP 2: GENERATE STOCK CHARTS")
    print(f"{'='*60}\n")

    try:
        # Input/output paths
        analysis_folder = os.path.join(job_folder, 'analysis')
        stocks_csv = os.path.join(analysis_folder, 'stocks_with_cmp.csv')
        charts_dir = os.path.join(job_folder, 'charts')
        output_csv = os.path.join(analysis_folder, 'stocks_with_charts.csv')

        # Verify input file exists
        if not os.path.exists(stocks_csv):
            return {
                'success': False,
                'error': f'Stocks with CMP file not found: {stocks_csv}'
            }

        # Verify Dhan API key
        if not dhan_api_key:
            return {
                'success': False,
                'error': 'Dhan API key not found. Please add it in API Keys settings.'
            }

        # Create charts directory
        os.makedirs(charts_dir, exist_ok=True)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "access-token": dhan_api_key
        }
        print(f"🔑 Dhan API key found")

        # Load stocks
        print("📊 Loading stocks with CMP...")
        stocks_data = []
        with open(stocks_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames)
            for row in reader:
                stocks_data.append(row)
        
        print(f"✅ Loaded {len(stocks_data)} stocks\n")

        # Add CHART column if not exists
        if 'CHART' not in fieldnames:
            fieldnames.append('CHART')

        print(f"📈 Generating charts for {len(stocks_data)} stocks...")

        success_count = 0
        failed_count = 0

        # Process each stock
        for idx, stock in enumerate(stocks_data):
            try:
                security_id = str(stock.get("SECURITY ID", "")).strip()
                if '.' in security_id:
                    security_id = security_id.split('.')[0]

                if not security_id or security_id == '' or security_id == 'nan':
                    stock_symbol = stock.get("STOCK SYMBOL", "")
                    print(f"  ⚠️ [{idx+1}/{len(stocks_data)}] {stock_symbol} - Skipping: Missing SECURITY ID")
                    stock["CHART"] = ""
                    failed_count += 1
                    continue

                stock_symbol = str(stock.get("STOCK SYMBOL", "")).strip()
                short_name = str(stock.get("SHORT NAME", stock_symbol)).strip()
                exchange = str(stock.get("EXCHANGE", "NSE")).strip().upper()

                # Get CHART TYPE from CSV (default to "Daily" if missing/invalid)
                chart_type_raw = stock.get("CHART TYPE", "")
                chart_type = normalize_chart_type(chart_type_raw)

                exchange_segment = f"{exchange}_EQ" if exchange in ["NSE", "BSE"] else "NSE_EQ"

                print(f"  [{idx+1}/{len(stocks_data)}] {stock_symbol} ({chart_type}, {exchange_segment})...")

                # Parse date and time from CSV
                date_obj = parse_date(str(stock.get("DATE", "")).strip())
                time_str = str(stock.get("TIME", "")).strip()
                h, m, s = parse_time(time_str)
                end_dt_local = IST.localize(datetime(date_obj.year, date_obj.month, date_obj.day, h, m, s))

                # Historical window: last 8 months
                start_hist = date_obj - relativedelta(months=8)
                end_hist_non_inclusive = date_obj + timedelta(days=1)

                # Fetch historical daily data
                daily = get_daily_history(security_id, start_hist,
                                         end_hist_non_inclusive, headers,
                                         exchange_segment)

                # Fetch intraday data
                market_open = IST.localize(datetime(date_obj.year, date_obj.month, date_obj.day, 9, 15, 0))
                if end_dt_local <= market_open:
                    intraday = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
                else:
                    intraday = get_intraday_1m(security_id, market_open,
                                              end_dt_local, headers,
                                              exchange_segment)

                # Resample to timeframe
                df_tf = resample_to(daily, chart_type, intraday)

                if df_tf.empty:
                    raise ValueError("API returned no candles for this SECURITY ID / time window.")

                # Add indicators
                df_tf = add_indicators(df_tf)

                # Get CMP value and datetime from CSV
                cmp_value = None
                try:
                    cmp_str = str(stock.get("CMP", "")).strip()
                    if cmp_str and cmp_str.upper() != 'N/A':
                        cmp_value = float(cmp_str)
                        if pd.isna(cmp_value) or cmp_value == 0:
                            cmp_value = None
                except (ValueError, TypeError):
                    pass

                cmp_datetime = IST.localize(datetime(date_obj.year, date_obj.month, date_obj.day, h, m, s))

                # Generate chart filename and save
                fname = f"{security_id}_{chart_type}_{date_obj.strftime('%Y%m%d')}_{h:02d}{m:02d}{s:02d}.png"
                save_path = os.path.join(charts_dir, fname)
                meta = {
                    "SHORT NAME": short_name,
                    "CHART TYPE": chart_type,
                    "EXCHANGE": exchange
                }
                make_premium_chart(df_tf, meta, save_path, cmp_value, cmp_datetime)

                # Save relative path for CSV
                relative_path = fname

                stock["CHART"] = relative_path

                print(f"      ✅ Chart saved: {relative_path}")
                success_count += 1

                # Rate limiting
                time.sleep(1.5)

            except Exception as e:
                stock_symbol = stock.get("STOCK SYMBOL", f"Row {idx+1}")
                print(f"      ❌ {stock_symbol} - Error: {str(e)}")
                stock["CHART"] = ""
                failed_count += 1

        # Save output CSV
        print(f"\n💾 Saving output CSV...")
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(stocks_data)

        print(f"✅ Generated {success_count} charts")
        if failed_count > 0:
            print(f"⚠️  Failed: {failed_count} charts")
        print(f"   Output: analysis/stocks_with_charts.csv\n")

        return {
            'success': True,
            'output_file': output_csv,
            'error': None
        }

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
