#!/usr/bin/env python
"""
LipSync Fusion - Main Flask Application
Simple web interface for hybrid lip-sync generation
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from loguru import logger

# Initialize Flask app
app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')

CORS(app)

# Configuration
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('outputs')
TEMP_FOLDER = Path('temp')

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
TEMP_FOLDER.mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_FILE_SIZE'] = 500 * 1024 * 1024  # 500MB

logger.add('logs/app.log', rotation='500 MB')

# Job tracking
jobs = {}


def allowed_file(filename, file_type):
    """Check if file extension is allowed."""
    if file_type == 'image':
        allowed = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    elif file_type == 'video':
        allowed = {'mp4', 'webm', 'avi', 'mov', 'mkv'}
    elif file_type == 'audio':
        allowed = {'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'}
    else:
        return False
    
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/')
def index():
    """Serve main web interface."""
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status and capabilities."""
    return jsonify({
        'status': 'online',
        'version': '1.0.0',
        'models': {
            'lipsync': ['musetalk', 'wav2lip', 'latentsync', 'auto'],
            'emotion': ['neutral', 'happy', 'sad', 'surprised', 'angry'],
            'motion': ['subtle', 'normal', 'exaggerated']
        },
        'max_video_size_mb': app.config['MAX_FILE_SIZE'] // (1024 * 1024),
        'supported_formats': {
            'input_video': ['mp4', 'webm', 'avi', 'mov'],
            'input_image': ['png', 'jpg', 'jpeg'],
            'input_audio': ['mp3', 'wav', 'm4a', 'aac'],
            'output': ['mp4', 'webm']
        }
    })


@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    job_id = str(uuid.uuid4())
    
    try:
        if 'media' not in request.files or 'audio' not in request.files:
            return jsonify({'error': 'Missing media or audio file'}), 400
        
        media_file = request.files['media']
        audio_file = request.files['audio']
        
        if media_file.filename == '' or audio_file.filename == '':
            return jsonify({'error': 'Files must be selected'}), 400
        
        # Validate file types
        media_allowed = allowed_file(media_file.filename, 'image') or \
                       allowed_file(media_file.filename, 'video')
        audio_allowed = allowed_file(audio_file.filename, 'audio')
        
        if not media_allowed or not audio_allowed:
            return jsonify({'error': 'Invalid file types'}), 400
        
        # Save files
        media_filename = secure_filename(f"{job_id}_media_{media_file.filename}")
        audio_filename = secure_filename(f"{job_id}_audio_{audio_file.filename}")
        
        media_path = UPLOAD_FOLDER / media_filename
        audio_path = UPLOAD_FOLDER / audio_filename
        
        media_file.save(str(media_path))
        audio_file.save(str(audio_path))
        
        # Initialize job
        jobs[job_id] = {
            'id': job_id,
            'status': 'uploaded',
            'created_at': datetime.utcnow().isoformat(),
            'media_path': str(media_path),
            'audio_path': str(audio_path),
            'progress': 0,
            'output_path': None,
            'error': None
        }
        
        logger.info(f"Job {job_id} uploaded: {media_filename}, {audio_filename}")
        
        return jsonify({
            'job_id': job_id,
            'status': 'uploaded'
        }), 200
    
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate lip-synced video."""
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        
        if job_id not in jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = jobs[job_id]
        job['status'] = 'processing'
        
        options = {
            'model': data.get('model', 'auto'),
            'emotion': data.get('emotion', 'neutral'),
            'motion_intensity': float(data.get('motion_intensity', 0.7)),
            'accuracy_mode': data.get('accuracy_mode', 'balanced')
        }
        
        logger.info(f"Processing job {job_id} with options: {options}")
        
        # TODO: Call actual pipeline
        # from backend.pipeline import LipSyncPipeline
        # pipeline = LipSyncPipeline()
        # result = pipeline.process(job['media_path'], job['audio_path'], **options)
        
        # Simulate completion
        output_filename = f"{job_id}_output.mp4"
        output_path = OUTPUT_FOLDER / output_filename
        
        job['status'] = 'completed'
        job['output_path'] = str(output_path)
        job['progress'] = 100
        
        return jsonify({
            'job_id': job_id,
            'status': 'completed',
            'output_path': str(output_path)
        }), 200
    
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/job/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job status."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    return jsonify({
        'id': job['id'],
        'status': job['status'],
        'progress': job.get('progress', 0),
        'created_at': job['created_at'],
        'error': job.get('error')
    }), 200


@app.route('/api/download/<job_id>', methods=['GET'])
def download(job_id):
    """Download generated video."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    if job['status'] != 'completed' or not job['output_path']:
        return jsonify({'error': 'Video not ready'}), 400
    
    if not os.path.exists(job['output_path']):
        return jsonify({'error': 'Output file not found'}), 404
    
    return send_file(job['output_path'], as_attachment=True, download_name=f"lipsync_{job_id}.mp4")


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500


if __name__ == '__main__':
    Path('logs').mkdir(exist_ok=True)
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug, threaded=True)
