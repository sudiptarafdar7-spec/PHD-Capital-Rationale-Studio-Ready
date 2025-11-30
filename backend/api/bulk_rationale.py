"""
Bulk Rationale API Endpoints
"""

from flask import request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.api import bulk_rationale_bp
from backend.utils.database import get_db_cursor
from backend.api.activity_logs import create_activity_log
from backend.utils.path_utils import resolve_job_folder_path
from datetime import datetime
import os
import uuid
import threading


BULK_STEPS = [
    {"step_number": 1, "name": "Translate", "description": "Translate input text to English"},
    {"step_number": 2, "name": "Convert to CSV", "description": "Convert text to structured CSV"},
    {"step_number": 3, "name": "Map Master File", "description": "Map stocks to master data"},
    {"step_number": 4, "name": "Fetch CMP", "description": "Fetch current market prices"},
    {"step_number": 5, "name": "Generate Charts", "description": "Generate stock charts"},
    {"step_number": 6, "name": "Generate PDF", "description": "Create final PDF report"},
]


def run_bulk_pipeline(job_id, job_folder, call_date, call_time, start_step=1):
    """Run the bulk rationale pipeline in background
    
    Args:
        job_id: Job identifier
        job_folder: Path to job folder
        call_date: Date of the call
        call_time: Time of the call
        start_step: Step number to start from (default 1)
    """
    from backend.pipeline.bulk import (
        step01_translate,
        step02_convert_csv,
        step03_map_master,
        step04_fetch_cmp,
        step05_generate_charts,
        step06_generate_pdf
    )
    
    steps = [
        (1, "Translate", step01_translate.run, [job_folder]),
        (2, "Convert to CSV", step02_convert_csv.run, [job_folder, call_date, call_time]),
        (3, "Map Master File", step03_map_master.run, [job_folder]),
        (4, "Fetch CMP", step04_fetch_cmp.run, [job_folder]),
        (5, "Generate Charts", step05_generate_charts.run, [job_folder]),
        (6, "Generate PDF", step06_generate_pdf.run, [job_folder]),
    ]
    
    try:
        for step_num, step_name, step_func, step_args in steps:
            if step_num < start_step:
                print(f"⏭️ Skipping Step {step_num}: {step_name} (already completed)")
                continue
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE job_steps 
                    SET status = 'running', started_at = %s
                    WHERE job_id = %s AND step_number = %s
                """, (datetime.now(), job_id, step_num))
                
                cursor.execute("""
                    UPDATE jobs SET current_step = %s, progress = %s, updated_at = %s
                    WHERE id = %s
                """, (step_num, int((step_num - 1) / 6 * 100), datetime.now(), job_id))
            
            print(f"\n{'='*60}")
            print(f"Running Step {step_num}: {step_name}")
            print(f"{'='*60}")
            
            result = step_func(*step_args)
            
            if result.get('success'):
                with get_db_cursor(commit=True) as cursor:
                    output_files = [result.get('output_file')] if result.get('output_file') else []
                    cursor.execute("""
                        UPDATE job_steps 
                        SET status = 'success', 
                            ended_at = %s,
                            output_files = %s,
                            message = %s
                        WHERE job_id = %s AND step_number = %s
                    """, (datetime.now(), output_files, f"Step {step_num} completed", job_id, step_num))
            else:
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("""
                        UPDATE job_steps 
                        SET status = 'failed', 
                            ended_at = %s,
                            message = %s
                        WHERE job_id = %s AND step_number = %s
                    """, (datetime.now(), result.get('error', 'Unknown error'), job_id, step_num))
                    
                    cursor.execute("""
                        UPDATE jobs SET status = 'failed', updated_at = %s
                        WHERE id = %s
                    """, (datetime.now(), job_id))
                
                print(f"❌ Step {step_num} failed: {result.get('error')}")
                return
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET status = 'pdf_ready', progress = 100, current_step = 6, updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
        
        print(f"\n✅ Bulk Rationale pipeline completed for job {job_id}")
        
    except Exception as e:
        print(f"❌ Pipeline error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE jobs SET status = 'failed', updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))


@bulk_rationale_bp.route('/create-job', methods=['POST'])
@jwt_required()
def create_job():
    """Create a new bulk rationale job"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        channel_id = data.get('channelId')
        youtube_url = data.get('youtubeUrl', '')
        call_date = data.get('callDate')
        call_time = data.get('callTime', '10:00:00')
        input_text = data.get('inputText', '')
        
        if not channel_id or not call_date or not input_text.strip():
            return jsonify({'error': 'Channel, date, and input text are required'}), 400
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                SELECT channel_name, platform FROM channels WHERE id = %s
            """, (channel_id,))
            channel = cursor.fetchone()
            
            if not channel:
                return jsonify({'error': 'Channel not found'}), 404
            
            channel_name = channel['channel_name']
            platform = channel['platform']
            
            job_id = f"bulk-{uuid.uuid4().hex[:8]}"
            title = f"{platform} - {channel_name} - {call_date}"
            
            job_folder = f"backend/job_files/{job_id}"
            os.makedirs(job_folder, exist_ok=True)
            os.makedirs(os.path.join(job_folder, 'analysis'), exist_ok=True)
            os.makedirs(os.path.join(job_folder, 'charts'), exist_ok=True)
            os.makedirs(os.path.join(job_folder, 'pdf'), exist_ok=True)
            
            input_file_path = os.path.join(job_folder, 'bulk-input.txt')
            with open(input_file_path, 'w', encoding='utf-8') as f:
                f.write(input_text)
            
            cursor.execute("""
                INSERT INTO jobs (id, youtube_url, title, channel_id, date, time, 
                                  user_id, tool_used, status, progress, current_step, folder_path,
                                  created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                job_id, youtube_url, title, channel_id, call_date, call_time,
                current_user_id, 'Bulk Rationale', 'processing', 0, 0, job_folder,
                datetime.now(), datetime.now()
            ))
            
            for step in BULK_STEPS:
                cursor.execute("""
                    INSERT INTO job_steps (job_id, step_number, step_name, status, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (job_id, step['step_number'], step['name'], 'pending', datetime.now()))
            
            create_activity_log(
                current_user_id,
                'job_started',
                f'Started Bulk Rationale: {title}',
                job_id,
                'Bulk Rationale'
            )
        
        thread = threading.Thread(
            target=run_bulk_pipeline,
            args=(job_id, job_folder, call_date, call_time)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'jobId': job_id,
            'title': title,
            'message': 'Bulk Rationale job started'
        }), 200
        
    except Exception as e:
        print(f"Error creating bulk job: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/jobs/<job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    """Get bulk rationale job status and details"""
    try:
        current_user_id = get_jwt_identity()
        
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT j.*, c.channel_name, c.platform
                FROM jobs j
                LEFT JOIN channels c ON j.channel_id = c.id
                WHERE j.id = %s AND j.user_id = %s
            """, (job_id, current_user_id))
            
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            cursor.execute("""
                SELECT * FROM job_steps 
                WHERE job_id = %s 
                ORDER BY step_number
            """, (job_id,))
            
            steps = cursor.fetchall()
            
            pdf_path = None
            if job['status'] in ['pdf_ready', 'completed', 'signed']:
                pdf_folder = os.path.join(job['folder_path'], 'pdf')
                pdf_file = os.path.join(pdf_folder, 'bulk_rationale.pdf')
                if os.path.exists(pdf_file):
                    pdf_path = pdf_file
            
            cursor.execute("""
                SELECT unsigned_pdf_path, signed_pdf_path, sign_status
                FROM saved_rationale
                WHERE job_id = %s
            """, (job_id,))
            saved = cursor.fetchone()
        
        return jsonify({
            'jobId': job['id'],
            'title': job['title'],
            'status': job['status'],
            'progress': job['progress'],
            'currentStep': job['current_step'],
            'channelName': job.get('channel_name'),
            'platform': job.get('platform'),
            'date': str(job['date']) if job['date'] else None,
            'time': str(job['time']) if job['time'] else None,
            'youtubeUrl': job['youtube_url'],
            'pdfPath': pdf_path,
            'unsignedPdfPath': saved['unsigned_pdf_path'] if saved else None,
            'signedPdfPath': saved['signed_pdf_path'] if saved else None,
            'signStatus': saved['sign_status'] if saved else None,
            'job_steps': [dict(s) for s in steps],
            'createdAt': job['created_at'].isoformat() if job['created_at'] else None,
            'updatedAt': job['updated_at'].isoformat() if job['updated_at'] else None
        }), 200
        
    except Exception as e:
        print(f"Error getting job: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/jobs/<job_id>', methods=['DELETE'])
@jwt_required()
def delete_job(job_id):
    """Delete a bulk rationale job"""
    try:
        current_user_id = get_jwt_identity()
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                SELECT folder_path FROM jobs 
                WHERE id = %s AND user_id = %s
            """, (job_id, current_user_id))
            
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            cursor.execute("DELETE FROM saved_rationale WHERE job_id = %s", (job_id,))
            cursor.execute("DELETE FROM job_steps WHERE job_id = %s", (job_id,))
            cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
            
            if job['folder_path'] and os.path.exists(job['folder_path']):
                import shutil
                shutil.rmtree(job['folder_path'], ignore_errors=True)
        
        return jsonify({
            'success': True,
            'message': 'Job deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"Error deleting job: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/save', methods=['POST'])
@jwt_required()
def save_job(job_id):
    """Save bulk rationale job to saved_rationale table"""
    try:
        current_user_id = get_jwt_identity()
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                SELECT j.*, c.channel_name
                FROM jobs j
                LEFT JOIN channels c ON j.channel_id = c.id
                WHERE j.id = %s AND j.user_id = %s
            """, (job_id, current_user_id))
            
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            if job['status'] not in ['pdf_ready', 'completed']:
                return jsonify({'error': 'PDF not ready yet'}), 400
            
            cursor.execute("SELECT id FROM saved_rationale WHERE job_id = %s", (job_id,))
            existing = cursor.fetchone()
            
            if existing:
                return jsonify({'error': 'Job already saved'}), 400
            
            pdf_path = os.path.join(job['folder_path'], 'pdf', 'bulk_rationale.pdf')
            
            if not os.path.exists(pdf_path):
                return jsonify({'error': 'PDF file not found'}), 404
            
            cursor.execute("""
                INSERT INTO saved_rationale (
                    job_id, tool_used, channel_id, title, date, youtube_url,
                    unsigned_pdf_path, sign_status, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                job_id, 'Bulk Rationale', job['channel_id'], job['title'],
                job['date'], job['youtube_url'], pdf_path, 'Unsigned',
                datetime.now(), datetime.now()
            ))
            
            rationale_id = cursor.fetchone()['id']
            
            cursor.execute("""
                UPDATE jobs SET status = 'completed', updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
            
            create_activity_log(
                current_user_id,
                'job_completed',
                f'Saved Bulk Rationale: {job["title"]}',
                job_id,
                'Bulk Rationale'
            )
        
        return jsonify({
            'success': True,
            'rationaleId': rationale_id,
            'message': 'Rationale saved successfully'
        }), 200
        
    except Exception as e:
        print(f"Error saving job: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/download', methods=['GET'])
@jwt_required()
def download_pdf(job_id):
    """Download the generated PDF"""
    try:
        current_user_id = get_jwt_identity()
        
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT folder_path FROM jobs 
                WHERE id = %s AND user_id = %s
            """, (job_id, current_user_id))
            
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
        
        resolved_folder = resolve_job_folder_path(job['folder_path'])
        pdf_path = os.path.join(resolved_folder, 'pdf', 'bulk_rationale.pdf')
        
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'PDF not found'}), 404
        
        return send_file(
            pdf_path,
            as_attachment=False,
            download_name=f'{job_id}_bulk_rationale.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error downloading PDF: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/upload-signed', methods=['POST'])
@jwt_required()
def upload_signed_pdf(job_id):
    """Upload signed PDF"""
    try:
        current_user_id = get_jwt_identity()
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files allowed'}), 400
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                SELECT j.folder_path, sr.id as rationale_id
                FROM jobs j
                LEFT JOIN saved_rationale sr ON j.id = sr.job_id
                WHERE j.id = %s AND j.user_id = %s
            """, (job_id, current_user_id))
            
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            if not job['rationale_id']:
                return jsonify({'error': 'Please save the job first'}), 400
            
            signed_filename = f'bulk_rationale_signed.pdf'
            signed_path = os.path.join(job['folder_path'], 'pdf', signed_filename)
            
            file.save(signed_path)
            
            cursor.execute("""
                UPDATE saved_rationale
                SET signed_pdf_path = %s, sign_status = 'Signed', 
                    signed_uploaded_at = %s, updated_at = %s
                WHERE job_id = %s
            """, (signed_path, datetime.now(), datetime.now(), job_id))
            
            cursor.execute("""
                UPDATE jobs SET status = 'signed', updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
        
        return jsonify({
            'success': True,
            'message': 'Signed PDF uploaded successfully',
            'signedPath': signed_path
        }), 200
        
    except Exception as e:
        print(f"Error uploading signed PDF: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/restart-step/<job_id>/<int:step_number>', methods=['POST'])
@jwt_required()
def restart_step(job_id, step_number):
    """Restart a failed step"""
    try:
        current_user_id = get_jwt_identity()
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                SELECT j.folder_path, j.date, j.time
                FROM jobs j
                WHERE j.id = %s AND j.user_id = %s
            """, (job_id, current_user_id))
            
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            cursor.execute("""
                UPDATE job_steps 
                SET status = 'pending', message = NULL, started_at = NULL, ended_at = NULL
                WHERE job_id = %s AND step_number >= %s
            """, (job_id, step_number))
            
            cursor.execute("""
                UPDATE jobs 
                SET status = 'processing', current_step = %s, updated_at = %s
                WHERE id = %s
            """, (step_number - 1, datetime.now(), job_id))
        
        call_date = str(job['date']) if job['date'] else datetime.now().strftime('%Y-%m-%d')
        call_time = str(job['time']) if job['time'] else '10:00:00'
        
        thread = threading.Thread(
            target=run_bulk_pipeline,
            args=(job_id, job['folder_path'], call_date, call_time, step_number)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Restarting from step {step_number}'
        }), 200
        
    except Exception as e:
        print(f"Error restarting step: {str(e)}")
        return jsonify({'error': str(e)}), 500
