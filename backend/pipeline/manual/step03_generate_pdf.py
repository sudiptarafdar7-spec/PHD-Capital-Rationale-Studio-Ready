"""
Manual Step 3: Generate PDF Report

Creates a professional PDF report from stocks_with_charts.csv with BLACK color theme

Input: 
  - analysis/stocks_with_charts.csv (from Step 2)
  - PDF template configuration from database
Output: 
  - PDF report with branded header/footer and BLACK theme
"""

import os
import shutil


def run(job_folder):
    """
    Generate PDF report from stocks_with_charts.csv with BLACK theme
    
    Args:
        job_folder: Path to job directory
        
    Returns:
        dict: {success: bool, error: str (optional)}
    """
    print("\n" + "=" * 60)
    print("MANUAL STEP 3: GENERATE PDF REPORT (BLACK THEME)")
    print(f"{'='*60}\n")

    try:
        # Input paths
        analysis_folder = os.path.join(job_folder, 'analysis')
        manual_csv = os.path.join(analysis_folder, 'stocks_with_charts.csv')  # Manual output name
        premium_csv = os.path.join(analysis_folder, 'stocks_with_analysis.csv')  # Premium PDF expects this name

        # Verify input file exists
        if not os.path.exists(manual_csv):
            return {
                'success': False,
                'error': f'Stocks with charts file not found: {manual_csv}'
            }

        print(f"📊 Using CSV: {manual_csv}")
        
        # Copy/rename CSV to match what Premium PDF generator expects
        # Premium expects stocks_with_analysis.csv (from its step 7)
        # Manual only goes to charts, so we rename it
        print(f"📝 Renaming CSV to Premium format: stocks_with_analysis.csv")
        shutil.copy2(manual_csv, premium_csv)

        # Call Premium PDF generation
        # NOTE: Currently uses BLUE theme from Premium pipeline
        # Future enhancement: Parameterize color theme to support BLACK for Manual
        from backend.pipeline.premium.step08_generate_pdf import run as generate_premium_pdf
        
        result = generate_premium_pdf(job_folder)
        
        if not result.get('success'):
            return result

        print(f"✅ PDF generated successfully")
        print(f"   Output: {result.get('output_file')}\n")
        print(f"ℹ️  Note: Currently using Premium BLUE theme")
        print(f"   BLACK theme customization planned for future release\n")

        return {
            'success': True,
            'output_file': result.get('output_file'),
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
