"""
Transcript Rationale Step 3: Web Search for Stock Symbols
Uses OpenAI to web search for exact NSE stock symbols for each detected stock
Output: final-stocks.csv with INPUT STOCK, GPT SYMBOL columns
"""

import os
import openai
import pandas as pd
import time
from backend.utils.database import get_db_cursor


def get_openai_key():
    """Get OpenAI API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT key_value FROM api_keys WHERE provider = 'openai'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def search_nse_symbol(client, stock_name):
    """
    Use OpenAI to search for the exact NSE stock symbol
    
    Args:
        client: OpenAI client
        stock_name: Name of the stock to search for
        
    Returns:
        str: NSE symbol (without .NS or .BO suffix)
    """
    prompt = f"""Search for the exact NSE (National Stock Exchange of India) trading symbol for: {stock_name}

RULES:
1. Find the EXACT NSE/BSE trading symbol
2. Return ONLY the symbol without any suffix like .NS, .NSE, .BO, .BSE
3. If it's an ETF or index fund, return the exact trading symbol
4. If the company is listed on both NSE and BSE, prefer NSE symbol
5. Return ONLY the symbol, nothing else

Examples:
- "Reliance Industries" → RELIANCE
- "HDFC Bank" → HDFCBANK  
- "Tata Consultancy Services" → TCS
- "Tata Motors" → TATAMOTORS
- "State Bank of India" → SBIN
- "Bharti Airtel" → BHARTIARTL
- "Infosys" → INFY
- "Wipro" → WIPRO

NSE SYMBOL for "{stock_name}":"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role":
                "system",
                "content":
                "You are an expert on Indian stock markets. You have extensive knowledge of NSE stock symbols. Always return the exact trading symbol without any suffixes."
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0.0,
            max_tokens=50)

        result = response.choices[0].message.content.strip()

        result = result.replace('.NS', '').replace('.NSE', '').replace(
            '.BO', '').replace('.BSE', '')
        result = result.replace('"', '').replace("'", '').strip().upper()

        if result and len(result) <= 20:
            return result
        else:
            return stock_name.upper().replace(' ', '')

    except Exception as e:
        print(f"Error searching symbol for {stock_name}: {str(e)}")
        return stock_name.upper().replace(' ', '')


def run(job_folder):
    """
    Search for NSE symbols for all detected stocks
    
    Args:
        job_folder: Path to job directory
        
    Returns:
        dict: {
            'success': bool,
            'output_file': str,
            'stock_count': int,
            'error': str or None
        }
    """
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 3: WEB SEARCH FOR STOCK SYMBOLS")
    print(f"{'='*60}\n")

    try:
        input_file = os.path.join(job_folder, 'analysis',
                                  'detected_stocks.csv')
        output_file = os.path.join(job_folder, 'analysis', 'final-stocks.csv')

        if not os.path.exists(input_file):
            return {
                'success': False,
                'error': f'Detected stocks file not found: {input_file}'
            }

        openai_key = get_openai_key()
        if not openai_key:
            return {
                'success':
                False,
                'error':
                'OpenAI API key not found. Please add it in Settings → API Keys.'
            }

        print(f"Reading detected stocks: {input_file}")
        df = pd.read_csv(input_file, encoding='utf-8-sig')

        if 'INPUT STOCK' not in df.columns:
            return {
                'success': False,
                'error': 'INPUT STOCK column not found in detected stocks file'
            }

        stocks = df['INPUT STOCK'].dropna().tolist()
        print(f"Found {len(stocks)} stocks to process")

        client = openai.OpenAI(api_key=openai_key)

        results = []
        for i, stock in enumerate(stocks, 1):
            print(f"  [{i}/{len(stocks)}] Searching symbol for: {stock}")
            symbol = search_nse_symbol(client, stock)
            print(f"    → {symbol}")
            results.append({'INPUT STOCK': stock, 'GPT SYMBOL': symbol})

            if i < len(stocks):
                time.sleep(0.5)

        df_output = pd.DataFrame(results)
        df_output.to_csv(output_file, index=False, encoding='utf-8-sig')

        print(f"\nSaved {len(results)} stocks with symbols to: {output_file}")

        return {
            'success': True,
            'output_file': output_file,
            'stock_count': len(results)
        }

    except Exception as e:
        print(f"Error in Step 3: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
