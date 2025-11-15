import os
import pandas as pd
from typing import List, Dict

def generate_manual_pdf(job_id: str, job_folder: str, stocks: List[Dict]) -> str:
    print("\n" + "=" * 60)
    print("MANUAL RATIONALE STEP 3: GENERATE PDF")
    print("=" * 60 + "\n")
    
    try:
        from backend.pipeline.premium.step08_generate_pdf import run as generate_premium_pdf
    except ImportError:
        raise ImportError("Premium PDF generator not available")
    
    analysis_folder = os.path.join(job_folder, 'analysis')
    csv_path = os.path.join(analysis_folder, 'stocks_with_charts.csv')
    
    if not os.path.exists(csv_path):
        raise ValueError(f"Stock data CSV not found: {csv_path}")
    
    print(f"📄 Generating PDF using Premium generator...")
    
    result = generate_premium_pdf(job_folder, job_id)
    
    if not result.get('success'):
        raise ValueError(result.get('error', 'PDF generation failed'))
    
    pdf_path = result.get('output_file', '')
    
    print(f"✅ PDF generated successfully: {pdf_path}\n")
    
    return pdf_path
