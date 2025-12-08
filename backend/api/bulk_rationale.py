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
import pandas as pd
import numpy as np


BULK_STEPS = [
    {"step_number": 1, "name": "Translate", "description": "Translate input text to English"},
    {"step_number": 2, "name": "Convert to CSV", "description": "Convert text to structured CSV"},
    {"step_number": 3, "name": "Polish Analysis", "description": "Polish analysis text professionally"},
    {"step_number": 4, "name": "Map Master File", "description": "Map stocks to master data"},
    {"step_number": 5, "name": "Fetch CMP", "description": "Fetch current market prices"},
    {"step_number": 6, "name": "Generate Charts", "description": "Generate stock charts"},
    {"step_number": 7, "name": "Generate PDF", "description": "Create final PDF report"},
]


def run_bulk_pipeline(job_id, job_folder, call_date, call_time, start_step=1, end_step=None):
    """Run the bulk rationale pipeline in background
    
    Args:
        job_id: Job identifier
        job_folder: Path to job folder
        call_date: Date of the call
        call_time: Time of the call
        start_step: Step number to start from (default 1)
        end_step: Step number to end at (optional, for pausing at checkpoints)
    """
    from backend.pipeline.bulk import (
        step01_translate,
        step02_convert_csv,
        step02b_polish_analysis,
        step03_map_master,
        step04_fetch_cmp,
        step05_generate_charts,
        step06_generate_pdf
    )
    
    steps = [
        (1, "Translate", step01_translate.run, [job_folder]),
        (2, "Convert to CSV", step02_convert_csv.run, [job_folder, call_date, call_time]),
        (3, "Polish Analysis", step02b_polish_analysis.run, [job_folder]),
        (4, "Map Master File", step03_map_master.run, [job_folder]),
        (5, "Fetch CMP", step04_fetch_cmp.run, [job_folder]),
        (6, "Generate Charts", step05_generate_charts.run, [job_folder, call_date, call_time]),
        (7, "Generate PDF", step06_generate_pdf.run, [job_folder]),
    ]
    
    try:
        for step_num, step_name, step_func, step_args in steps:
            if step_num < start_step:
                print(f"⏭️ Skipping Step {step_num}: {step_name} (already completed)")
                continue
            
            if end_step is not None and step_num > end_step:
                print(f"⏸️ Pausing before Step {step_num}: {step_name}")
                break
                
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE job_steps 
                    SET status = 'running', started_at = %s
                    WHERE job_id = %s AND step_number = %s
                """, (datetime.now(), job_id, step_num))
                
                cursor.execute("""
                    UPDATE jobs SET current_step = %s, progress = %s, updated_at = %s
                    WHERE id = %s
                """, (step_num, int((step_num - 1) / 7 * 100), datetime.now(), job_id))
            
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
                
                # After Step 4 completes, pause for CSV review
                if step_num == 4:
                    with get_db_cursor(commit=True) as cursor:
                        cursor.execute("""
                            UPDATE jobs 
                            SET status = 'awaiting_step4_review', progress = 57, updated_at = %s
                            WHERE id = %s
                        """, (datetime.now(), job_id))
                    print(f"Job {job_id}: Paused after Step 4 for mapped master file CSV review")
                    return
                
                # After Step 6 (Generate Charts), check for failed charts
                if step_num == 6:
                    failed_charts = result.get('failed_charts', [])
                    if failed_charts:
                        import json
                        with get_db_cursor(commit=True) as cursor:
                            cursor.execute("""
                                UPDATE jobs 
                                SET status = 'awaiting_chart_upload', progress = 85, updated_at = %s
                                WHERE id = %s
                            """, (datetime.now(), job_id))
                            
                            # Store failed charts info in job_steps message
                            cursor.execute("""
                                UPDATE job_steps 
                                SET message = %s
                                WHERE job_id = %s AND step_number = %s
                            """, (json.dumps({'failed_charts': failed_charts, 'success_count': result.get('success_count', 0)}), job_id, step_num))
                        
                        print(f"Job {job_id}: Paused after Step 6 - {len(failed_charts)} chart(s) need manual upload")
                        return
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
        
        # Only mark as pdf_ready if we completed all steps
        if end_step is None or end_step >= 7:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE jobs 
                    SET status = 'pdf_ready', progress = 100, current_step = 7, updated_at = %s
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


def _job_path(job_id, *path_parts):
    """Helper to get path within job folder"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT folder_path FROM jobs WHERE id = %s", (job_id,))
        result = cursor.fetchone()
        if result:
            folder_path = resolve_job_folder_path(result['folder_path'])
            return os.path.join(folder_path, *path_parts)
    return None


def check_job_access(job_id, user_id):
    """Check if user has access to job"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id FROM jobs WHERE id = %s AND user_id = %s
        """, (job_id, user_id))
        job = cursor.fetchone()
        if not job:
            return False, "Job not found or access denied"
    return True, None


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
                resolved_folder = resolve_job_folder_path(job['folder_path'])
                pdf_folder = os.path.join(resolved_folder, 'pdf')
                if os.path.exists(pdf_folder):
                    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf') and not f.startswith('bulk_rationale_signed')]
                    if pdf_files:
                        pdf_path = os.path.join(pdf_folder, pdf_files[0])
            
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
        pdf_folder = os.path.join(resolved_folder, 'pdf')
        
        pdf_path = None
        if os.path.exists(pdf_folder):
            pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf') and not f.startswith('bulk_rationale_signed')]
            if pdf_files:
                pdf_path = os.path.join(pdf_folder, pdf_files[0])
        
        if not pdf_path or not os.path.exists(pdf_path):
            return jsonify({'error': 'PDF not found'}), 404
        
        return send_file(
            pdf_path,
            as_attachment=False,
            download_name=os.path.basename(pdf_path),
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


# ==================== Step 4 CSV Review Endpoints ====================

@bulk_rationale_bp.route('/jobs/<job_id>/step4-csv-preview', methods=['GET'])
@jwt_required()
def get_step4_csv_preview(job_id):
    """Get mapped_master_file.csv content for preview after Step 4"""
    try:
        current_user_id = get_jwt_identity()
        
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        csv_path = _job_path(job_id, 'analysis', 'mapped_master_file.csv')
        
        if not csv_path or not os.path.exists(csv_path):
            return jsonify({'error': 'mapped_master_file.csv not found'}), 404
        
        df = pd.read_csv(csv_path)
        
        data = df.to_dict('records')
        for row in data:
            for key, value in row.items():
                if pd.isna(value) or (isinstance(value, (int, float, np.number)) and not np.isfinite(value)):
                    row[key] = None
        
        return jsonify({
            'success': True,
            'data': data,
            'columns': df.columns.tolist()
        }), 200
        
    except Exception as e:
        print(f"Error getting Step 4 CSV preview: {str(e)}")
        return jsonify({'error': f'Failed to get CSV preview: {str(e)}'}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/step4-download-csv', methods=['GET'])
@jwt_required()
def download_step4_csv(job_id):
    """Download mapped_master_file.csv file"""
    try:
        current_user_id = get_jwt_identity()
        
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        csv_path = _job_path(job_id, 'analysis', 'mapped_master_file.csv')
        
        if not csv_path or not os.path.exists(csv_path):
            return jsonify({'error': 'mapped_master_file.csv not found'}), 404
        
        return send_file(
            csv_path,
            as_attachment=True,
            download_name='mapped_master_file.csv',
            mimetype='text/csv'
        )
        
    except Exception as e:
        print(f"Error downloading Step 4 CSV: {str(e)}")
        return jsonify({'error': f'Failed to download CSV: {str(e)}'}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/step4-upload-csv', methods=['POST'])
@jwt_required()
def upload_step4_csv(job_id):
    """Upload and replace mapped_master_file.csv file"""
    try:
        current_user_id = get_jwt_identity()
        
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400
        
        csv_path = _job_path(job_id, 'analysis', 'mapped_master_file.csv')
        
        if not csv_path:
            return jsonify({'error': 'Job folder not found'}), 404
        
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        file.save(csv_path)
        
        return jsonify({
            'success': True,
            'message': 'mapped_master_file.csv uploaded and replaced successfully'
        }), 200
        
    except Exception as e:
        print(f"Error uploading Step 4 CSV: {str(e)}")
        return jsonify({'error': f'Failed to upload CSV: {str(e)}'}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/step4-continue-pipeline', methods=['POST'])
@jwt_required()
def step4_continue_pipeline(job_id):
    """Continue pipeline execution from Step 5 after Step 4 CSV review"""
    try:
        current_user_id = get_jwt_identity()
        
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id, status, folder_path, date, time FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            if job['status'] != 'awaiting_step4_review':
                return jsonify({'error': 'Job is not in awaiting_step4_review status'}), 400
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET status = 'processing', current_step = 5, updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
        
        call_date = str(job['date']) if job['date'] else datetime.now().strftime('%Y-%m-%d')
        call_time = str(job['time']) if job['time'] else '10:00:00'
        
        def run_remaining_steps():
            try:
                run_bulk_pipeline(
                    job_id, 
                    resolve_job_folder_path(job['folder_path']), 
                    call_date, 
                    call_time, 
                    start_step=5
                )
            except Exception as e:
                print(f"Error continuing pipeline from Step 5 for job {job_id}: {str(e)}")
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("""
                        UPDATE jobs 
                        SET status = 'failed', updated_at = %s
                        WHERE id = %s
                    """, (datetime.now(), job_id))
        
        thread = threading.Thread(target=run_remaining_steps)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Pipeline continuing from Step 5'
        }), 200
        
    except Exception as e:
        print(f"Error continuing pipeline from Step 4: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/failed-charts', methods=['GET'])
@jwt_required()
def get_failed_charts(job_id):
    """Get list of failed charts for a job"""
    try:
        current_user_id = get_jwt_identity()
        
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        with get_db_cursor() as cursor:
            cursor.execute("SELECT status, folder_path FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            cursor.execute("""
                SELECT message FROM job_steps 
                WHERE job_id = %s AND step_number = 6
            """, (job_id,))
            step = cursor.fetchone()
        
        failed_charts = []
        success_count = 0
        
        if step and step['message']:
            try:
                import json
                data = json.loads(step['message'])
                failed_charts = data.get('failed_charts', [])
                success_count = data.get('success_count', 0)
            except (json.JSONDecodeError, TypeError):
                pass
        
        job_folder = resolve_job_folder_path(job['folder_path'])
        failed_charts_file = os.path.join(job_folder, 'analysis', 'failed_charts.json')
        
        if not failed_charts and os.path.exists(failed_charts_file):
            try:
                import json
                with open(failed_charts_file, 'r', encoding='utf-8') as f:
                    failed_charts = json.load(f)
            except Exception:
                pass
        
        return jsonify({
            'success': True,
            'failed_charts': failed_charts,
            'success_count': success_count,
            'status': job['status']
        }), 200
        
    except Exception as e:
        print(f"Error getting failed charts: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/upload-chart/<int:stock_index>', methods=['POST'])
@jwt_required()
def upload_chart(job_id, stock_index):
    """Upload a chart for a specific failed stock"""
    try:
        current_user_id = get_jwt_identity()
        
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        if 'chart' not in request.files:
            return jsonify({'error': 'No chart file provided'}), 400
        
        chart_file = request.files['chart']
        if chart_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        ext = chart_file.filename.rsplit('.', 1)[-1].lower() if '.' in chart_file.filename else ''
        if ext not in allowed_extensions:
            return jsonify({'error': 'Only PNG/JPG files are allowed'}), 400
        
        with get_db_cursor() as cursor:
            cursor.execute("SELECT folder_path FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
        
        job_folder = resolve_job_folder_path(job['folder_path'])
        charts_folder = os.path.join(job_folder, 'charts')
        analysis_folder = os.path.join(job_folder, 'analysis')
        stocks_file = os.path.join(analysis_folder, 'stocks_with_charts.csv')
        
        if not os.path.exists(stocks_file):
            return jsonify({'error': 'Stocks CSV file not found'}), 404
        
        df = pd.read_csv(stocks_file)
        
        if stock_index < 0 or stock_index >= len(df):
            return jsonify({'error': 'Invalid stock index'}), 400
        
        stock_name = str(df.iloc[stock_index].get('INPUT STOCK', f'stock_{stock_index}')).strip()
        symbol = str(df.iloc[stock_index].get('STOCK SYMBOL', '')).strip()
        
        safe_name = ''.join(c if c.isalnum() else '_' for c in (symbol or stock_name))
        filename = f"manual_{safe_name}_{stock_index}.{ext}"
        save_path = os.path.join(charts_folder, filename)
        
        chart_file.save(save_path)
        
        relative_path = f"charts/{filename}"
        df.at[stock_index, 'CHART PATH'] = relative_path
        df.to_csv(stocks_file, index=False, encoding='utf-8-sig')
        
        failed_charts_file = os.path.join(analysis_folder, 'failed_charts.json')
        if os.path.exists(failed_charts_file):
            try:
                import json
                with open(failed_charts_file, 'r', encoding='utf-8') as f:
                    failed_list = json.load(f)
                
                failed_list = [fc for fc in failed_list if fc.get('index') != stock_index]
                
                with open(failed_charts_file, 'w', encoding='utf-8') as f:
                    json.dump(failed_list, f, indent=2)
                
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("""
                        SELECT message FROM job_steps 
                        WHERE job_id = %s AND step_number = 6
                    """, (job_id,))
                    step = cursor.fetchone()
                    
                    if step and step['message']:
                        try:
                            data = json.loads(step['message'])
                            data['failed_charts'] = failed_list
                            cursor.execute("""
                                UPDATE job_steps 
                                SET message = %s
                                WHERE job_id = %s AND step_number = 6
                            """, (json.dumps(data), job_id))
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
            except Exception as e:
                print(f"Error updating failed charts list: {e}")
        
        print(f"✅ Chart uploaded for stock {stock_name} (index {stock_index}): {filename}")
        
        return jsonify({
            'success': True,
            'message': f'Chart uploaded successfully for {stock_name}',
            'chart_path': relative_path
        }), 200
        
    except Exception as e:
        print(f"Error uploading chart: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/step6-continue-pipeline', methods=['POST'])
@jwt_required()
def step6_continue_pipeline(job_id):
    """Continue pipeline execution from Step 7 (PDF) after chart uploads"""
    try:
        current_user_id = get_jwt_identity()
        
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id, status, folder_path, date, time FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            if job['status'] != 'awaiting_chart_upload':
                return jsonify({'error': 'Job is not in awaiting_chart_upload status'}), 400
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET status = 'processing', current_step = 7, updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
        
        call_date = str(job['date']) if job['date'] else datetime.now().strftime('%Y-%m-%d')
        call_time = str(job['time']) if job['time'] else '10:00:00'
        
        def run_pdf_step():
            try:
                run_bulk_pipeline(
                    job_id, 
                    resolve_job_folder_path(job['folder_path']), 
                    call_date, 
                    call_time, 
                    start_step=7
                )
            except Exception as e:
                print(f"Error running PDF step for job {job_id}: {str(e)}")
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("""
                        UPDATE jobs 
                        SET status = 'failed', updated_at = %s
                        WHERE id = %s
                    """, (datetime.now(), job_id))
        
        thread = threading.Thread(target=run_pdf_step)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Generating PDF report...'
        }), 200
        
    except Exception as e:
        print(f"Error continuing to PDF generation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bulk_rationale_bp.route('/jobs/<job_id>/skip-failed-charts', methods=['POST'])
@jwt_required()
def skip_failed_charts(job_id):
    """Skip failed charts and continue to PDF generation without them"""
    try:
        current_user_id = get_jwt_identity()
        
        has_access, error_msg = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error_msg}), 403
        
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id, status, folder_path, date, time FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            if job['status'] != 'awaiting_chart_upload':
                return jsonify({'error': 'Job is not in awaiting_chart_upload status'}), 400
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET status = 'processing', current_step = 7, updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
        
        call_date = str(job['date']) if job['date'] else datetime.now().strftime('%Y-%m-%d')
        call_time = str(job['time']) if job['time'] else '10:00:00'
        
        def run_pdf_step():
            try:
                run_bulk_pipeline(
                    job_id, 
                    resolve_job_folder_path(job['folder_path']), 
                    call_date, 
                    call_time, 
                    start_step=7
                )
            except Exception as e:
                print(f"Error running PDF step for job {job_id}: {str(e)}")
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("""
                        UPDATE jobs 
                        SET status = 'failed', updated_at = %s
                        WHERE id = %s
                    """, (datetime.now(), job_id))
        
        thread = threading.Thread(target=run_pdf_step)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Skipping failed charts and generating PDF...'
        }), 200
        
    except Exception as e:
        print(f"Error skipping failed charts: {str(e)}")
        return jsonify({'error': str(e)}), 500
