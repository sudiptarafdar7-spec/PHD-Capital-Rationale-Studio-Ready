"""
Step 3: Fetch stock charts based on chart type
Creates stocks_with_charts.csv by adding CHART column
"""
import os
import csv
from backend.pipeline.premium.step04_generate_charts import generate_chart_for_stock

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
            security_id = stock['SECURITY ID']
            chart_type = stock['CHART TYPE']  # Daily, Weekly, or Monthly
            stock_symbol = stock['STOCK SYMBOL']
            
            # Map chart type to timeframe
            timeframe_map = {
                'Daily': '1D',
                'Weekly': '1W',
                'Monthly': '1M'
            }
            timeframe = timeframe_map.get(chart_type, '1D')
            
            if security_id:
                chart_filename = f"stock_{i+1}_{stock_symbol.replace(' ', '_')}.png"
                chart_path = os.path.join(charts_folder, chart_filename)
                
                success = generate_chart_for_stock(
                    security_id=security_id,
                    stock_name=stock_symbol,
                    chart_path=chart_path,
                    dhan_api_key=dhan_api_key,
                    timeframe=timeframe
                )
                
                stock['CHART'] = chart_filename if success else 'N/A'
            else:
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
        print(f"Error in step03_fetch_charts: {str(e)}")
        return {'success': False, 'error': str(e)}
