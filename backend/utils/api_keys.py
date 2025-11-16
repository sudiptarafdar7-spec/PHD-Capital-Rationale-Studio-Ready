"""
Utility functions for fetching API keys from the database
"""
from backend.utils.database import get_db_cursor


def get_rapidapi_key():
    """
    Fetch RapidAPI key from database.
    
    Supports both 'rapidapi' (preferred) and 'rapidapi_video_transcript' (legacy) provider names.
    The same RapidAPI account key works across all subscribed APIs (youtube-mp36, video-transcript-scraper, etc.)
    
    Returns:
        str: API key value
        
    Raises:
        ValueError: If no RapidAPI key is configured in database
    """
    try:
        with get_db_cursor() as cursor:
            # Try preferred provider name first
            cursor.execute("SELECT key_value FROM api_keys WHERE provider = %s", ('rapidapi',))
            result = cursor.fetchone()
            
            # Fall back to legacy provider name for backward compatibility
            if not result:
                cursor.execute("SELECT key_value FROM api_keys WHERE provider = %s", ('rapidapi_video_transcript',))
                result = cursor.fetchone()
            
            if result and result['key_value']:
                return result['key_value']
            else:
                raise ValueError(
                    'RapidAPI key not configured. Please add it in Settings → API Keys. '
                    'The same key is used for audio downloads and caption scraping.'
                )
    except Exception as db_error:
        raise ValueError(f'Database error fetching RapidAPI key: {db_error}')
