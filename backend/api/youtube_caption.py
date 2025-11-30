"""
YouTube Caption API - Standalone caption fetching endpoints
"""
from flask import request, jsonify, send_file
from flask_jwt_extended import jwt_required
from backend.api import Blueprint
from backend.services.youtube_caption_service import caption_service

youtube_caption_bp = Blueprint('youtube_caption', __name__, url_prefix='/api/v1/youtube-caption')


@youtube_caption_bp.route('/languages', methods=['POST'])
@jwt_required()
def get_available_languages():
    """
    Get available caption languages for a YouTube video
    
    Request body:
        {
            "youtube_url": "https://www.youtube.com/watch?v=..."
        }
    
    Response:
        {
            "success": true,
            "languages": [{"code": "en", "name": "English"}, ...],
            "video_id": "abc123",
            "error": null
        }
    """
    try:
        data = request.get_json()
        youtube_url = data.get('youtube_url', '').strip()
        
        if not youtube_url:
            return jsonify({
                'success': False,
                'languages': [],
                'error': 'YouTube URL is required'
            }), 400
        
        result = caption_service.get_available_languages(youtube_url)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'languages': [],
            'error': str(e)
        }), 500


@youtube_caption_bp.route('/fetch', methods=['POST'])
@jwt_required()
def fetch_captions():
    """
    Fetch captions for a YouTube video
    
    Request body:
        {
            "youtube_url": "https://www.youtube.com/watch?v=...",
            "language": "en"  // optional
        }
    
    Response:
        {
            "success": true,
            "caption_id": "abc123_xyz",
            "captions": [{"timestamp": "00:00:05", "text": "Hello world"}, ...],
            "raw_text": "[00:00:05] Hello world\n...",
            "language": "en",
            "download_url": "/api/v1/youtube-caption/download/abc123_xyz",
            "error": null
        }
    """
    try:
        data = request.get_json()
        youtube_url = data.get('youtube_url', '').strip()
        language = data.get('language', None)
        
        if not youtube_url:
            return jsonify({
                'success': False,
                'error': 'YouTube URL is required'
            }), 400
        
        result = caption_service.fetch_captions(youtube_url, language)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@youtube_caption_bp.route('/download/<caption_id>', methods=['GET'])
@jwt_required()
def download_caption(caption_id):
    """
    Download caption file as .txt
    Deletes the file after download
    """
    try:
        file_path = caption_service.get_caption_file(caption_id)
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'Caption file not found or already downloaded'
            }), 404
        
        response = send_file(
            file_path,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'youtube_caption_{caption_id}.txt'
        )
        
        @response.call_on_close
        def cleanup():
            caption_service.delete_caption_file(caption_id)
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@youtube_caption_bp.route('/clear/<caption_id>', methods=['DELETE'])
@jwt_required()
def clear_caption(caption_id):
    """
    Clear/delete caption file without downloading
    """
    try:
        deleted = caption_service.delete_caption_file(caption_id)
        
        return jsonify({
            'success': True,
            'deleted': deleted
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
