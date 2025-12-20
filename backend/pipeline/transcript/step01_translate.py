"""
Transcript Rationale Step 1: Translate Input Text
Translates transcript-input.txt to English using OpenAI
Includes chunking for large transcripts to avoid token limits
"""

import os
import time
import openai
from backend.utils.database import get_db_cursor


MAX_CHARS_PER_CHUNK = 15000


def get_openai_key():
    """Get OpenAI API key from database"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT key_value FROM api_keys WHERE provider = 'openai'")
        result = cursor.fetchone()
        if result and result['key_value']:
            return result['key_value'].strip()
    return None


def split_text_into_chunks(text, max_chars=MAX_CHARS_PER_CHUNK):
    """Split text into chunks at paragraph boundaries"""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            if current_chunk:
                current_chunk += '\n\n' + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > max_chars:
                lines = para.split('\n')
                current_chunk = ""
                for line in lines:
                    if len(current_chunk) + len(line) + 1 <= max_chars:
                        if current_chunk:
                            current_chunk += '\n' + line
                        else:
                            current_chunk = line
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = line
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def translate_chunk(client, chunk_text, chunk_num, total_chunks):
    """Translate a single chunk using OpenAI"""
    print(f"  Translating chunk {chunk_num}/{total_chunks} ({len(chunk_text)} chars)...")
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are a professional translator specializing in financial content. 
Translate the following text to English while:
1. Preserving all stock names, symbols, numbers, and financial terms accurately
2. Maintaining the original structure and formatting (preserve all sections and stock entries)
3. Keeping any dates, times, and price targets exactly as they appear
4. If the text is already in English, return it as-is with minor cleanup
5. Do not add any explanations or commentary - just translate
6. IMPORTANT: Translate ALL content completely - do not skip or truncate any sections
7. Preserve speaker names like "Pradip" or "Mr. Pradip" exactly
8. If a stock name appears to be gibberish or random characters, keep it as-is"""
            },
            {
                "role": "user",
                "content": chunk_text
            }
        ],
        temperature=0.1,
        max_tokens=16384
    )
    
    return response.choices[0].message.content.strip()


def run(job_folder):
    """
    Translate transcript-input.txt to English using OpenAI
    
    Args:
        job_folder: Path to job directory
        
    Returns:
        dict: {
            'success': bool,
            'output_file': str,
            'error': str or None
        }
    """
    print("\n" + "=" * 60)
    print("TRANSCRIPT STEP 1: TRANSLATE INPUT TEXT")
    print(f"{'='*60}\n")
    
    try:
        input_file = os.path.join(job_folder, 'transcript-input.txt')
        output_file = os.path.join(job_folder, 'transcript-input-english.txt')
        
        if not os.path.exists(input_file):
            return {
                'success': False,
                'error': f'Input file not found: {input_file}'
            }
        
        openai_key = get_openai_key()
        if not openai_key:
            return {
                'success': False,
                'error': 'OpenAI API key not found. Please add it in Settings → API Keys.'
            }
        
        print(f"Reading input file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        print(f"Input text length: {len(input_text)} characters")
        
        if not input_text.strip():
            return {
                'success': False,
                'error': 'Input text is empty'
            }
        
        print("Translating to English using OpenAI...")
        
        client = openai.OpenAI(api_key=openai_key)
        
        chunks = split_text_into_chunks(input_text)
        print(f"Split input into {len(chunks)} chunk(s)")
        
        translated_chunks = []
        for i, chunk in enumerate(chunks, 1):
            translated = translate_chunk(client, chunk, i, len(chunks))
            translated_chunks.append(translated)
            if i < len(chunks):
                time.sleep(1)
        
        translated_text = '\n\n'.join(translated_chunks)
        
        print(f"Translation complete: {len(translated_text)} characters")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(translated_text)
        
        print(f"Saved translated text to: {output_file}")
        
        return {
            'success': True,
            'output_file': output_file
        }
        
    except Exception as e:
        print(f"Error in Step 1: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
