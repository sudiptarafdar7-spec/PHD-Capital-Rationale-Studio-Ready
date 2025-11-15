"""
Manual Step 1: Fetch CMP (Current Market Price)

Fetches current market price from Dhan API for each stock at the time
of the call.

Input: 
  - analysis/input.csv (created at job creation with master data)
  - Dhan API key from database
Output: 
  - analysis/stocks_with_cmp.csv
"""

import os
import csv
import requests
import time
from datetime import datetime, timedelta


def fetch_cmp_from_dhan(api_key, security_id, exchange, instrument, dt):
    """
    Fetch CMP from Dhan API for a specific stock at a specific time
    
    Args:
        api_key: Dhan API access token
        security_id: Security ID from master file
        exchange: Exchange (NSE/BSE)
        instrument: Instrument type (EQUITY)
        dt: Datetime when stock was called
        
    Returns:
        float: Current Market Price or None
    """
    url = "https://api.dhan.co/v2/charts/intraday"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access-token": api_key
    }

    try:
        # Format datetime range (call time + 10 minutes)
        from_date = dt.strftime("%Y-%m-%d %H:%M:00")
        to_date = (dt + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:00")

        # Exchange segment formatting
        exchange = str(exchange).upper()
        instrument = str(instrument).upper()

        if instrument == "EQUITY":
            exchange_segment = f"{exchange}_EQ"
        else:
            exchange_segment = f"{exchange}_EQ"  # Default to EQ

        # Remove .0 if security_id is float-like
        security_id_str = str(security_id).split(".")[0]

        # API payload
        payload = {
            "securityId": security_id_str,
            "exchangeSegment": exchange_segment,
            "instrument": "EQUITY",
            "interval": "5",
            "oi": False,
            "fromDate": from_date,
            "toDate": to_date
        }

        # Make API request
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        # Log detailed error if request fails
        if response.status_code != 200:
            print(f"    ⚠️ API error ({response.status_code}): {response.text}")
            response.raise_for_status()

        data = response.json()

        # Extract CMP from response
        if "close" in data and len(data["close"]) > 0:
            cmp_value = data["close"][0]
            return cmp_value
        else:
            return None

    except Exception as e:
        print(f"    ⚠️ API error: {str(e)}")
        return None


def run(job_folder, dhan_api_key):
    """
    Fetch CMP for all stocks from Dhan API
    
    Args:
        job_folder: Path to job directory
        dhan_api_key: Dhan API access token
        
    Returns:
        dict: {success: bool, error: str (optional)}
    """
    print("\n" + "=" * 60)
    print("MANUAL STEP 1: FETCH CMP (CURRENT MARKET PRICE)")
    print(f"{'='*60}\n")

    try:
        # Input/Output paths
        analysis_folder = os.path.join(job_folder, 'analysis')
        input_csv = os.path.join(analysis_folder, 'input.csv')
        output_csv = os.path.join(analysis_folder, 'stocks_with_cmp.csv')

        # Verify input file exists
        if not os.path.exists(input_csv):
            return {
                'success': False,
                'error': f'Input CSV file not found: {input_csv}'
            }

        # Verify Dhan API key
        if not dhan_api_key:
            return {
                'success': False,
                'error': 'Dhan API key not found. Please add it in API Keys settings.'
            }

        print(f"🔑 Dhan API key found")

        # Load stocks file
        print("📖 Loading stocks from input.csv...")
        stocks_data = []
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                stocks_data.append(row)
        
        print(f"✅ Loaded {len(stocks_data)} stocks\n")

        # Add CMP column if not exists
        if 'CMP' not in fieldnames:
            fieldnames = list(fieldnames) + ['CMP']

        # Fetch CMP for each stock
        print("💹 Fetching Current Market Prices from Dhan API...")
        print("-" * 60)

        success_count = 0
        failed_count = 0

        for i, stock in enumerate(stocks_data):
            try:
                # Parse datetime from DATE and TIME columns
                date_str = str(stock.get('DATE', '')).strip()
                time_str = str(stock.get('TIME', '')).strip()
                
                if not date_str or not time_str:
                    stock_symbol = stock.get("STOCK SYMBOL", f"Row {i}")
                    print(f"  ⚠️ {stock_symbol:25} | Missing DATE or TIME, skipping")
                    stock['CMP'] = 'N/A'
                    failed_count += 1
                    continue

                # Combine date and time
                dt_str = f"{date_str} {time_str}:00"
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # Try without seconds
                    dt_str = f"{date_str} {time_str}"
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

                stock_symbol = stock.get("STOCK SYMBOL", "")
                security_id = stock.get("SECURITY ID", "")
                exchange = stock.get("EXCHANGE", "BSE")
                instrument = stock.get("INSTRUMENT", "EQUITY")

                # Skip if missing required data
                if not security_id or str(security_id).strip() == "":
                    print(f"  ⚠️ {stock_symbol:25} | Missing Security ID, skipping")
                    stock['CMP'] = 'N/A'
                    failed_count += 1
                    continue

                # Fetch CMP from Dhan API
                cmp_value = fetch_cmp_from_dhan(dhan_api_key, security_id, exchange, instrument, dt)

                if cmp_value is not None:
                    stock['CMP'] = cmp_value
                    print(f"  ✅ {stock_symbol:25} | CMP: ₹{cmp_value:,.2f} @ {dt_str}")
                    success_count += 1
                else:
                    stock['CMP'] = 'N/A'
                    print(f"  ⚠️ {stock_symbol:25} | No data available @ {dt_str}")
                    failed_count += 1

                # Add delay to avoid API rate limiting (429 errors)
                time.sleep(1.5)

            except Exception as e:
                stock_symbol = stock.get("STOCK SYMBOL", f"Row {i}")
                print(f"  ❌ {stock_symbol:25} | Error: {str(e)}")
                stock['CMP'] = 'N/A'
                failed_count += 1

        print("-" * 60)
        print(f"\n📊 CMP Fetch Summary:")
        print(f"   Total stocks: {len(stocks_data)}")
        print(f"   Successfully fetched: {success_count}")
        print(f"   Failed/No data: {failed_count}\n")

        # Save output with CMP column
        print(f"💾 Saving CMP data to: {output_csv}")

        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(stocks_data)

        print(f"✅ Saved {len(stocks_data)} records")
        print(f"✅ Output: analysis/stocks_with_cmp.csv\n")

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
