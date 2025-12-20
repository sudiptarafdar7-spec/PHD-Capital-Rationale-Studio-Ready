"""
Transcript Rationale Step 8: Generate PDF
Creates a professional PDF report from stocks_with_charts.csv with premium blue theme
(Same design as Bulk Rationale)
"""

import os
import re
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, Flowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage, ImageDraw
from datetime import datetime
import psycopg2


def get_db_connection():
    """Get database connection"""
    import os
    return psycopg2.connect(os.environ["DATABASE_URL"])


def sanitize_filename(s: str) -> str:
    """Sanitize string for safe filesystem usage"""
    return str(s).strip().replace(" ", "_").replace(":", "-").replace("/", "-").replace("\\", "-")


def fetch_pdf_config(job_id: str):
    """Fetch PDF configuration from database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT c.channel_name, c.channel_logo_path, j.title, j.date, j.youtube_url, c.platform
            FROM jobs j
            LEFT JOIN channels c ON j.channel_id = c.id
            WHERE j.id = %s
        """, (job_id,))
        job_row = cursor.fetchone()
        if not job_row:
            raise ValueError(f"Job {job_id} not found")
        
        channel_name, channel_logo_path_raw, title, input_date, youtube_url, platform = job_row
        
        channel_logo_path = None
        if channel_logo_path_raw:
            if os.path.isabs(channel_logo_path_raw):
                channel_logo_path = channel_logo_path_raw
            else:
                possible_paths = [
                    f"/home/runner/workspace/backend/channel_logos/{channel_logo_path_raw}",
                    f"backend/channel_logos/{channel_logo_path_raw}",
                    f"/home/runner/workspace/backend/uploaded_files/{channel_logo_path_raw}",
                    f"backend/uploaded_files/{channel_logo_path_raw}",
                    channel_logo_path_raw
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        channel_logo_path = path
                        break
        
        cursor.execute("""
            SELECT company_name, registration_details, disclaimer_text, disclosure_text, company_data
            FROM pdf_template
            ORDER BY id DESC
            LIMIT 1
        """)
        template_row = cursor.fetchone()
        if template_row:
            company_name, registration_details, disclaimer_text, disclosure_text, company_data = template_row
        else:
            company_name = "PHD CAPITAL PVT LTD"
            registration_details = "SEBI Regd No - INH000016126"
            disclaimer_text = None
            disclosure_text = None
            company_data = None
        
        cursor.execute("""
            SELECT file_type, file_path, file_name
            FROM uploaded_files
            WHERE file_type IN ('companyLogo', 'customFont')
            ORDER BY uploaded_at DESC
        """)
        uploaded_files = cursor.fetchall()
        
        company_logo_path = None
        font_regular_path = None
        font_bold_path = None
        
        for file_type, file_path, file_name in uploaded_files:
            if file_type == 'companyLogo' and not company_logo_path:
                company_logo_path = file_path
            elif file_type == 'customFont':
                if 'bold' in file_name.lower() and not font_bold_path:
                    font_bold_path = file_path
                elif not font_regular_path:
                    font_regular_path = file_path
        
        input_date_str = None
        if input_date:
            if hasattr(input_date, 'strftime'):
                input_date_str = input_date.strftime('%Y-%m-%d')
            else:
                input_date_str = str(input_date)
        
        return {
            'channel_name': channel_name or "Platform",
            'channel_logo_path': channel_logo_path,
            'title': title or "Transcript Rationale Report",
            'input_date': input_date_str,
            'youtube_url': youtube_url,
            'platform': platform,
            'company_name': company_name,
            'registration_details': registration_details,
            'disclaimer_text': disclaimer_text,
            'disclosure_text': disclosure_text,
            'company_data': company_data,
            'company_logo_path': company_logo_path,
            'font_regular_path': font_regular_path,
            'font_bold_path': font_bold_path,
        }
        
    finally:
        cursor.close()
        conn.close()


def create_circular_logo(input_path: str, output_path: str, size: int = 100):
    """Create circular version of logo"""
    try:
        img = PILImage.open(input_path).convert("RGBA")
        img = img.resize((size, size), PILImage.LANCZOS)
        
        mask = PILImage.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        output = PILImage.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(img, mask=mask)
        output.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"Error creating circular logo: {e}")
        return False


def run(job_folder, job_id=None):
    """Generate PDF report"""
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 8: GENERATE PDF")
    print(f"{'='*60}\n")
    
    try:
        analysis_folder = os.path.join(job_folder, 'analysis')
        charts_folder = os.path.join(job_folder, 'charts')
        
        input_csv = os.path.join(analysis_folder, 'stocks_with_charts.csv')
        
        if not os.path.exists(input_csv):
            return {
                'success': False,
                'error': f'Stocks with charts file not found: {input_csv}'
            }
        
        print(f"Reading stocks: {input_csv}")
        df = pd.read_csv(input_csv)
        df.columns = df.columns.str.strip().str.upper()
        
        if job_id:
            config = fetch_pdf_config(job_id)
        else:
            config = {
                'channel_name': 'Platform',
                'title': 'Transcript Rationale Report',
                'company_name': 'PHD CAPITAL PVT LTD',
                'registration_details': 'SEBI Regd No - INH000016126',
            }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        channel_name_safe = sanitize_filename(config.get('channel_name', 'report'))
        pdf_filename = f"transcript_rationale_{channel_name_safe}_{timestamp}.pdf"
        pdf_folder = os.path.join(job_folder, 'pdf')
        os.makedirs(pdf_folder, exist_ok=True)
        pdf_path = os.path.join(pdf_folder, pdf_filename)
        
        print(f"Generating PDF: {pdf_filename}")
        print(f"Stocks count: {len(df)}")
        
        PREMIUM_BLUE = colors.Color(0.0, 0.32, 0.65)
        LIGHT_BLUE = colors.Color(0.9, 0.95, 1.0)
        
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=PREMIUM_BLUE,
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        stock_title_style = ParagraphStyle(
            'StockTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=PREMIUM_BLUE,
            spaceBefore=12,
            spaceAfter=6
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY
        )
        
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.gray,
            leading=10,
            alignment=TA_JUSTIFY
        )
        
        story = []
        
        story.append(Paragraph(config.get('title', 'Transcript Rationale Report'), title_style))
        story.append(Spacer(1, 6))
        
        subtitle = f"{config.get('channel_name', '')} | {config.get('input_date', datetime.now().strftime('%Y-%m-%d'))}"
        story.append(Paragraph(subtitle, ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=11, textColor=colors.gray, alignment=TA_CENTER)))
        story.append(Spacer(1, 20))
        
        for idx, row in df.iterrows():
            stock_symbol = row.get('STOCK SYMBOL', row.get('GPT SYMBOL', 'Unknown'))
            listed_name = row.get('LISTED NAME', stock_symbol)
            short_name = row.get('SHORT NAME', '')
            exchange = row.get('EXCHANGE', 'NSE')
            cmp = row.get('CMP', '')
            chart_type = row.get('CHART TYPE', 'DAILY')
            analysis = row.get('ANALYSIS', '')
            chart_path = row.get('CHART PATH', '')
            
            stock_header = f"{stock_symbol}"
            if listed_name and listed_name != stock_symbol:
                stock_header += f" ({listed_name})"
            stock_header += f" - {exchange}"
            
            story.append(Paragraph(stock_header, stock_title_style))
            
            info_text = []
            if cmp:
                info_text.append(f"<b>CMP:</b> Rs. {cmp}")
            if chart_type:
                info_text.append(f"<b>Chart:</b> {chart_type}")
            if info_text:
                story.append(Paragraph(" | ".join(info_text), body_style))
                story.append(Spacer(1, 6))
            
            if chart_path and os.path.exists(chart_path):
                try:
                    img = Image(chart_path, width=6.5*inch, height=3.5*inch)
                    story.append(img)
                    story.append(Spacer(1, 10))
                except Exception as e:
                    print(f"Error adding chart for {stock_symbol}: {e}")
            
            if analysis:
                analysis_clean = str(analysis).replace('\n', '<br/>')
                story.append(Paragraph(f"<b>Analysis:</b> {analysis_clean}", body_style))
            
            story.append(Spacer(1, 20))
            
            if idx < len(df) - 1:
                story.append(Spacer(1, 10))
        
        story.append(Spacer(1, 30))
        
        disclaimer = config.get('disclaimer_text', """
        <b>Disclaimer:</b> This report is for informational purposes only and should not be construed as investment advice. 
        The information contained herein is obtained from sources believed to be reliable, but its accuracy or completeness 
        is not guaranteed. Past performance is not indicative of future results. Investment in securities market is subject 
        to market risks. Read all related documents carefully before investing.
        """)
        story.append(Paragraph(disclaimer, disclaimer_style))
        
        doc.build(story)
        
        print(f"PDF generated successfully: {pdf_path}")
        
        if job_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE jobs 
                    SET pdf_path = %s, updated_at = %s
                    WHERE id = %s
                """, (pdf_path, datetime.now(), job_id))
                conn.commit()
            finally:
                cursor.close()
                conn.close()
        
        return {
            'success': True,
            'output_file': pdf_path,
            'pdf_path': pdf_path,
            'stock_count': len(df)
        }
        
    except Exception as e:
        print(f"Error in Step 8: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
