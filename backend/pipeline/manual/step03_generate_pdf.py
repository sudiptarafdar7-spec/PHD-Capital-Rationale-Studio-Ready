"""
Step 3: Generate PDF report from stocks with charts
Creates manual_rationale.pdf
"""
import os
import csv

def run(job_folder):
    """
    Generate PDF report from stocks with charts
    
    Args:
        job_folder: Path to job folder
    
    Returns:
        dict: {success: bool, error: str (optional)}
    """
    try:
        # Import the premium PDF generation step
        from backend.pipeline.premium.step08_generate_pdf import run as generate_premium_pdf
        
        # Read stocks with charts
        input_path = os.path.join(job_folder, 'analysis', 'stocks_with_charts.csv')
        if not os.path.exists(input_path):
            return {'success': False, 'error': 'Stocks with charts file not found'}
        
        stocks_data = []
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stocks_data.append(row)
        
        if not stocks_data:
            return {'success': False, 'error': 'No stock data found'}
        
        # Call premium PDF generation (it handles manual rationale too)
        result = generate_premium_pdf(job_folder)
        
        if not result.get('success'):
            return result
        
        print(f"✓ Generated PDF report with {len(stocks_data)} stocks")
        return {'success': True}
        
    except Exception as e:
        print(f"Error in step03_generate_pdf: {str(e)}")
        return {'success': False, 'error': str(e)}
