import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.config import Config
from backend.api import auth_bp, users_bp, api_keys_bp, pdf_template_bp, uploaded_files_bp, channels_bp, media_rationale_bp, upload_rationale_bp, premium_rationale_bp, saved_rationale_bp, activity_logs_bp, dashboard_bp, manual_v2_bp
from backend.utils.database import init_database

def create_app():
    # Serve static files from build directory in production
    static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'build')
    app = Flask(__name__, static_folder=static_folder, static_url_path='')
    app.config.from_object(Config)
    
    # Initialize database tables
    with app.app_context():
        init_database()
    
    # CORS configuration with environment-based security
    allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*')
    if allowed_origins != '*':
        allowed_origins = allowed_origins.split(',')
    
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    jwt = JWTManager(app)
    
    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({'error': 'Missing or invalid token'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(api_keys_bp)
    app.register_blueprint(pdf_template_bp)
    app.register_blueprint(uploaded_files_bp)
    app.register_blueprint(channels_bp)
    app.register_blueprint(media_rationale_bp)
    app.register_blueprint(upload_rationale_bp)
    app.register_blueprint(premium_rationale_bp)
    app.register_blueprint(manual_v2_bp)
    app.register_blueprint(saved_rationale_bp)
    app.register_blueprint(activity_logs_bp)
    app.register_blueprint(dashboard_bp)
    
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok', 'message': 'PHD Capital Rationale Studio API'}), 200
    
    # Serve React frontend (catch-all route for SPA)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        static_dir = app.static_folder or static_folder
        if path != "" and os.path.exists(os.path.join(static_dir, path)):
            return send_from_directory(static_dir, path)
        else:
            return send_from_directory(static_dir, 'index.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8000, debug=True)
