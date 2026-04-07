"""
Authentication Routes
Handles user authentication with Google OAuth and JWT tokens
"""

from flask import Blueprint, request, jsonify, redirect, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from models.user_model import User

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Global variables
user_model = None
JWT_SECRET = None
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Google OAuth configuration
GOOGLE_CLIENT_ID = None
GOOGLE_CLIENT_SECRET = None
GOOGLE_REDIRECT_URI = None

def init_auth_routes(db):
    """Initialize authentication routes with database"""
    global user_model, JWT_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
    
    user_model = User(db)
    JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    
    # Google OAuth credentials
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/auth/google/callback')
    
    print("\n" + "="*60)
    print("GOOGLE OAUTH CONFIGURATION DEBUG")
    print("="*60)
    print(f"GOOGLE_CLIENT_ID type: {type(GOOGLE_CLIENT_ID)}")
    print(f"GOOGLE_CLIENT_ID is None: {GOOGLE_CLIENT_ID is None}")
    print(f"GOOGLE_CLIENT_ID length: {len(GOOGLE_CLIENT_ID) if GOOGLE_CLIENT_ID else 0}")
    print(f"GOOGLE_CLIENT_ID value: {GOOGLE_CLIENT_ID}")
    print(f"GOOGLE_CLIENT_SECRET is None: {GOOGLE_CLIENT_SECRET is None}")
    print(f"GOOGLE_CLIENT_SECRET length: {len(GOOGLE_CLIENT_SECRET) if GOOGLE_CLIENT_SECRET else 0}")
    print(f"GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI}")
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("Warning: Google OAuth credentials not configured")
        print("   Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file")
    else:
        print("Google OAuth configured successfully")
    print("="*60 + "\n")


def create_jwt_token(user_id, email):
    """Create JWT token for user"""
    payload = {
        'user_id': str(user_id),
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require JWT token for routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = verify_jwt_token(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Add user info to request
            request.user_id = payload['user_id']
            request.user_email = payload['email']
            
        except Exception as e:
            return jsonify({'error': 'Token verification failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated


@auth_bp.route('/google/login')
def google_login():
    """Initiate Google OAuth flow"""
    print("\n" + "="*60)
    print("GOOGLE LOGIN REQUEST RECEIVED")
    print("="*60)
    print(f"GOOGLE_CLIENT_ID (in route): {GOOGLE_CLIENT_ID}")
    print(f"GOOGLE_CLIENT_SECRET (in route): {'SET' if GOOGLE_CLIENT_SECRET else 'NOT SET'}")
    print(f"GOOGLE_REDIRECT_URI (in route): {GOOGLE_REDIRECT_URI}")
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("ERROR: Client ID or Secret is missing!")
        return jsonify({
            'error': 'Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET'
        }), 500
    
    try:
        print("\nCreating OAuth Flow Configuration:")
        client_config = {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        }
        print(f"   Config client_id: {client_config['web']['client_id']}")
        print(f"   Config redirect_uris: {client_config['web']['redirect_uris']}")
        
        flow = Flow.from_client_config(
            client_config,
            scopes=[
                'openid',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
        )
        
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        print(f"   Flow redirect_uri set to: {flow.redirect_uri}")
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        print("\nGenerated Authorization URL:")
        print(f"   {authorization_url}")
        print(f"   State: {state}")
        
        # Parse the URL to show the client_id parameter
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(authorization_url)
        params = parse_qs(parsed.query)
        print("\nURL Parameters:")
        print(f"   client_id in URL: {params.get('client_id', ['NOT FOUND'])[0]}")
        print(f"   redirect_uri in URL: {params.get('redirect_uri', ['NOT FOUND'])[0]}")
        print(f"   response_type: {params.get('response_type', ['NOT FOUND'])[0]}")
        print(f"   scope: {params.get('scope', ['NOT FOUND'])[0]}")
        print("="*60 + "\n")
        
        # Store state in session
        session['oauth_state'] = state
        
        return redirect(authorization_url)
    
    except Exception as e:
        print("\nEXCEPTION in google_login:")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
        return redirect(f'http://localhost:8000/login.html?error=Failed+to+initiate+Google+login')


@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return redirect('http://localhost:8000/login.html?error=OAuth+not+configured')
    
    try:
        # Get authorization code
        code = request.args.get('code')
        if not code:
            return redirect('http://localhost:8000/login.html?error=Authorization+failed')
        
        # Exchange code for token
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=[
                'openid',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
        )
        
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        
        # Get user info
        credentials = flow.credentials
        request_adapter = google_requests.Request()
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request_adapter,
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        google_id = id_info.get('sub')
        email = id_info.get('email')
        name = id_info.get('name')
        picture = id_info.get('picture')
        
        # Check if user exists
        user = user_model.find_by_google_id(google_id)
        
        if not user:
            # Check if user exists with this email
            user = user_model.find_by_email(email)
            if user:
                # Update existing user with Google ID
                user_model.update_user(email, {
                    'google_id': google_id,
                    'profile_picture': picture,
                    'email_verified': True,
                    'registration_completed': True
                })
                user = user_model.find_by_email(email)
            else:
                # Create new user — Google has verified their email
                user = user_model.create_user(
                    email=email,
                    name=name,
                    google_id=google_id,
                    profile_picture=picture
                )
                # Google already verified the email, mark immediately
                if user:
                    user_model.update_user(email, {
                        'email_verified': True,
                        'registration_completed': True
                    })
                    user = user_model.find_by_email(email)
        else:
            # Update last login
            user_model.update_last_login(email=email)
        
        # Create JWT token
        token = create_jwt_token(user['_id'], email)
        
        # Redirect to frontend with token
        return redirect(f'https://secure-data-storage-and-integrity-v.vercel.app/login.html?token={token}')
    
    except Exception as e:
        print(f"Google callback error: {e}")
        return redirect(f'http://localhost:8000/login.html?error=Authentication+failed')


@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token():
    """Verify JWT token"""
    user = user_model.find_by_id(request.user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'valid': True,
        'user': user_model.serialize_user(user)
    })

