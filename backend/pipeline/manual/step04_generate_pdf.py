"""
Step 4: Generate PDF report from stocks with charts
Creates manual_rationale.pdf
"""
import os
import csv
from backend.pipeline.premium.step08_generate_pdf import generate_pdf_report

def run(job_folder):
    """
    Generate PDF report from stocks with charts
    
    Args:
        job_folder: Path to job folder
    
    Returns:
        dict: {success: bool, error: str (optional)}
    """
    try:
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
        
        # Prepare PDF data
        pdf_data = {
            'date': stocks_data[0].get('DATE', ''),
            'stocks': []
        }
        
        for stock in stocks_data:
            pdf_data['stocks'].append({
                'name': stock['STOCK NAME'],
                'symbol': stock['STOCK SYMBOL'],
                'time': stock['TIME'],
                'cmp': stock.get('CMP', 'N/A'),
                'chart_type': stock['CHART TYPE'],
                'analysis': stock['ANALYSIS'],
                'chart_path': os.path.join(job_folder, 'charts', stock['CHART']) if stock.get('CHART') != 'N/A' else None
            })
        
        # Generate PDF
        pdf_path = os.path.join(job_folder, 'pdf', 'manual_rationale.pdf')
        
        success = generate_pdf_report(
            pdf_path=pdf_path,
            data=pdf_data,
            template_type='manual'
        )
        
        if not success:
            return {'success': False, 'error': 'Failed to generate PDF'}
        
        print(f"✓ Generated PDF report with {len(stocks_data)} stocks")
        return {'success': True}
        
    except Exception as e:
        print(f"Error in step04_generate_pdf: {str(e)}")
        return {'success': False, 'error': str(e)}
