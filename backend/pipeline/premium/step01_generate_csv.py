"""
Premium Step 1: Generate Premium Rationale CSV from Input Text
Uses OpenAI GPT to parse stock calls and create structured CSV
"""
import os
import csv
from openai import OpenAI


def run(job_folder, input_text, openai_api_key):
    """
    Parse input text and generate premium_rationale_stocks.csv
    
    Args:
        job_folder: Path to job folder
        input_text: Raw text with stock calls
        openai_api_key: OpenAI API key
    
    Returns:
        dict: {
            'success': bool,
            'output_file': str,
            'stocks_count': int,
            'error': str or None
        }
    """
    try:
        print("=" * 60)
        print("PREMIUM STEP 1: GENERATE CSV FROM INPUT TEXT")
        print("=" * 60)
        
        analysis_folder = os.path.join(job_folder, 'analysis')
        os.makedirs(analysis_folder, exist_ok=True)
        
        output_csv = os.path.join(analysis_folder, 'premium_rationale_stocks.csv')
        
        # TODO: Implement OpenAI parsing logic
        print("🤖 Calling OpenAI GPT to parse stock calls...")
        print(f"   Input length: {len(input_text)} characters")
        
        if not openai_api_key:
            raise ValueError("OpenAI API key not found in database")
        
        client = OpenAI(api_key=openai_api_key)
        
        prompt = f"""You are a financial data extraction expert. Parse the following stock market calls and extract structured data into a CSV format.

**Required CSV Columns (MUST be exact):**
DATE,TIME,STOCK NAME,TARGETS,STOP LOSS,HOLDING PERIOD,CALL,CHART TYPE

**Instructions:**
1. Extract each stock call as a separate row
2. DATE: Format as YYYY-MM-DD (e.g., 2025-11-11)
3. TIME: Format as HH:MM:SS (e.g., 14:30:00)
4. STOCK NAME: Full stock name or symbol
5. TARGETS: Target prices (comma-separated if multiple, e.g., "150, 160, 170")
6. STOP LOSS: Stop loss price or percentage (e.g., "140" or "5%")
7. HOLDING PERIOD: Duration to hold (e.g., "1 Week", "Short Term", "Intraday")
8. CALL: Type of call (e.g., "BUY", "SELL", "HOLD", "ACCUMULATE")
9. CHART TYPE: Chart timeframe - STRICTLY one of: "Daily", "Weekly", "Monthly"
   - Use "Daily" for Intraday, Short Term, or Swing trades
   - Use "Weekly" for Medium Term trades
   - Use "Monthly" for Long Term or Positional trades
   - Default to "Daily" if unclear

**Important:**
- Return ONLY the CSV data with header row
- NO markdown formatting (no ```csv or ``` tags)
- Use proper CSV escaping for commas in values
- If a field is missing, leave it empty but include the comma
- Ensure all rows have exactly 8 columns
- CHART TYPE must be EXACTLY one of: Daily, Weekly, Monthly (case-sensitive)

**Input Text:**
{input_text}

**Output (CSV format only):**"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a precise financial data extraction system. Return only valid CSV data without any additional text or formatting."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.1
        )
        
        csv_content = response.choices[0].message.content.strip()
        
        # Remove markdown formatting if present
        if csv_content.startswith("```"):
            lines = csv_content.split('\n')
            csv_content = '\n'.join([line for line in lines if not line.startswith('```')])
            csv_content = csv_content.strip()
        
        # Additional cleanup: remove "csv" tag if present
        if csv_content.lower().startswith("csv"):
            csv_content = '\n'.join(csv_content.split('\n')[1:]).strip()
        
        # Validate CSV format
        lines = csv_content.split('\n')
        if len(lines) < 2:
            raise ValueError("Generated CSV has no data rows")
        
        # Check header
        expected_header = "DATE,TIME,STOCK NAME,TARGETS,STOP LOSS,HOLDING PERIOD,CALL,CHART TYPE"
        actual_header = lines[0].strip()
        
        if actual_header != expected_header:
            print(f"⚠️  Warning: Header mismatch")
            print(f"   Expected: {expected_header}")
            print(f"   Got:      {actual_header}")
            # Try to fix common issues
            if "STOCK NAME" not in actual_header and "STOCK" in actual_header:
                csv_content = csv_content.replace("STOCK,", "STOCK NAME,", 1)
        
        # Parse and re-write CSV with proper quoting to handle commas in values
        import io
        csv_buffer = io.StringIO(csv_content)
        reader = csv.DictReader(csv_buffer)
        rows = list(reader)
        stocks_count = len(rows)
        
        # Get valid fieldnames (filter out None)
        valid_fieldnames = [fn for fn in reader.fieldnames if fn is not None]
        
        # Clean rows: remove None keys and ensure all expected fields exist
        cleaned_rows = []
        valid_chart_types = {"Daily", "Weekly", "Monthly"}
        
        for row in rows:
            # Remove None keys from row
            cleaned_row = {k: v for k, v in row.items() if k is not None}
            
            # Ensure all expected fields exist
            for field in valid_fieldnames:
                if field not in cleaned_row:
                    cleaned_row[field] = ''
            
            # Sanitize CHART TYPE
            chart_type = str(cleaned_row.get('CHART TYPE', '')).strip()
            if chart_type not in valid_chart_types:
                cleaned_row['CHART TYPE'] = 'Daily'
                print(f"   ⚠️  Invalid CHART TYPE '{chart_type}' → defaulting to 'Daily'")
            
            cleaned_rows.append(cleaned_row)
        
        # Save CSV with proper quoting
        with open(output_csv, 'w', encoding='utf-8', newline='') as f:
            if cleaned_rows:
                writer = csv.DictWriter(f, fieldnames=valid_fieldnames, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                writer.writerows(cleaned_rows)
        
        # Re-read to validate
        with open(output_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            stocks_count = len(rows)
            
            # Validate required columns
            required_columns = ['DATE', 'TIME', 'STOCK NAME', 'TARGETS', 'STOP LOSS', 'HOLDING PERIOD', 'CALL', 'CHART TYPE']
            if reader.fieldnames:
                missing_cols = [col for col in required_columns if col not in reader.fieldnames]
                if missing_cols:
                    raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
        
        print(f"✅ Generated CSV with {stocks_count} stock call(s)")
        print(f"   Output: {output_csv}")
        print(f"   Columns: {', '.join(reader.fieldnames) if reader.fieldnames else 'Unknown'}")
        
        return {
            'success': True,
            'output_file': output_csv,
            'stocks_count': stocks_count,
            'error': None
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
