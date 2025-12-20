"""
Transcript Rationale Step 2: Detect Stocks
Detects all stock names discussed by Mr. Pradip ONLY (ignores other speakers)
Splits transcript into 3 parts for accurate detection
Output: detected_stocks.csv with INPUT STOCK column
"""

import os
import openai
import pandas as pd
from backend.utils.database import get_db_cursor


def get_openai_key():
    """Get OpenAI API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'openai'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def split_transcript(text, num_parts=3, overlap_lines=10):
    """
    Split transcript into multiple parts with overlap for context
    
    Args:
        text: Full transcript text
        num_parts: Number of parts to split into
        overlap_lines: Number of lines to overlap between parts
        
    Returns:
        List of text chunks
    """
    lines = text.split('\n')
    total_lines = len(lines)
    
    if total_lines < 30:
        return [text]
    
    base_chunk_size = total_lines // num_parts
    chunks = []
    
    for i in range(num_parts):
        start_idx = max(0, i * base_chunk_size - overlap_lines)
        
        if i == num_parts - 1:
            end_idx = total_lines
        else:
            end_idx = (i + 1) * base_chunk_size + overlap_lines
        
        chunk_lines = lines[start_idx:end_idx]
        chunks.append('\n'.join(chunk_lines))
    
    return chunks


def detect_pradip_stocks(client, transcript_chunk, chunk_num, total_chunks):
    """
    Use OpenAI to detect stocks discussed by Mr. Pradip in a transcript chunk
    
    Args:
        client: OpenAI client
        transcript_chunk: Text chunk to analyze
        chunk_num: Current chunk number
        total_chunks: Total number of chunks
        
    Returns:
        List of stock names
    """
    prompt = f"""You are analyzing Part {chunk_num} of {total_chunks} of a YouTube video transcript.
This transcript is from a financial show where an anchor interviews stock analysts.
We are ONLY interested in stocks discussed/analyzed by MR. PRADIP (Pradip Hotchandani or simply "Pradip").

CRITICAL RULES:
1. ONLY extract stock names that MR. PRADIP discusses or gives his analysis on
2. COMPLETELY IGNORE stocks mentioned by the anchor or other analysts
3. When the anchor asks "What do you think about [STOCK]?" to Pradip - that stock counts
4. Go line by line, word by word to detect accurately
5. Include Indian stocks, indices, and financial instruments Pradip discusses

The anchor typically asks Pradip about specific stocks, and Pradip gives his views.
Pattern to look for:
- Anchor: "What about [STOCK]?" → Pradip responds → Include this stock
- Pradip: "I like [STOCK]..." → Include this stock
- Pradip: "[STOCK] looks good..." → Include this stock

OUTPUT FORMAT:
Return ONLY a comma-separated list of stock names.
Example: RELIANCE, TATA MOTORS, HDFC BANK, INFOSYS

If no stocks are discussed by Pradip in this chunk, return: NONE

TRANSCRIPT CHUNK:
{transcript_chunk}

STOCKS DISCUSSED BY PRADIP:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing financial video transcripts and identifying which stocks are discussed by specific speakers. Be thorough and accurate."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        
        if result.upper() == 'NONE' or not result:
            return []
        
        stocks = [s.strip().upper() for s in result.split(',')]
        stocks = [s for s in stocks if s and s != 'NONE' and len(s) > 1]
        
        return stocks
        
    except Exception as e:
        print(f"Error detecting stocks in chunk {chunk_num}: {str(e)}")
        return []


def run(job_folder):
    """
    Detect all stocks discussed by Mr. Pradip in the transcript
    
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
    print("TRANSCRIPT STEP 2: DETECT PRADIP'S STOCKS")
    print(f"{'='*60}\n")
    
    try:
        input_file = os.path.join(job_folder, 'transcript-input-english.txt')
        analysis_folder = os.path.join(job_folder, 'analysis')
        os.makedirs(analysis_folder, exist_ok=True)
        output_file = os.path.join(analysis_folder, 'detected_stocks.csv')
        
        if not os.path.exists(input_file):
            return {
                'success': False,
                'error': f'Translated input file not found: {input_file}'
            }
        
        openai_key = get_openai_key()
        if not openai_key:
            return {
                'success': False,
                'error': 'OpenAI API key not found. Please add it in Settings → API Keys.'
            }
        
        print(f"Reading translated transcript: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        print(f"Transcript length: {len(transcript_text)} characters")
        
        print("Splitting transcript into 3 parts for accurate detection...")
        chunks = split_transcript(transcript_text, num_parts=3)
        print(f"Created {len(chunks)} chunks")
        
        client = openai.OpenAI(api_key=openai_key)
        
        all_stocks = []
        for i, chunk in enumerate(chunks, 1):
            print(f"\nProcessing chunk {i}/{len(chunks)}...")
            stocks = detect_pradip_stocks(client, chunk, i, len(chunks))
            print(f"  Found {len(stocks)} stocks: {stocks[:5]}{'...' if len(stocks) > 5 else ''}")
            all_stocks.extend(stocks)
        
        unique_stocks = []
        seen = set()
        for stock in all_stocks:
            stock_normalized = stock.upper().strip()
            if stock_normalized and stock_normalized not in seen:
                seen.add(stock_normalized)
                unique_stocks.append(stock_normalized)
        
        print(f"\nTotal unique stocks found: {len(unique_stocks)}")
        print(f"Stocks: {unique_stocks}")
        
        df = pd.DataFrame({'INPUT STOCK': unique_stocks})
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"Saved detected stocks to: {output_file}")
        
        return {
            'success': True,
            'output_file': output_file,
            'stock_count': len(unique_stocks)
        }
        
    except Exception as e:
        print(f"Error in Step 2: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
