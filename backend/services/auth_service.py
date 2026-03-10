"""
Auth Service
============
JWT token management and shared authentication utilities.

WHY JWT (JSON Web Tokens)?
- Stateless: Server doesn't store sessions — scales horizontally
- Self-contained: Token carries user info + expiry — one DB lookup saved
- Secure: Signed with server secret — tamper-evident
- Standard: RFC 7519 — widely supported by all languages/frameworks

JWT Structure (3 parts, base64-encoded, dot-separated):
  HEADER.PAYLOAD.SIGNATURE
  - Header: algorithm (HS256)
  - Payload: user_id, email, exp (expiry), iat (issued at)
  - Signature: HMAC-SHA256 of header+payload with SECRET_KEY

SECURITY NOTE:
JWT payload is base64-encoded, NOT encrypted.
Don't store sensitive data (passwords, OTPs) in JWT payload.
Store only the minimum needed: user_id + email.
"""

import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify


# ──────────────────────────────────────────────
# JWT Configuration
# ──────────────────────────────────────────────

JWT_ALGORITHM = 'HS256'         # HMAC-SHA256 — fast, symmetric, standard
JWT_EXPIRATION_HOURS = 24       # Token valid for 24 hours


def get_jwt_secret():
    """
    Get JWT secret from environment.
    WHY not hardcode: If code is leaked (GitHub), secret stays safe.
    In production, use a 256-bit random string.
    """
    return os.getenv('JWT_SECRET_KEY', 'dev-secret-change-in-production')


# ──────────────────────────────────────────────
# Token Creation & Verification
# ──────────────────────────────────────────────

def create_jwt_token(user_id, email):
    """
    Create a signed JWT token for a user.

    Payload contains:
    - user_id: MongoDB ObjectId as string
    - email: user's email
    - exp: expiry timestamp (UNIX epoch) — jwt library validates this automatically
    - iat: issued-at timestamp — useful for token age checks
    """
    payload = {
        'user_id': str(user_id),
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_jwt_token(token):
    """
    Verify and decode a JWT token.

    Returns decoded payload dict if valid.
    Returns None if expired or tampered.

    jwt.decode() handles:
    - Signature verification (tamper detection)
    - Expiry check (exp claim)
    - Algorithm validation
    """
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        # Token is valid but has expired
        return None
    except jwt.InvalidTokenError:
        # Token was tampered with or malformed
        return None


# ──────────────────────────────────────────────
# Route Decorator
# ──────────────────────────────────────────────

def token_required(f):
    """
    Decorator to protect routes that require authentication.

    Usage:
        @app.route('/protected')
        @token_required
        def protected_route():
            # request.user_id and request.user_email are available here
            pass

    Token must be sent in Authorization header:
        Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...

    WHY decorator pattern?
    - DRY: Don't repeat auth logic in every route
    - Consistent: Same auth behavior across all protected routes
    - Separates concerns: Routes focus on business logic
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                'error': 'Authorization header missing',
                'error_code': 'NO_TOKEN'
            }), 401

        try:
            # Strip "Bearer " prefix
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
            else:
                token = auth_header

            payload = verify_jwt_token(token)
            if not payload:
                return jsonify({
                    'error': 'Token is invalid or expired. Please login again.',
                    'error_code': 'INVALID_TOKEN'
                }), 401

            # Attach user info to request for use in route handler
            request.user_id = payload['user_id']
            request.user_email = payload['email']

        except Exception as e:
            return jsonify({
                'error': 'Token verification failed',
                'error_code': 'TOKEN_ERROR'
            }), 401

        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────
# Input Validation Utilities
# ──────────────────────────────────────────────

def validate_email(email):
    """Basic email format validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_otp_format(otp):
    """OTP must be exactly 6 digits"""
    return otp and len(otp) == 6 and otp.isdigit()


def get_client_ip():
    """
    Get the real client IP, handling proxies.
    X-Forwarded-For: used by nginx/load balancers to pass real IP
    """
    x_forwarded = request.headers.get('X-Forwarded-For')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.remote_addr


def get_user_agent():
    """Get browser/client user-agent string"""
    return request.headers.get('User-Agent', 'Unknown')
