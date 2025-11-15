"""
Step 2: Fetch stock charts based on chart type
Creates stocks_with_charts.csv by adding CHART column
"""
import os
import csv
import pandas as pd
from datetime import datetime, timedelta
from backend.pipeline.premium.step04_generate_charts import (
    _post, zip_candles, make_premium_chart
)

def fetch_chart_data(security_id, dhan_api_key, timeframe='1D', days_back=180):
    """
    Fetch chart data from Dhan API
    
    Args:
        security_id: Security ID from master file
        dhan_api_key: Dhan API key
        timeframe: Chart timeframe (1D, 1W, 1M)
        days_back: Number of days of historical data
    
    Returns:
        DataFrame with OHLCV data or None
    """
    try:
        # Calculate date range
        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=days_back)
        
        # Prepare API request
        headers = {
            "access-token": dhan_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "expiryCode": 0,
            "fromDate": from_date.strftime("%Y-%m-%d"),
            "toDate": to_date.strftime("%Y-%m-%d")
        }
        
        # Fetch historical data
        response = _post("/v2/charts/historical", payload, headers)
        
        if not response or 'data' not in response:
            return None
        
        # Convert to DataFrame
        df = zip_candles(response)
        
        if df.empty:
            return None
        
        return df
        
    except Exception as e:
        print(f"Error fetching chart data: {str(e)}")
        return None

def generate_chart(security_id, stock_symbol, chart_path, dhan_api_key, timeframe='1D'):
    """
    Generate stock chart and save to file
    
    Args:
        security_id: Security ID
        stock_symbol: Stock trading symbol
        chart_path: Path to save chart image
        dhan_api_key: Dhan API key
        timeframe: Chart timeframe (1D, 1W, 1M)
    
    Returns:
        bool: True if successful
    """
    try:
        # Fetch chart data
        df = fetch_chart_data(security_id, dhan_api_key, timeframe)
        
        if df is None or df.empty:
            print(f"No chart data available for {stock_symbol}")
            return False
        
        # Prepare metadata
        meta = {
            'stock_name': stock_symbol,
            'chart_type': timeframe
        }
        
        # Generate chart
        make_premium_chart(df, meta, chart_path, chart_type=timeframe)
        
        return os.path.exists(chart_path)
        
    except Exception as e:
        print(f"Error generating chart for {stock_symbol}: {str(e)}")
        return False

def run(job_folder, dhan_api_key):
    """
    Fetch stock charts based on chart type (Daily/Weekly/Monthly)
    
    Args:
        job_folder: Path to job folder
        dhan_api_key: Dhan API key
    
    Returns:
        dict: {success: bool, error: str (optional)}
    """
    try:
        if not dhan_api_key:
            return {'success': False, 'error': 'Dhan API key not configured'}
        
        # Read stocks with CMP
        input_path = os.path.join(job_folder, 'analysis', 'stocks_with_cmp.csv')
        if not os.path.exists(input_path):
            return {'success': False, 'error': 'Stocks with CMP file not found'}
        
        stocks_data = []
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stocks_data.append(row)
        
        charts_folder = os.path.join(job_folder, 'charts')
        os.makedirs(charts_folder, exist_ok=True)
        
        # Generate chart for each stock based on chart type
        for i, stock in enumerate(stocks_data):
            security_id = stock.get('SECURITY ID', '')
            chart_type = stock.get('CHART TYPE', 'Daily')
            stock_symbol = stock.get('STOCK SYMBOL', '')
            
            # Map chart type to timeframe
            timeframe_map = {
                'Daily': '1D',
                'Weekly': '1W',
                'Monthly': '1M'
            }
            timeframe = timeframe_map.get(chart_type, '1D')
            
            if security_id and security_id.strip():
                chart_filename = f"stock_{i+1}_{stock_symbol.replace(' ', '_')}.png"
                chart_path = os.path.join(charts_folder, chart_filename)
                
                success = generate_chart(
                    security_id=security_id,
                    stock_symbol=stock_symbol,
                    chart_path=chart_path,
                    dhan_api_key=dhan_api_key,
                    timeframe=timeframe
                )
                
                stock['CHART'] = chart_filename if success else 'N/A'
            else:
                print(f"⚠️ Missing SECURITY ID for {stock_symbol}")
                stock['CHART'] = 'N/A'
        
        # Write output CSV
        output_path = os.path.join(job_folder, 'analysis', 'stocks_with_charts.csv')
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = list(stocks_data[0].keys()) if stocks_data else []
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(stocks_data)
        
        print(f"✓ Generated charts for {len(stocks_data)} stocks")
        return {'success': True}
        
    except Exception as e:
        print(f"Error in step02_fetch_charts: {str(e)}")
        return {'success': False, 'error': str(e)}
