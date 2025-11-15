from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.utils.database import get_db_cursor
from backend.api import manual_rationale_bp
from backend.models.user import User
from datetime import datetime
import os
import secrets
import threading
import json
import csv

def is_admin(user_id):
    user = User.find_by_id(user_id)
    return user and user.get('role') == 'admin'

def load_master_stock_data():
    """
    Load master CSV and create lookup dictionary for EQUITY stocks
    Returns: dict mapping stock_symbol -> {securityId, listedName, shortName, exchange, instrument}
    """
    try:
        # Get master CSV file path from database
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT file_path FROM uploaded_files 
                WHERE file_type = 'masterFile' 
                ORDER BY uploaded_at DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if not result:
                return None
            
            master_csv_path = result['file_path']
        
        if not os.path.exists(master_csv_path):
            return None
        
        # Read master CSV and build lookup dictionary
        stock_lookup = {}
        with open(master_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Filter by EQUITY instrument
                instrument = row.get('SEM_INSTRUMENT_NAME', '')
                if instrument.upper() != 'EQUITY':
                    continue
                
                # Filter by ES exchange type
                exch_type = row.get('SEM_EXCH_INSTRUMENT_TYPE', '')
                if exch_type.upper() != 'ES':
                    continue
                
                # Get stock symbol from SEM_TRADING_SYMBOL
                stock_symbol = row.get('SEM_TRADING_SYMBOL', '').strip()
                
                if not stock_symbol:
                    continue
                
                # Store master data indexed by stock symbol (case-insensitive)
                stock_lookup[stock_symbol.upper()] = {
                    'securityId': row.get('SEM_SMST_SECURITY_ID', ''),
                    'listedName': row.get('SM_SYMBOL_NAME', ''),
                    'shortName': row.get('SEM_CUSTOM_SYMBOL', stock_symbol),
                    'exchange': row.get('SEM_EXM_EXCH_ID', 'BSE'),
                    'instrument': row.get('SEM_INSTRUMENT_NAME', 'EQUITY')
                }
        
        return stock_lookup
        
    except Exception as e:
        print(f"Error loading master stock data: {str(e)}")
        return None

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

@manual_rationale_bp.route('/create-job', methods=['POST'])
@jwt_required()
def create_job():
    """Create a new Manual Rationale job"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Extract input data
        channel_id = data.get('channelId')
        url = data.get('url', '')  # Optional YouTube URL
        call_date_raw = data.get('callDate')
        stocks = data.get('stocks', [])  # [{stockName, time, chartType, analysis}]
        
        if not channel_id or not call_date_raw or not stocks:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Normalize date to YYYY-MM-DD format (frontend may send DD/MM/YYYY, YYYY-MM-DD, or with time)
        try:
            # Strip time component if present (e.g., "09/11/2025 00:00:00" → "09/11/2025")
            date_part = call_date_raw.split()[0] if ' ' in call_date_raw else call_date_raw
            
            # Try parsing DD/MM/YYYY format first (common frontend format)
            if '/' in date_part:
                date_obj = datetime.strptime(date_part, '%d/%m/%Y')
            else:
                # Try ISO format YYYY-MM-DD
                date_obj = datetime.strptime(date_part, '%Y-%m-%d')
            
            call_date = date_obj.strftime('%Y-%m-%d')  # Normalize to ISO format
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use DD/MM/YYYY or YYYY-MM-DD'}), 400
        
        # Get channel details
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT id, channel_name, platform, channel_url 
                FROM channels 
                WHERE id = %s
            """, (channel_id,))
            channel = cursor.fetchone()
            
            if not channel:
                return jsonify({'error': 'Channel not found'}), 404
        
        # Load master stock data for automatic enrichment
        stock_lookup = load_master_stock_data()
        if stock_lookup is None:
            return jsonify({'error': 'Master CSV file not found or cannot be read'}), 500
        
        # Enrich stock data with master CSV lookup
        enriched_stocks = []
        missing_stocks = []
        
        for stock in stocks:
            stock_symbol = stock.get('stockName', '').strip().upper()
            
            if not stock_symbol:
                continue
            
            # Lookup master data
            master_data = stock_lookup.get(stock_symbol)
            
            if not master_data:
                missing_stocks.append(stock_symbol)
                continue
            
            # Enrich with master data
            enriched_stock = {
                'stockName': stock_symbol,
                'time': stock.get('time', ''),
                'chartType': stock.get('chartType', 'Daily'),
                'analysis': stock.get('analysis', ''),
                'securityId': master_data['securityId'],
                'listedName': master_data['listedName'],
                'shortName': master_data['shortName'],
                'exchange': master_data['exchange'],
                'instrument': master_data['instrument']
            }
            enriched_stocks.append(enriched_stock)
        
        # Validate that all stocks were found
        if missing_stocks:
            return jsonify({
                'error': f'Stock symbols not found in master CSV: {", ".join(missing_stocks)}'
            }), 400
        
        if not enriched_stocks:
            return jsonify({'error': 'No valid stocks provided'}), 400
        
        # Generate unique job ID
        job_id = f"manual-{secrets.token_hex(4)}"
        
        # Create job folder structure
        job_folder = os.path.join('backend', 'job_files', job_id)
        os.makedirs(job_folder, exist_ok=True)
        os.makedirs(os.path.join(job_folder, 'analysis'), exist_ok=True)
        os.makedirs(os.path.join(job_folder, 'charts'), exist_ok=True)
        os.makedirs(os.path.join(job_folder, 'pdf'), exist_ok=True)
        
        # Create input.csv with enriched master data
        input_csv_path = os.path.join(job_folder, 'analysis', 'input.csv')
        with open(input_csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['DATE', 'TIME', 'STOCK SYMBOL', 'CHART TYPE', 
                          'LISTED NAME', 'SHORT NAME', 'SECURITY ID', 'EXCHANGE', 'INSTRUMENT', 'ANALYSIS']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for stock in enriched_stocks:
                writer.writerow({
                    'DATE': call_date,
                    'TIME': stock['time'],
                    'STOCK SYMBOL': stock['stockName'],
                    'CHART TYPE': stock['chartType'],
                    'LISTED NAME': stock['listedName'],
                    'SHORT NAME': stock['shortName'],
                    'SECURITY ID': stock['securityId'],
                    'EXCHANGE': stock['exchange'],
                    'INSTRUMENT': stock['instrument'],
                    'ANALYSIS': stock['analysis']
                })
        
        # Generate rationale title
        rationale_title = f"{channel['platform'].upper()} - {channel['channel_name']} - {call_date}"
        
        # Store enriched stocks count
        stocks_str = ', '.join([s['stockName'] for s in enriched_stocks])
        
        # Create job record in database with youtube_url
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                INSERT INTO jobs (
                    id, user_id, channel_id, tool_used, title, 
                    date, time, youtube_url, status, current_step, 
                    progress, folder_path, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                job_id,
                current_user_id,
                channel_id,
                'Manual Rationale',
                rationale_title,
                call_date,
                '00:00:00',
                url if url else None,  # Store YouTube URL
                'pending',
                0,
                0,
                job_folder,
                datetime.now(),
                datetime.now()
            ))
            
            # Initialize job steps (3 steps for Manual Rationale - mapping is done at input creation)
            manual_steps = [
                {'step_number': 1, 'step_name': 'Fetch Current Market Price'},
                {'step_number': 2, 'step_name': 'Generate Stock Charts'},
                {'step_number': 3, 'step_name': 'Generate PDF Report'},
            ]
            
            for step in manual_steps:
                cursor.execute("""
                    INSERT INTO job_steps (job_id, step_number, step_name, status, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (job_id, step['step_number'], step['step_name'], 'pending', datetime.now()))
        
        # Start processing in background thread
        thread = threading.Thread(target=process_manual_job_async, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Manual Rationale job created successfully',
            'jobId': job_id,
            'title': rationale_title
        }), 201
        
    except Exception as e:
        print(f"Error creating Manual Rationale job: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_manual_job_async(job_id):
    """Process Manual Rationale job in background"""
    try:
        # Import pipeline steps
        from backend.pipeline.manual import (
            step01_fetch_cmp,
            step02_fetch_charts,
            step03_generate_pdf
        )
        
        # Update job status to processing
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET status = 'processing', current_step = 1, updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
        
        # Get job details
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
        
        job_folder = job['folder_path']
        
        # Get API keys from database
        with get_db_cursor() as cursor:
            cursor.execute("SELECT key_value FROM api_keys WHERE LOWER(provider) = 'dhan'")
            dhan_key_row = cursor.fetchone()
            dhan_api_key = dhan_key_row['key_value'] if dhan_key_row else None
        
        # Define pipeline steps (3 steps total - mapping done at input creation)
        steps = [
            (1, lambda: step01_fetch_cmp.run(job_folder, dhan_api_key)),
            (2, lambda: step02_fetch_charts.run(job_folder, dhan_api_key)),
            (3, lambda: step03_generate_pdf.run(job_folder)),
        ]
        
        # Execute steps sequentially
        for step_num, step_func in steps:
            # Update step status to running
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE job_steps 
                    SET status = 'running', started_at = %s
                    WHERE job_id = %s AND step_number = %s
                """, (datetime.now(), job_id, step_num))
                
                cursor.execute("""
                    UPDATE jobs 
                    SET current_step = %s, progress = %s, updated_at = %s
                    WHERE id = %s
                """, (step_num, (step_num - 1) * 25, datetime.now(), job_id))
            
            # Execute step
            result = step_func()
            
            if not result.get('success'):
                # Step failed
                error_msg = result.get('error', 'Unknown error')
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("""
                        UPDATE job_steps 
                        SET status = 'failed', message = %s, ended_at = %s
                        WHERE job_id = %s AND step_number = %s
                    """, (error_msg, datetime.now(), job_id, step_num))
                    
                    cursor.execute("""
                        UPDATE jobs 
                        SET status = 'failed', updated_at = %s
                        WHERE id = %s
                    """, (datetime.now(), job_id))
                return
            
            # Step succeeded
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE job_steps 
                    SET status = 'success', ended_at = %s
                    WHERE job_id = %s AND step_number = %s
                """, (datetime.now(), job_id, step_num))
        
        # All steps completed - mark job as pdf_ready
        # Note: jobs table doesn't have pdf_path column - PDF stored in saved_rationale table
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET status = 'pdf_ready', progress = 100, updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
        
        print(f"Manual Rationale job {job_id} completed successfully")
        
    except Exception as e:
        print(f"Error processing Manual Rationale job {job_id}: {str(e)}")
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET status = 'failed', updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))

@manual_rationale_bp.route('/jobs/<job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    """Get Manual Rationale job details"""
    try:
        current_user_id = get_jwt_identity()
        
        # Check access
        has_access, error = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error}), 403 if error == "Access denied" else 404
        
        # Get job details
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
            
            cursor.execute("SELECT * FROM job_steps WHERE job_id = %s ORDER BY step_number", (job_id,))
            steps = cursor.fetchall()
        
        # Get PDF path from saved_rationale if job is saved
        pdf_path = None
        with get_db_cursor() as cursor2:
            cursor2.execute("""
                SELECT unsigned_pdf_path FROM saved_rationale WHERE job_id = %s
            """, (job_id,))
            saved = cursor2.fetchone()
            if saved:
                pdf_path = saved['unsigned_pdf_path']
        
        return jsonify({
            'jobId': job['id'],
            'title': job['title'],
            'status': job['status'],
            'progress': job['progress'],
            'currentStep': job['current_step'],
            'pdfPath': pdf_path,
            'job_steps': [{
                'id': step['id'],
                'job_id': step['job_id'],
                'step_number': step['step_number'],
                'step_name': step['step_name'],
                'status': step['status'],
                'started_at': step['started_at'].isoformat() if step.get('started_at') else None,
                'ended_at': step['ended_at'].isoformat() if step.get('ended_at') else None,
                'error_message': step.get('error_message')
            } for step in steps]
        }), 200
        
    except Exception as e:
        print(f"Error getting job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@manual_rationale_bp.route('/job/<job_id>/save', methods=['POST'])
@jwt_required()
def save_job(job_id):
    """Save Manual Rationale job to saved_rationale table"""
    try:
        current_user_id = get_jwt_identity()
        
        # Check access
        has_access, error = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error}), 403 if error == "Access denied" else 404
        
        # Get job data
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()
        
        # Read stock symbols from input.csv
        input_csv_path = os.path.join(job['folder_path'], 'analysis', 'input.csv')
        stock_symbols = []
        if os.path.exists(input_csv_path):
            with open(input_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stock_symbols.append(row.get('STOCK SYMBOL', ''))
        
        stocks_str = ', '.join(stock_symbols) if stock_symbols else 'Manual Rationale'
        
        # Get actual PDF path from job folder
        pdf_path = os.path.join(job['folder_path'], 'pdf', 'premium_rationale.pdf')
        
        # Save to saved_rationale table
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                INSERT INTO saved_rationale (
                    job_id, user_id, channel_id, tool_used, stock_name,
                    youtube_url, video_upload_date, youtube_video_name,
                    unsigned_pdf_path, status, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    unsigned_pdf_path = EXCLUDED.unsigned_pdf_path,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
            """, (
                job_id,
                current_user_id,
                job['channel_id'],
                'Manual Rationale',
                stocks_str,
                job.get('youtube_url'),  # Use youtube_url from jobs table
                job['date'],
                job['title'],  # Use job title as youtube_video_name
                pdf_path,  # Actual PDF path: premium_rationale.pdf
                'completed',
                datetime.now(),
                datetime.now()
            ))
            
            # Update job status
            cursor.execute("""
                UPDATE jobs 
                SET status = 'completed', updated_at = %s
                WHERE id = %s
            """, (datetime.now(), job_id))
        
        return jsonify({'success': True, 'message': 'Job saved successfully'}), 200
        
    except Exception as e:
        print(f"Error saving job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@manual_rationale_bp.route('/jobs/<job_id>', methods=['DELETE'])
@jwt_required()
def delete_job(job_id):
    """Delete Manual Rationale job"""
    try:
        current_user_id = get_jwt_identity()
        
        # Check access
        has_access, error = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error}), 403 if error == "Access denied" else 404
        
        # Delete job
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM job_steps WHERE job_id = %s", (job_id,))
            cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        
        return jsonify({'success': True, 'message': 'Job deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting job: {str(e)}")
        return jsonify({'error': str(e)}), 500

@manual_rationale_bp.route('/restart-step/<job_id>/<int:step_number>', methods=['POST'])
@jwt_required()
def restart_step(job_id, step_number):
    """Restart Manual Rationale job from a specific step"""
    try:
        current_user_id = get_jwt_identity()
        
        # Check access
        has_access, error = check_job_access(job_id, current_user_id)
        if not has_access:
            return jsonify({'error': error}), 403 if error == "Access denied" else 404
        
        # Reset steps from step_number onwards
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE job_steps 
                SET status = 'pending', started_at = NULL, ended_at = NULL, error_message = NULL
                WHERE job_id = %s AND step_number >= %s
            """, (job_id, step_number))
            
            cursor.execute("""
                UPDATE jobs 
                SET status = 'pending', current_step = %s, updated_at = %s
                WHERE id = %s
            """, (step_number - 1, datetime.now(), job_id))
        
        # Restart processing from the specified step
        thread = threading.Thread(target=process_manual_job_async, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': f'Job restarted from step {step_number}'}), 200
        
    except Exception as e:
        print(f"Error restarting job: {str(e)}")
        return jsonify({'error': str(e)}), 500
