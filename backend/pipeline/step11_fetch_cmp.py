"""
Step 11: Fetch CMP (Current Market Price)

Fetches current market price from Dhan API for each stock at the time
it was mentioned in the video.

Input: 
  - analysis/stocks_with_date_time.csv (from Step 10)
  - Dhan API key from database
Output: 
  - analysis/stocks_with_cmp.csv
"""

import os
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from backend.utils.database import get_db_cursor


def get_dhan_api_key():
    """Fetch Dhan API key from database (decrypts automatically)"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT key_value 
                FROM api_keys 
                WHERE LOWER(provider) = 'dhan'
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            
            if result and result['key_value']:
                return result['key_value']
            else:
                raise ValueError(
                    "❌ Dhan API key not found in database.\n"
                    "   Please add it in Settings → API Keys → Dhan (provider: 'dhan')"
                )

    except Exception as e:
        raise Exception(f"Failed to fetch Dhan API key from database: {str(e)}")


def fetch_cmp_from_dhan(api_key, security_id, exchange, segment, instrument,
                        dt):
    """
    Fetch CMP from Dhan API for a specific stock at a specific time
    
    Args:
        api_key: Dhan API access token
        security_id: Security ID from master file
        exchange: Exchange (NSE/BSE)
        segment: Market segment (EQ, etc.)
        instrument: Instrument type (EQUITY)
        dt: Datetime when stock was mentioned
        
    Returns:
        float: Current Market Price or None
    """
    url = "https://api.dhan.co/v2/charts/intraday"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access-token": api_key
    }

    response = None
    try:
        # Format datetime range (mentioned time + 10 minutes) - HH:MM:00 format
        from_date = dt.strftime("%Y-%m-%d %H:%M:00")
        to_date = (dt + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:00")

        # Exchange segment formatting
        exchange = str(exchange).upper()
        segment = str(segment).upper()
        instrument = str(instrument).upper()

        if instrument == "EQUITY":
            exchange_segment = f"{exchange}_EQ"
        else:
            exchange_segment = f"{exchange}_{segment}"

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
        response = requests.post(url,
                                 headers=headers,
                                 json=payload,
                                 timeout=10)
        
        # Check for authentication errors
        if response.status_code == 401:
            raise RuntimeError(
                "❌ Dhan API authentication failed (401 Unauthorized).\n"
                "   Your Dhan API key is invalid or expired.\n"
                "   Please update it in Settings → API Keys → Dhan"
            )
        
        response.raise_for_status()

        data = response.json()

        # Extract CMP from response
        if "close" in data and len(data["close"]) > 0:
            cmp_value = data["close"][0]
            return cmp_value
        else:
            return None

    except requests.HTTPError as e:
        if response and response.status_code == 401:
            raise RuntimeError(
                "❌ Dhan API authentication failed (401 Unauthorized).\n"
                "   Your Dhan API key is invalid or expired.\n"
                "   Please update it in Settings → API Keys → Dhan"
            )
        print(f"    ⚠️ API error: {str(e)}")
        return None
    except Exception as e:
        print(f"    ⚠️ API error: {str(e)}")
        return None


def run(job_folder):
    """
    Fetch CMP for all stocks from Dhan API
    
    Args:
        job_folder: Path to job directory
        
    Returns:
        dict: Status, message, and output files
    """
    print("\n" + "=" * 60)
    print("STEP 11: Fetch CMP from Dhan API")
    print(f"{'='*60}\n")

    try:
        # Input/Output paths
        input_csv = os.path.join(job_folder, "analysis",
                                 "stocks_with_date_time.csv")
        output_csv = os.path.join(job_folder, "analysis",
                                  "stocks_with_cmp.csv")

        # Verify input file exists
        if not os.path.exists(input_csv):
            return {
                'status': 'failed',
                'message': f'Stocks with date/time file not found: {input_csv}'
            }

        # Get Dhan API key from database
        print("🔑 Retrieving Dhan API key from database...")
        api_key = get_dhan_api_key()
        
        if not api_key:
            return {
                'status': 'failed',
                'message': 'Dhan API key is empty or missing. Please add it in Settings → API Keys'
            }
        
        print(f"✅ Dhan API key found\n")

        # Load stocks file
        print("📖 Loading stocks with date/time...")
        df = pd.read_csv(input_csv)
        print(f"✅ Loaded {len(df)} stocks\n")

        # Ensure CMP column exists
        if "CMP" not in df.columns:
            df["CMP"] = None

        # Fetch CMP for each stock
        print("💹 Fetching Current Market Prices from Dhan API...")
        print("-" * 60)

        success_count = 0
        failed_count = 0

        for i, row in df.iterrows():
            try:
                # Parse datetime from DATE and START TIME (HH:MM:00 format)
                dt_str = f"{row['DATE']} {row['START TIME']}"
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:00")

                stock_symbol = row.get("STOCK SYMBOL", "")
                security_id = row.get("SECURITY ID", "")
                exchange = row.get("EXCHANGE", "")
                segment = row.get("SEGMENT", "")
                instrument = row.get("INSTRUMENT", "")

                # Skip if missing required data
                if not security_id or pd.isna(security_id) or str(
                        security_id).strip() == "":
                    print(
                        f"  ⚠️ {stock_symbol:15} | Missing Security ID, skipping"
                    )
                    failed_count += 1
                    continue

                # Fetch CMP from Dhan API
                cmp_value = fetch_cmp_from_dhan(api_key, security_id, exchange,
                                                segment, instrument, dt)

                if cmp_value is not None:
                    df.at[i, "CMP"] = cmp_value
                    print(
                        f"  ✅ {stock_symbol:15} | CMP: ₹{cmp_value:,.2f} @ {dt_str}"
                    )
                    success_count += 1
                else:
                    print(
                        f"  ⚠️ {stock_symbol:15} | No data available @ {dt_str}"
                    )
                    failed_count += 1

                # Add delay to avoid API rate limiting (429 errors)
                time.sleep(1.5)

            except Exception as e:
                stock_symbol = row.get("STOCK SYMBOL", f"Row {i}")
                print(f"  ❌ {stock_symbol:15} | Error: {str(e)}")
                failed_count += 1

        print("-" * 60)
        print(f"\n📊 CMP Fetch Summary:")
        print(f"   Total stocks: {len(df)}")
        print(f"   Successfully fetched: {success_count}")
        print(f"   Failed/No data: {failed_count}\n")

        # Reorder columns
        final_cols = [
            "STOCK NAME", "STOCK SYMBOL", "LISTED NAME", "SHORT NAME",
            "SECURITY ID", "EXCHANGE", "INSTRUMENT", "SEGMENT", "START TIME",
            "DATE", "CMP"
        ]

        # Only include columns that exist
        final_cols = [col for col in final_cols if col in df.columns]
        df = df.reindex(columns=final_cols)

        # Save output
        print(f"💾 Saving CMP data to: {output_csv}")

        # Ensure analysis directory exists
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)

        df.to_csv(output_csv, index=False)

        print(f"✅ Saved {len(df)} records")
        print(f"✅ Output: analysis/stocks_with_cmp.csv\n")

        return {
            'status': 'success',
            'message':
            f'Fetched CMP for {success_count} of {len(df)} stocks from Dhan API',
            'output_files': ['analysis/stocks_with_cmp.csv']
        }

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'status': 'failed', 'message': f'CMP fetch failed: {str(e)}'}


if __name__ == "__main__":
    # Test the step
    import sys
    if len(sys.argv) > 1:
        test_folder = sys.argv[1]
    else:
        test_folder = "backend/job_files/test_job"

    result = run(test_folder)
    print(f"\n{'='*60}")
    print(f"Result: {result['status'].upper()}")
    print(f"Message: {result['message']}")
    if 'output_files' in result:
        print(f"Output Files: {result['output_files']}")
    print(f"{'='*60}")
