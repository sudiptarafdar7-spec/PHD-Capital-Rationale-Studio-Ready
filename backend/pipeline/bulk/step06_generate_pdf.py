"""
Bulk Rationale Step 6: Generate PDF Report
Creates professional PDF report with premium blue design
"""

import os
import re
import pandas as pd
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
from backend.utils.database import get_db_cursor
from backend.utils.path_utils import resolve_uploaded_file_path


PRIMARY_BLUE = colors.HexColor('#1565C0')
ACCENT_GOLD = colors.HexColor('#D4AF37')
LIGHT_BLUE = colors.HexColor('#E3F2FD')
DARK_BLUE = colors.HexColor('#0D47A1')


def safe_str(val):
    """Convert value to safe string without special characters"""
    if pd.isna(val) or val is None:
        return ""
    s = str(val)
    s = s.replace('₹', 'Rs.')
    s = s.replace('–', '-')
    s = s.replace('—', '-')
    s = s.replace('"', '"').replace('"', '"')
    s = s.replace(''', "'").replace(''', "'")
    return s


def fetch_pdf_config(job_id):
    """Fetch PDF configuration from database"""
    config = {
        'channel_name': 'Channel',
        'channel_logo_path': None,
        'channel_url': '',
        'company_name': '',
        'registration_details': '',
        'disclaimer_text': '',
        'disclosure_text': '',
        'company_data': '',
        'company_logo_path': None,
        'font_regular_path': None,
        'font_bold_path': None
    }
    
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT j.channel_id, c.channel_name, c.channel_logo_path, c.channel_url
                FROM jobs j
                LEFT JOIN channels c ON j.channel_id = c.id
                WHERE j.id = %s
            """, (job_id,))
            job = cursor.fetchone()
            
            if job:
                config['channel_name'] = job.get('channel_name') or 'Channel'
                config['channel_logo_path'] = job.get('channel_logo_path')
                config['channel_url'] = job.get('channel_url') or ''
            
            cursor.execute("SELECT * FROM pdf_template LIMIT 1")
            template = cursor.fetchone()
            if template:
                config['company_name'] = template.get('company_name') or ''
                config['registration_details'] = template.get('registration_details') or ''
                config['disclaimer_text'] = template.get('disclaimer_text') or ''
                config['disclosure_text'] = template.get('disclosure_text') or ''
                config['company_data'] = template.get('company_data') or ''
            
            cursor.execute("""
                SELECT file_type, file_path FROM uploaded_files 
                WHERE file_type IN ('companyLogo', 'fontRegular', 'fontBold')
            """)
            files = cursor.fetchall()
            for f in files:
                path = resolve_uploaded_file_path(f['file_path'])
                if f['file_type'] == 'companyLogo':
                    config['company_logo_path'] = path
                elif f['file_type'] == 'fontRegular':
                    config['font_regular_path'] = path
                elif f['file_type'] == 'fontBold':
                    config['font_bold_path'] = path
    except Exception as e:
        print(f"⚠️ Error fetching config: {e}")
    
    return config


def create_round_logo(logo_path, size=40):
    """Create circular logo from image"""
    try:
        if not logo_path or not os.path.exists(logo_path):
            return None
        
        img = PILImage.open(logo_path).convert('RGBA')
        img = img.resize((size, size), PILImage.Resampling.LANCZOS)
        
        mask = PILImage.new('L', (size, size), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        output = PILImage.new('RGBA', (size, size), (255, 255, 255, 0))
        output.paste(img, (0, 0), mask)
        
        temp_path = f"/tmp/round_logo_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        output.save(temp_path, 'PNG')
        
        return temp_path
    except Exception as e:
        print(f"⚠️ Error creating round logo: {e}")
        return None


def run(job_folder, template_config=None):
    """
    Generate PDF report from stocks_with_charts.csv
    
    Args:
        job_folder: Path to job directory
        template_config: Optional PDF template configuration
    
    Returns:
        dict: {
            'success': bool,
            'output_file': str,
            'error': str or None
        }
    """
    print("\n" + "=" * 60)
    print("BULK STEP 6: GENERATE PDF REPORT")
    print(f"{'='*60}\n")
    
    try:
        job_id = os.path.basename(job_folder)
        
        analysis_folder = os.path.join(job_folder, 'analysis')
        pdf_folder = os.path.join(job_folder, 'pdf')
        os.makedirs(pdf_folder, exist_ok=True)
        
        stocks_csv = os.path.join(analysis_folder, 'stocks_with_charts.csv')
        if not os.path.exists(stocks_csv):
            return {
                'success': False,
                'error': f'Stocks CSV not found: {stocks_csv}'
            }
        
        print("📖 Loading stocks data...")
        df = pd.read_csv(stocks_csv, encoding='utf-8')
        print(f"✅ Loaded {len(df)} stocks\n")
        
        print("🔑 Fetching PDF configuration...")
        config = fetch_pdf_config(job_id)
        print(f"✅ Channel: {config['channel_name']}")
        
        pdf_filename = "bulk_rationale.pdf"
        output_pdf = os.path.join(pdf_folder, pdf_filename)
        print(f"📄 Output: {output_pdf}\n")
        
        BASE_REG = "Helvetica"
        BASE_BLD = "Helvetica-Bold"
        
        if config['font_regular_path'] and os.path.exists(config['font_regular_path']):
            try:
                pdfmetrics.registerFont(TTFont("NotoSans", config['font_regular_path']))
                BASE_REG = "NotoSans"
                print(f"✅ Loaded custom font (regular)")
            except:
                pass
        
        if config['font_bold_path'] and os.path.exists(config['font_bold_path']):
            try:
                pdfmetrics.registerFont(TTFont("NotoSans-Bold", config['font_bold_path']))
                BASE_BLD = "NotoSans-Bold"
                print(f"✅ Loaded custom font (bold)")
            except:
                pass
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=BASE_BLD,
            fontSize=18,
            textColor=PRIMARY_BLUE,
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=BASE_BLD,
            fontSize=14,
            textColor=PRIMARY_BLUE,
            spaceBefore=12,
            spaceAfter=6
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName=BASE_REG,
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY
        )
        
        small_style = ParagraphStyle(
            'SmallText',
            parent=styles['Normal'],
            fontName=BASE_REG,
            fontSize=8,
            textColor=colors.gray
        )
        
        doc = SimpleDocTemplate(
            output_pdf,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        story.append(Paragraph(f"{config['channel_name']} - Bulk Analysis Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        if config['company_name']:
            story.append(Paragraph(safe_str(config['company_name']), heading_style))
        
        if config['registration_details']:
            reg_text = re.sub('<[^<]+?>', '', config['registration_details'])
            story.append(Paragraph(safe_str(reg_text), small_style))
        
        story.append(Spacer(1, 0.3*inch))
        
        date_str = df['DATE'].iloc[0] if 'DATE' in df.columns else datetime.now().strftime('%Y-%m-%d')
        time_str = df['TIME'].iloc[0] if 'TIME' in df.columns else ''
        story.append(Paragraph(f"Report Date: {date_str} {time_str}", body_style))
        story.append(Paragraph(f"Total Stocks: {len(df)}", body_style))
        story.append(Spacer(1, 0.3*inch))
        
        for idx, row in df.iterrows():
            stock_elements = []
            
            stock_name = safe_str(row.get('LISTED NAME', row.get('STOCK NAME', '')))
            symbol = safe_str(row.get('STOCK SYMBOL', ''))
            
            stock_elements.append(Paragraph(f"{stock_name} ({symbol})", heading_style))
            stock_elements.append(Spacer(1, 0.1*inch))
            
            chart_path = row.get('CHART PATH', '')
            if chart_path and pd.notna(chart_path) and isinstance(chart_path, str) and chart_path.strip():
                full_chart_path = os.path.join(job_folder, str(chart_path).strip())
                if os.path.exists(full_chart_path):
                    try:
                        img = Image(full_chart_path, width=6.5*inch, height=4*inch)
                        stock_elements.append(img)
                        stock_elements.append(Spacer(1, 0.2*inch))
                    except Exception as e:
                        print(f"⚠️ Error loading chart for {stock_name}: {e}")
            
            table_data = [
                ['Exchange', 'Symbol', 'Security ID', 'CMP'],
                [
                    safe_str(row.get('EXCHANGE', 'NSE')),
                    symbol,
                    safe_str(row.get('SECURITY ID', '')),
                    f"Rs. {row.get('CMP', 'N/A')}" if pd.notna(row.get('CMP')) else 'N/A'
                ]
            ]
            
            table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), BASE_BLD),
                ('FONTNAME', (0, 1), (-1, -1), BASE_REG),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                ('BACKGROUND', (0, 1), (-1, -1), LIGHT_BLUE),
            ]))
            stock_elements.append(table)
            stock_elements.append(Spacer(1, 0.2*inch))
            
            analysis = safe_str(row.get('ANALYSIS', ''))
            if analysis:
                stock_elements.append(Paragraph("Rationale - Our View", heading_style))
                stock_elements.append(Paragraph(analysis, body_style))
            
            story.append(KeepTogether(stock_elements))
            
            if idx < len(df) - 1:
                story.append(PageBreak())
        
        if config['disclaimer_text']:
            story.append(PageBreak())
            story.append(Paragraph("Disclaimer", title_style))
            story.append(Spacer(1, 0.2*inch))
            disclaimer = re.sub('<[^<]+?>', '', config['disclaimer_text'])
            story.append(Paragraph(safe_str(disclaimer), body_style))
        
        if config['disclosure_text']:
            story.append(PageBreak())
            story.append(Paragraph("Disclosure", title_style))
            story.append(Spacer(1, 0.2*inch))
            disclosure = re.sub('<[^<]+?>', '', config['disclosure_text'])
            story.append(Paragraph(safe_str(disclosure), body_style))
        
        print("📝 Building PDF document...")
        doc.build(story)
        
        print(f"\n✅ PDF generated successfully!")
        print(f"💾 Output: {output_pdf}")
        
        return {
            'success': True,
            'output_file': output_pdf
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_folder = sys.argv[1]
    else:
        test_folder = "backend/job_files/test_bulk_job"
    
    result = run(test_folder)
    print(f"\n{'='*60}")
    print(f"Result: {'SUCCESS' if result.get('success') else 'FAILED'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print(f"{'='*60}")
