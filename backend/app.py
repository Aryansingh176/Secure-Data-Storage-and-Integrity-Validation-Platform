"""
Flask Backend Server
BTech CSE Final Year Project - Data Integrity Platform

This is the main server file that:
- Connects to MongoDB
- Sets up API routes
- Handles CORS
- Runs the Flask application
"""

from flask import Flask, jsonify, session
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Import configurations and routes
from config.database import db_instance
from routes.data_routes import data_bp, init_routes
from routes.auth_routes import auth_bp, init_auth_routes
from routes.otp_auth_routes import otp_auth_bp, init_otp_auth
from routes.integrity_routes import integrity_bp, init_integrity_routes

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Disable strict slashes (allows /api/data and /api/data/ to work the same)
app.url_map.strict_slashes = False

# Configure secret key for sessions (required for OAuth)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure CORS (allow frontend to access API)
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:8000').split(',')
CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)

# Connect to MongoDB
db = db_instance.connect()

if db is None:
    print("[ERROR] Failed to connect to MongoDB. Please ensure MongoDB is running.")
    print("   Run: mongod")
    exit(1)

# Initialize routes with database
init_routes(db)
init_auth_routes(db)
init_otp_auth(db)
init_integrity_routes(db)

# Register blueprints
app.register_blueprint(data_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(otp_auth_bp)
app.register_blueprint(integrity_bp)

# Root endpoint
@app.route('/')
def index():
    """Root endpoint - API information"""
    return jsonify({
        'name': 'Data Integrity Platform API',
        'version': '1.0.0',
        'description': 'BTech CSE Final Year Project',
        'status': 'running',
        'endpoints': {
            # ── Data / Integrity ──────────────────────────────────────────────
            'POST /api/data/upload':          'Upload file → compute SHA-256 → store hash (requires auth)',
            'POST /api/data/text':            'Hash text input → store hash (requires auth)',
            'GET  /api/data/my-records':      'Get authenticated user\'s records',
            'GET  /api/data/my-statistics':   'Dashboard stats for authenticated user',
            'POST /api/data/<id>/verify':     'Verify file/text integrity against stored hash',
            'DELETE /api/data/<id>':          'Delete a record (owner only)',
            # ── Legacy (no auth) ──────────────────────────────────────────────
            'POST /api/data':                 'Create text record (legacy, no auth)',
            'GET  /api/data':                 'Get all records (legacy)',
            'GET  /api/data/statistics':      'Global stats (legacy)',
            # ── Integrity (clean routes) ──────────────────────────────────────
            'POST /api/upload':               'Upload file or text → SHA-256 → store (requires auth)',
            'POST /api/verify':               'Verify file/text against stored hash (requires auth)',
            'GET  /api/records':              'Get all records for authenticated user',
            'DELETE /api/records/<id>':       'Delete a record (owner only)',
            'GET  /api/dashboard/stats':      'Dashboard statistics for authenticated user',
            # ── Auth ──────────────────────────────────────────────────────────
            'GET  /api/auth/google/login':    'Google OAuth login',
            'POST /api/auth/login':           'Send OTP to email/phone',
            'POST /api/auth/verify-login':    'Verify OTP → receive JWT token',
            'GET  /api/auth/user/profile':    'Get user profile (requires auth)',
            'PUT  /api/auth/user/profile':    'Update profile (requires auth)',
        }
    })

# Health check endpoint
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected' if db is not None else 'disconnected'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

# Note: MongoDB connection remains open during app lifetime
# Connection pooling is handled by pymongo automatically
# No need to close after each request

# Run the server
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True') == 'True'
    
    print("\n" + "="*60)
    print("Data Integrity Platform - Backend Server")
    print("="*60)
    print(f"Server running on: http://localhost:{port}")
    print(f"MongoDB: {os.getenv('MONGO_DB_NAME', 'data_integrity_platform')}")
    print(f"Debug mode: {debug}")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
