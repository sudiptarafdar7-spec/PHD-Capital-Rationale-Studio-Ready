from flask import request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.utils.database import get_db_cursor
from backend.utils.path_utils import resolve_job_folder_path
from backend.api import upload_rationale_bp
from backend.models.user import User
from backend.pipeline.upload_pipeline_manager import create_job_directory, UPLOAD_PIPELINE_STEPS, run_pipeline_step
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import secrets
import threading
import csv
import io
import shutil
import subprocess

ALLOWED_AUDIO_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aac'}
ALLOWED_CAPTION_EXTENSIONS = {'.txt', '.json'}

def is_admin(user_id):
    user = User.find_by_id(user_id)
    return user and user.get('role') == 'admin'

def check_job_access(job_id, current_user_id):
    """Verify user owns this job or is admin"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT user_id FROM jobs WHERE id = %s", (job_id,))
        job = cursor.fetchone()
        
        if not job:
            return False, "Job not found"
        
        if job['user_id'] != current_user_id and not is_admin(current_user_id):
            return False, "Access denied"
        
        return True, None

def _job_path(job_id, *parts):
    """
    Helper to build absolute path to job file.
    Composes relative path and resolves to absolute path.
    """
    relative_path = os.path.join('backend', 'job_files', job_id, *parts)
    return resolve_job_folder_path(relative_path)

def convert_audio_to_16k_mono(input_path, output_path):
    """Convert audio file to 16kHz mono WAV using ffmpeg"""
    try:
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-ar', '16000',      # 16kHz sample rate
            '-ac', '1',          # Mono (1 channel)
            '-y',                # Overwrite output
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"Error converting audio: {str(e)}")
        return False

@upload_rationale_bp.route('/start-analysis', methods=['POST'])
@jwt_required()
def start_analysis():
    try:
        current_user_id = get_jwt_identity()
        
        # Get form data
        tool_used = request.form.get('toolUsed', 'Upload Rationale')
        title = request.form.get('title', '')
        channel_name = request.form.get('channelName', '')
        date = request.form.get('uploadDate', '')
        time = request.form.get('uploadTime', '00:00:00')
        
        # Get uploaded files
        audio_file = request.files.get('audioFile')
        caption_file = request.files.get('captionFile')
        
        # Validation
        if not audio_file or not caption_file:
            return jsonify({'error': 'Both audio file and caption file are required'}), 400
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        # Validate file extensions
        audio_ext = os.path.splitext(audio_file.filename)[1].lower()
        caption_ext = os.path.splitext(caption_file.filename)[1].lower()
        
        if audio_ext not in ALLOWED_AUDIO_EXTENSIONS:
            return jsonify({'error': f'Invalid audio file type. Allowed: {", ".join(ALLOWED_AUDIO_EXTENSIONS)}'}), 400
        
        if caption_ext not in ALLOWED_CAPTION_EXTENSIONS:
            return jsonify({'error': f'Invalid caption file type. Allowed: {", ".join(ALLOWED_CAPTION_EXTENSIONS)}'}), 400
        
        # Generate unique job ID
        job_id = f"job-{secrets.token_hex(4)}"
        
        # Get channel_id from database (if exists)
        channel_id = None
        if channel_name:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM channels 
                    WHERE LOWER(channel_name) = LOWER(%s)
                """, (channel_name,))
                
                channel = cursor.fetchone()
                if channel:
                    channel_id = channel['id']
        
        # Create job directory structure
        create_job_directory(job_id)
        
        # Save uploaded files
        audio_folder = os.path.join('backend', 'job_files', job_id, 'audio')
        captions_folder = os.path.join('backend', 'job_files', job_id, 'captions')
        os.makedirs(audio_folder, exist_ok=True)
        os.makedirs(captions_folder, exist_ok=True)
        
        # Save raw audio file temporarily
        raw_audio_path = os.path.join(audio_folder, f"uploaded_audio{audio_ext}")
        audio_file.save(raw_audio_path)
        
        # Convert audio to 16kHz mono WAV (required for AssemblyAI)
        prepared_audio_path = os.path.join(audio_folder, "audio_16k_mono.wav")
        if not convert_audio_to_16k_mono(raw_audio_path, prepared_audio_path):
            return jsonify({'error': 'Failed to convert audio file to required format'}), 500
        
        # Save caption file as captions.json
        caption_path = os.path.join(captions_folder, 'captions.json')
        
        # If caption is .txt, convert to simple JSON format
        if caption_ext == '.txt':
            caption_text = caption_file.read().decode('utf-8')
            import json
            captions_data = {
                "text": caption_text,
                "source": "user_upload"
            }
            with open(caption_path, 'w', encoding='utf-8') as f:
                json.dump(captions_data, f, ensure_ascii=False, indent=2)
        else:
            # Save JSON directly
            caption_file.save(caption_path)
        
        # Create job record in database
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                INSERT INTO jobs (
                    id, user_id, channel_id, tool_used, title,
                    date, time, status, 
                    current_step, progress, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                job_id, current_user_id, channel_id, tool_used, title,
                date, time, 'pending', 
                0, 0, datetime.now(), datetime.now()
            ))
            
            # Initialize all 12 upload pipeline steps (steps 3-14 renumbered as 1-12)
            for step in UPLOAD_PIPELINE_STEPS:
                cursor.execute("""
                    INSERT INTO job_steps (
                        job_id, step_number, step_name, 
                        status, message, output_files
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    job_id, step['number'], step['name'],
                    'pending', None, []
                ))
        
        # Start pipeline execution in background thread
        def run_pipeline_background():
            try:
                # Update job status to processing
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("""
                        UPDATE jobs 
                        SET status = 'processing', updated_at = %s
                        WHERE id = %s
                    """, (datetime.now(), job_id))
                
                # Run pipeline steps 1-10 (pause after Step 10 for CSV review)
                # Note: Step 1 in upload pipeline = Step 3 in media pipeline
                all_success = True
                for step_num in range(1, 11):  # Run steps 1 to 10 (transcribe to analysis)
                    success = run_pipeline_step(job_id, step_num)
                    if not success:
                        all_success = False
                        break
                
                # After Step 10 completes successfully, pause and set status to 'awaiting_csv_review'
                if all_success:
                    with get_db_cursor(commit=True) as cursor:
                        cursor.execute("""
                            UPDATE jobs 
                            SET status = 'awaiting_csv_review', progress = 80, updated_at = %s
                            WHERE id = %s
                        """, (datetime.now(), job_id))
                    print(f"Job {job_id}: Paused after Step 10 for CSV review")
                
            except Exception as e:
                print(f"Pipeline error for job {job_id}: {str(e)}")
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("""
                        UPDATE jobs 
                        SET status = 'failed', updated_at = %s
                        WHERE id = %s
                    """, (datetime.now(), job_id))
        
        # Start background thread
        thread = threading.Thread(target=run_pipeline_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Analysis started successfully',
            'jobId': job_id
        }), 200
        
    except Exception as e:
        print(f"Error starting analysis: {str(e)}")
        return jsonify({'error': f'Failed to start analysis: {str(e)}'}), 500

@upload_rationale_bp.route('/job/<job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    try:
        current_user_id = get_jwt_identity()
        
        # Check authorization
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        # Get job details from database
        with get_db_cursor() as cursor:
            # Fetch job record
            cursor.execute("""
                SELECT 
                    j.id, j.tool_used, j.title, j.date, j.time,
                    j.status, j.current_step, j.progress, 
                    j.created_at, j.updated_at,
                    c.channel_name, c.channel_logo_path,
                    sr.unsigned_pdf_path, sr.signed_pdf_path
                FROM jobs j
                LEFT JOIN channels c ON j.channel_id = c.id
                LEFT JOIN saved_rationale sr ON j.id = sr.job_id
                WHERE j.id = %s
            """, (job_id,))
            
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            # Fetch job steps
            cursor.execute("""
                SELECT step_number, step_name, status, message, 
                       output_files, started_at, ended_at
                FROM job_steps
                WHERE job_id = %s
                ORDER BY step_number ASC
            """, (job_id,))
            
            steps = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'job': {
                'id': job['id'],
                'toolUsed': job['tool_used'],
                'title': job['title'],
                'channelName': job.get('channel_name', ''),
                'channelLogo': f"/api/v1/channels/{job['channel_id']}/logo" if job.get('channel_logo_path') else '',
                'uploadDate': job['date'],
                'uploadTime': job['time'],
                'status': job['status'],
                'currentStep': job['current_step'],
                'progress': job['progress'],
                'createdAt': job['created_at'].isoformat() if job['created_at'] else None,
                'updatedAt': job['updated_at'].isoformat() if job['updated_at'] else None,
                'unsignedPdfPath': job.get('unsigned_pdf_path'),
                'signedPdfPath': job.get('signed_pdf_path'),
                'steps': [
                    {
                        'step_number': s['step_number'],
                        'step_name': s['step_name'],
                        'status': s['status'],
                        'message': s['message'],
                        'outputFiles': s['output_files'] or [],
                        'startedAt': s['started_at'].isoformat() if s['started_at'] else None,
                        'endedAt': s['ended_at'].isoformat() if s['ended_at'] else None,
                    }
                    for s in steps
                ]
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching job: {str(e)}")
        return jsonify({'error': f'Failed to fetch job: {str(e)}'}), 500

@upload_rationale_bp.route('/job/<job_id>/steps', methods=['GET'])
@jwt_required()
def get_job_steps(job_id):
    try:
        current_user_id = get_jwt_identity()
        
        # Check authorization
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        # Fetch job steps
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT step_number, step_name, status, message, 
                       output_files, started_at, ended_at
                FROM job_steps
                WHERE job_id = %s
                ORDER BY step_number ASC
            """, (job_id,))
            
            steps = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'steps': [
                {
                    'step_number': s['step_number'],
                    'step_name': s['step_name'],
                    'status': s['status'],
                    'message': s['message'],
                    'outputFiles': s['output_files'] or [],
                    'startedAt': s['started_at'].isoformat() if s['started_at'] else None,
                    'endedAt': s['ended_at'].isoformat() if s['ended_at'] else None,
                }
                for s in steps
            ]
        }), 200
        
    except Exception as e:
        print(f"Error fetching job steps: {str(e)}")
        return jsonify({'error': f'Failed to fetch job steps: {str(e)}'}), 500

@upload_rationale_bp.route('/job/<job_id>/csv', methods=['GET'])
@jwt_required()
def download_csv(job_id):
    try:
        current_user_id = get_jwt_identity()
        
        # Check authorization
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        # Build path to CSV file
        csv_path = _job_path(job_id, 'analysis', 'stocks_with_analysis.csv')
        
        if not os.path.exists(csv_path):
            return jsonify({'error': 'CSV file not found'}), 404
        
        return send_file(
            csv_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{job_id}_analysis.csv'
        )
        
    except Exception as e:
        print(f"Error downloading CSV: {str(e)}")
        return jsonify({'error': f'Failed to download CSV: {str(e)}'}), 500

@upload_rationale_bp.route('/job/<job_id>/csv', methods=['POST'])
@jwt_required()
def upload_csv(job_id):
    try:
        current_user_id = get_jwt_identity()
        
        # Check authorization
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        # Get uploaded CSV file
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        csv_file = request.files['file']
        
        if not csv_file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400
        
        # Save CSV file
        csv_path = _job_path(job_id, 'analysis', 'stocks_with_analysis.csv')
        csv_file.save(csv_path)
        
        # Update job status to resume pipeline
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET status = 'processing', updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
        
        # Continue pipeline from Step 11 (Generate Charts)
        def continue_pipeline():
            try:
                # Run steps 11-12 (Charts and PDF)
                all_success = True
                for step_num in range(11, 13):  # Steps 11-12
                    success = run_pipeline_step(job_id, step_num)
                    if not success:
                        all_success = False
                        break
                
                # After Step 12, set status to 'pdf_ready'
                if all_success:
                    with get_db_cursor(commit=True) as cursor:
                        cursor.execute("""
                            UPDATE jobs 
                            SET status = 'pdf_ready', progress = 93, updated_at = %s
                            WHERE id = %s
                        """, (datetime.now(), job_id))
                    print(f"Job {job_id}: PDF generation complete")
                
            except Exception as e:
                print(f"Pipeline continuation error for job {job_id}: {str(e)}")
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("""
                        UPDATE jobs 
                        SET status = 'failed', updated_at = %s
                        WHERE id = %s
                    """, (datetime.now(), job_id))
        
        # Start background thread
        thread = threading.Thread(target=continue_pipeline)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'CSV uploaded successfully, continuing pipeline...'
        }), 200
        
    except Exception as e:
        print(f"Error uploading CSV: {str(e)}")
        return jsonify({'error': f'Failed to upload CSV: {str(e)}'}), 500

@upload_rationale_bp.route('/job/<job_id>/download', methods=['GET'])
@jwt_required()
def download_pdf(job_id):
    try:
        current_user_id = get_jwt_identity()
        
        # Check authorization
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            # Return uniform 403 response to avoid information disclosure
            return jsonify({'error': 'Access denied'}), 403
        
        # Get the requested PDF path from query parameter
        pdf_relative_path = request.args.get('path', '')
        
        if not pdf_relative_path:
            return jsonify({'error': 'PDF path is required'}), 400
        
        # Resolve to absolute path
        pdf_path = resolve_job_folder_path(pdf_relative_path)
        
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'PDF not found'}), 404
        
        # Extract filename from path
        filename = os.path.basename(pdf_path)
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=False,  # Display inline in browser
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error downloading PDF: {str(e)}")
        return jsonify({'error': 'Failed to download PDF'}), 500

@upload_rationale_bp.route('/job/<job_id>', methods=['DELETE'])
@jwt_required()
def delete_job(job_id):
    try:
        current_user_id = get_jwt_identity()
        
        # Check authorization
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        # Delete job files from filesystem
        job_folder = os.path.join('backend', 'job_files', job_id)
        if os.path.exists(job_folder):
            shutil.rmtree(job_folder)
        
        # Delete job from database (cascade will delete job_steps)
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        
        return jsonify({
            'success': True,
            'message': 'Job deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"Error deleting job: {str(e)}")
        return jsonify({'error': f'Failed to delete job: {str(e)}'}), 500
