"""
OTP Authentication Routes
==========================
Implements complete multi-channel OTP authentication.

Route Summary:
  POST /api/auth/register         → Register user, send OTP to email + phone
  POST /api/auth/verify-email     → Verify email OTP
  POST /api/auth/verify-phone     → Verify phone OTP
  POST /api/auth/resend-otp       → Resend OTP (with rate limiting)
  POST /api/auth/login            → Send login OTP to email or phone
  POST /api/auth/verify-login     → Verify login OTP, get JWT token
  GET  /api/auth/status           → Get verification status (requires token)
  GET  /api/auth/user/profile     → Get user profile (requires token)
  PUT  /api/auth/user/profile     → Update profile (requires token)
  POST /api/auth/logout           → Logout (token deletion handled client-side)

Three-Layer Security:
  Layer 1: Per-OTP attempt limit (max 3 per OTP code)
  Layer 2: Per-channel send limit (max 3 per 15 minutes)
  Layer 3: Account lockout (max 5 failures per 24 hours)
"""

from flask import Blueprint, request, jsonify

# Models
from models.user_model import User
from models.rate_limit_model import RateLimitModel
from models.audit_log_model import AuditLogModel, AuditAction

# Services
from services.otp_service import OTPService
from services.email_service import send_email_otp
from services.sms_service import send_sms_otp, validate_phone_e164
from services.auth_service import (
    create_jwt_token, verify_jwt_token, token_required,
    validate_email, validate_otp_format,
    get_client_ip, get_user_agent
)

import os

# Blueprint prefix: all routes start with /api/auth
otp_auth_bp = Blueprint('otp_auth', __name__, url_prefix='/api/auth')

# ── Global model/service references (initialized via init_otp_auth) ──────────
user_model = None
rate_limit_model = None
audit_model = None
otp_service = None


def init_otp_auth(db):
    """
    Initialize all models and services with the database connection.
    Called from app.py after MongoDB connects.

    WHY dependency injection (passing db)?
    - Testable: can pass mock db in tests
    - Flexible: can switch databases without changing this file
    - Clear ownership: app.py controls the DB connection
    """
    global user_model, rate_limit_model, audit_model, otp_service

    user_model = User(db)
    rate_limit_model = RateLimitModel(db)
    audit_model = AuditLogModel(db)
    otp_service = OTPService(db)

    # Config values
    global RATE_LIMIT_MAX, RATE_LIMIT_WINDOW, MAX_DAILY_FAILURES, LOCK_HOURS
    RATE_LIMIT_MAX = int(os.getenv('RATE_LIMIT_MAX_REQUESTS', 3))
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW_MINUTES', 15))
    MAX_DAILY_FAILURES = int(os.getenv('MAX_DAILY_FAILURES', 5))
    LOCK_HOURS = int(os.getenv('ACCOUNT_LOCKOUT_HOURS', 24))

    print("[OK] OTP Authentication routes initialized")


# ──────────────────────────────────────────────────────────────────────────────
# HELPER: Send OTP via email + SMS
# ──────────────────────────────────────────────────────────────────────────────

def _send_otp_to_channel(user_id, user, identifier, channel, purpose, ip, ua):
    """
    Internal helper: create OTP and send to appropriate channel.
    Returns: (success: bool, error_response: dict|None, expiry_seconds: int)
    """
    # Layer 2: Per-channel rate limiting
    # Prevents OTP spam: max 3 sends per channel per 15 minutes
    rl_type = f'otp_send_{channel}'
    rl_result = rate_limit_model.check_and_increment(
        identifier=identifier,
        request_type=rl_type,
        limit=RATE_LIMIT_MAX,
        window_minutes=RATE_LIMIT_WINDOW
    )

    if not rl_result['allowed']:
        audit_model.log(
            identifier=identifier,
            action=AuditAction.RATE_LIMITED,
            channel=channel,
            success=False,
            ip_address=ip,
            user_agent=ua,
            user_id=str(user_id),
            details={
                'reason': 'OTP send rate limit exceeded',
                'reset_at': rl_result['reset_at'].isoformat()
            }
        )
        return False, {
            'error': f'Too many OTP requests. Try again in {rl_result.get("minutes_remaining", RATE_LIMIT_WINDOW)} minutes.',
            'error_code': 'RATE_LIMIT_EXCEEDED',
            'reset_at': rl_result['reset_at'].isoformat()
        }, 0

    # Generate and store OTP
    raw_otp, _ = otp_service.create_and_store_otp(
        user_id=user_id,
        identifier=identifier,
        channel=channel,
        purpose=purpose,
        ip_address=ip,
        user_agent=ua
    )

    # Send OTP via appropriate channel (wrapped to prevent unhandled exceptions)
    try:
        if channel == 'email':
            success, msg = send_email_otp(
                to_email=identifier,
                otp=raw_otp,
                user_name=user.get('name'),
                expiry_minutes=10,
                purpose=purpose
            )
        else:
            success, msg = send_sms_otp(
                to_phone=identifier,
                otp=raw_otp,
                expiry_minutes=5,
                purpose=purpose
            )
    except Exception as exc:
        print(f"[ERROR] OTP send failed ({channel}): {exc}")
        success, msg = False, str(exc)

    if not success:
        return False, {
            'error': f'Failed to send OTP via {channel}. {msg}',
            'error_code': 'OTP_SEND_FAILED'
        }, 0

    expiry_seconds = 600 if channel == 'email' else 300
    return True, None, expiry_seconds


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE 1: REGISTER
# POST /api/auth/register
# Body: { "email": "...", "phone": "+91...", "name": "..." }
# ──────────────────────────────────────────────────────────────────────────────

@otp_auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user and send OTP to both email and phone.

    FLOW:
    1. Validate inputs (email format, phone format)
    2. Check if email/phone already registered
    3. Create user (unverified)
    4. Send OTP to email (10 min expiry)
    5. Send OTP to phone (5 min expiry)
    6. Return user_id for verification step

    After registration, user is redirected to OTP verification page.
    They must verify BOTH channels to complete registration.
    """
    data = request.get_json()
    ip = get_client_ip()
    ua = get_user_agent()

    # ── Input Validation ──────────────────────────────────────────────────────
    if not data:
        return jsonify({'error': 'Request body is required', 'error_code': 'NO_DATA'}), 400

    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()

    errors = {}
    if not email:
        errors['email'] = 'Email is required'
    elif not validate_email(email):
        errors['email'] = 'Invalid email format'

    if not phone:
        errors['phone'] = 'Phone number is required'
    else:
        phone_valid, normalized_phone = validate_phone_e164(phone)
        if not phone_valid:
            errors['phone'] = 'Invalid phone. Use format: +91XXXXXXXXXX'
        else:
            phone = normalized_phone

    if not name:
        errors['name'] = 'Name is required'

    if errors:
        return jsonify({'error': 'Validation failed', 'fields': errors}), 400

    # ── Check Existing Users ──────────────────────────────────────────────────
    if user_model.find_by_email(email):
        return jsonify({
            'error': 'Email already registered. Please login instead.',
            'error_code': 'EMAIL_EXISTS'
        }), 409

    if user_model.find_by_phone(phone):
        return jsonify({
            'error': 'Phone number already registered. Please login instead.',
            'error_code': 'PHONE_EXISTS'
        }), 409

    # ── Create User ───────────────────────────────────────────────────────────
    user = user_model.create_user(email=email, phone=phone, name=name)
    if not user:
        return jsonify({'error': 'Failed to create account', 'error_code': 'DB_ERROR'}), 500

    user_id = user['_id']

    # Log registration event
    audit_model.log(
        identifier=email,
        action=AuditAction.REGISTRATION,
        channel='system',
        success=True,
        ip_address=ip,
        user_agent=ua,
        user_id=str(user_id),
        details={'name': name, 'phone': phone}
    )

    # ── Send OTPs ─────────────────────────────────────────────────────────────
    results = {}

    # Send email OTP
    email_ok, email_err, email_expiry = _send_otp_to_channel(
        user_id, user, email, 'email', 'registration', ip, ua
    )
    results['email'] = {
        'sent': email_ok,
        'expiry_seconds': email_expiry if email_ok else 0
    }

    # Send phone OTP
    phone_ok, phone_err, phone_expiry = _send_otp_to_channel(
        user_id, user, phone, 'phone', 'registration', ip, ua
    )
    results['phone'] = {
        'sent': phone_ok,
        'expiry_seconds': phone_expiry if phone_ok else 0
    }

    return jsonify({
        'message': 'Registration successful! Check your email and phone for OTPs.',
        'user_id': str(user_id),
        'email': email,
        'phone': phone,
        'otp_sent': results
    }), 201


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE 2: VERIFY EMAIL OTP
# POST /api/auth/verify-email
# Body: { "email": "...", "otp": "123456" }
# ──────────────────────────────────────────────────────────────────────────────

@otp_auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """
    Verify the email OTP.
    Marks email_verified=True on the user document.
    auto-completes registration if phone is also verified.
    """
    data = request.get_json()
    ip = get_client_ip()
    ua = get_user_agent()

    # Accept both 'email' and 'identifier' (profile page sends 'identifier')
    email = (data.get('email') or data.get('identifier') or '').strip().lower()
    otp = data.get('otp', '').strip()

    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400

    if not validate_otp_format(otp):
        return jsonify({'error': 'OTP must be exactly 6 digits', 'error_code': 'INVALID_FORMAT'}), 400

    # Find user
    user = user_model.find_by_email(email)
    if not user:
        return jsonify({'error': 'No account found with this email', 'error_code': 'USER_NOT_FOUND'}), 404

    # Check already verified
    if user.get('email_verified'):
        return jsonify({'message': 'Email already verified', 'error_code': 'ALREADY_VERIFIED'}), 200

    user_id = str(user['_id'])

    # Layer 3: Check account lockout
    locked, locked_until = user_model.is_locked(user)
    if locked:
        return jsonify({
            'error': f'Account locked until {locked_until.strftime("%Y-%m-%d %H:%M")} UTC due to too many failed attempts.',
            'error_code': 'ACCOUNT_LOCKED',
            'locked_until': locked_until.isoformat()
        }), 423

    # Verify OTP (Layer 1 handled inside OTPService)
    result = otp_service.verify_otp(
        identifier=email,
        entered_otp=otp,
        channel='email',
        purpose='registration',
        user_id=user_id,
        ip_address=ip,
        user_agent=ua
    )

    if not result['success']:
        # Layer 3: Track failure and lock if threshold reached
        total_failures = user_model.increment_failed_attempts(user_id)
        if total_failures >= MAX_DAILY_FAILURES:
            locked_until = user_model.lock_account(user_id, hours=LOCK_HOURS)
            audit_model.log(
                identifier=email,
                action=AuditAction.ACCOUNT_LOCKED,
                channel='email',
                success=False,
                ip_address=ip,
                user_agent=ua,
                user_id=user_id,
                details={'failed_attempts': total_failures, 'locked_until': locked_until.isoformat()}
            )
            return jsonify({
                'error': f'Account locked for {LOCK_HOURS} hours due to too many failed attempts.',
                'error_code': 'ACCOUNT_LOCKED',
                'locked_until': locked_until.isoformat()
            }), 423

        return jsonify(result), 400

    # ── OTP Correct ───────────────────────────────────────────────────────────
    user_model.mark_email_verified(user_id)
    user_model.reset_failed_attempts(user_id)

    # Fetch updated user to check registration_completed
    updated_user = user_model.find_by_id(user_id)
    registration_done = updated_user.get('registration_completed', False)

    audit_model.log(
        identifier=email,
        action=AuditAction.EMAIL_VERIFIED,
        channel='email',
        success=True,
        ip_address=ip,
        user_agent=ua,
        user_id=user_id
    )

    response = {
        'success': True,
        'message': 'Email verified successfully!',
        'email_verified': True,
        'phone_verified': updated_user.get('phone_verified', False),
        'registration_completed': registration_done
    }

    # If both verified, include JWT token so user can proceed directly
    if registration_done:
        token = create_jwt_token(user_id, email)
        user_model.update_last_login(user_id=user_id)
        response['token'] = token
        response['user'] = user_model.serialize_user(updated_user)
        response['message'] = 'Registration complete! Both channels verified.'

    return jsonify(response), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE 3: VERIFY PHONE OTP
# POST /api/auth/verify-phone
# Body: { "phone": "+91...", "otp": "123456" }
# ──────────────────────────────────────────────────────────────────────────────

@otp_auth_bp.route('/verify-phone', methods=['POST'])
def verify_phone():
    """
    Verify the phone OTP.
    Mirrors verify_email but for the phone channel.
    """
    data = request.get_json()
    ip = get_client_ip()
    ua = get_user_agent()

    # Accept both 'phone' and 'identifier' (profile page sends 'identifier')
    phone = (data.get('phone') or data.get('identifier') or '').strip()
    otp = data.get('otp', '').strip()

    if not phone or not otp:
        return jsonify({'error': 'Phone and OTP are required'}), 400

    # Normalize phone
    phone_valid, phone = validate_phone_e164(phone)
    if not phone_valid:
        return jsonify({'error': 'Invalid phone format', 'error_code': 'INVALID_PHONE'}), 400

    if not validate_otp_format(otp):
        return jsonify({'error': 'OTP must be exactly 6 digits', 'error_code': 'INVALID_FORMAT'}), 400

    user = user_model.find_by_phone(phone)
    if not user:
        return jsonify({'error': 'No account found with this phone', 'error_code': 'USER_NOT_FOUND'}), 404

    if user.get('phone_verified'):
        return jsonify({'message': 'Phone already verified', 'error_code': 'ALREADY_VERIFIED'}), 200

    user_id = str(user['_id'])
    email = user.get('email', phone)

    locked, locked_until = user_model.is_locked(user)
    if locked:
        return jsonify({
            'error': f'Account locked until {locked_until.strftime("%Y-%m-%d %H:%M")} UTC.',
            'error_code': 'ACCOUNT_LOCKED',
            'locked_until': locked_until.isoformat()
        }), 423

    result = otp_service.verify_otp(
        identifier=phone,
        entered_otp=otp,
        channel='phone',
        purpose='registration',
        user_id=user_id,
        ip_address=ip,
        user_agent=ua
    )

    if not result['success']:
        total_failures = user_model.increment_failed_attempts(user_id)
        if total_failures >= MAX_DAILY_FAILURES:
            locked_until = user_model.lock_account(user_id, hours=LOCK_HOURS)
            return jsonify({
                'error': f'Account locked for {LOCK_HOURS} hours.',
                'error_code': 'ACCOUNT_LOCKED',
                'locked_until': locked_until.isoformat()
            }), 423
        return jsonify(result), 400

    user_model.mark_phone_verified(user_id)
    user_model.reset_failed_attempts(user_id)

    updated_user = user_model.find_by_id(user_id)
    registration_done = updated_user.get('registration_completed', False)

    audit_model.log(
        identifier=phone,
        action=AuditAction.PHONE_VERIFIED,
        channel='phone',
        success=True,
        ip_address=ip,
        user_agent=ua,
        user_id=user_id
    )

    response = {
        'success': True,
        'message': 'Phone verified successfully!',
        'email_verified': updated_user.get('email_verified', False),
        'phone_verified': True,
        'registration_completed': registration_done
    }

    if registration_done:
        token = create_jwt_token(user_id, email)
        user_model.update_last_login(user_id=user_id)
        response['token'] = token
        response['user'] = user_model.serialize_user(updated_user)
        response['message'] = 'Registration complete! Both channels verified.'

    return jsonify(response), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE 4: RESEND OTP
# POST /api/auth/resend-otp
# Body: { "identifier": "email or phone", "channel": "email|phone", "purpose": "registration|login" }
# ──────────────────────────────────────────────────────────────────────────────

@otp_auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """
    Resend OTP to email or phone.

    Rate limited: max 3 sends per channel per 15 minutes.
    The rate limiter is checked inside _send_otp_to_channel.
    """
    data = request.get_json()
    ip = get_client_ip()
    ua = get_user_agent()

    identifier = data.get('identifier', '').strip()
    channel = data.get('channel', '').strip().lower()
    purpose = data.get('purpose', 'registration').strip().lower()

    if not identifier or channel not in ('email', 'phone'):
        return jsonify({'error': 'identifier and channel (email/phone) are required'}), 400

    # Find user by appropriate field
    if channel == 'email':
        user = user_model.find_by_email(identifier.lower())
    else:
        _, normalized = validate_phone_e164(identifier)
        if normalized:
            identifier = normalized
        user = user_model.find_by_phone(identifier)

    # Fallback: if not found by identifier, try resolving via Bearer token
    # This covers Google OAuth users who haven't stored a phone yet
    if not user:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token_str = auth_header[7:]
            try:
                payload = verify_jwt_token(token_str)
                if payload and payload.get('user_id'):
                    user = user_model.find_by_id(payload['user_id'])
                    if user and channel == 'phone':
                        # Store the phone on the user document so future lookups work
                        user_model.update_user(user.get('email', ''), {'phone': identifier})
                        user = user_model.find_by_id(payload['user_id'])
            except Exception:
                pass

    if not user:
        return jsonify({'error': 'No account found', 'error_code': 'USER_NOT_FOUND'}), 404

    user_id = user['_id']

    ok, err, expiry = _send_otp_to_channel(
        user_id, user, identifier, channel, purpose, ip, ua
    )

    if not ok:
        return jsonify(err), 429  # 429 Too Many Requests

    audit_model.log(
        identifier=identifier,
        action=AuditAction.RESEND_OTP,
        channel=channel,
        success=True,
        ip_address=ip,
        user_agent=ua,
        user_id=str(user_id),
        details={'purpose': purpose}
    )

    return jsonify({
        'success': True,
        'message': f'New OTP sent to your {channel}.',
        'expiry_seconds': expiry
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE 5: LOGIN — Send OTP
# POST /api/auth/login
# Body: { "identifier": "email or phone", "channel": "email|phone" }
# ──────────────────────────────────────────────────────────────────────────────

@otp_auth_bp.route('/login', methods=['POST'])
def login():
    """
    Initiate login by sending OTP to the user's chosen channel.

    FLOW:
    1. User provides email or phone + preferred channel
    2. We verify the account exists and is fully registered
    3. Send OTP to chosen channel
    4. User completes login via /verify-login

    WHY require registration_completed?
    Prevents users with partial registration from logging in.
    Ensures identity is fully verified before granting access.
    """
    data = request.get_json()
    ip = get_client_ip()
    ua = get_user_agent()

    identifier = data.get('identifier', '').strip()
    channel = data.get('channel', 'email').strip().lower()

    if not identifier:
        return jsonify({'error': 'Email or phone is required'}), 400

    if channel not in ('email', 'phone'):
        channel = 'email'  # Default to email

    # Find user
    user = user_model.find_by_identifier(identifier)
    if not user:
        # Security: Don't reveal if identifier exists or not
        return jsonify({
            'error': 'No account found. Please register first.',
            'error_code': 'USER_NOT_FOUND'
        }), 404

    # Check registration completed
    if not user.get('registration_completed'):
        return jsonify({
            'error': 'Please complete email and phone verification before logging in.',
            'error_code': 'REGISTRATION_INCOMPLETE',
            'email_verified': user.get('email_verified', False),
            'phone_verified': user.get('phone_verified', False)
        }), 403

    # Check account locked
    locked, locked_until = user_model.is_locked(user)
    if locked:
        return jsonify({
            'error': f'Account locked until {locked_until.strftime("%Y-%m-%d %H:%M")} UTC.',
            'error_code': 'ACCOUNT_LOCKED',
            'locked_until': locked_until.isoformat()
        }), 423

    # Determine the actual identifier for the chosen channel
    otp_identifier = user['email'] if channel == 'email' else user['phone']

    ok, err, expiry = _send_otp_to_channel(
        user['_id'], user, otp_identifier, channel, 'login', ip, ua
    )

    if not ok:
        return jsonify(err), 429

    return jsonify({
        'success': True,
        'message': f'OTP sent to your {channel}.',
        'channel': channel,
        'expiry_seconds': expiry,
        'identifier': otp_identifier     # echoed back for client-side use
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE 6: VERIFY LOGIN OTP — Get JWT Token
# POST /api/auth/verify-login
# Body: { "identifier": "email or phone", "otp": "123456", "channel": "email|phone" }
# ──────────────────────────────────────────────────────────────────────────────

@otp_auth_bp.route('/verify-login', methods=['POST'])
def verify_login():
    """
    Verify login OTP and return JWT token for authenticated session.

    On success:
    - Returns JWT token (24h expiry)
    - Client stores token in localStorage
    - All subsequent requests include token in Authorization header
    """
    data = request.get_json()
    ip = get_client_ip()
    ua = get_user_agent()

    identifier = data.get('identifier', '').strip()
    otp = data.get('otp', '').strip()
    channel = data.get('channel', 'email').strip().lower()

    if not identifier or not otp:
        return jsonify({'error': 'identifier and OTP are required'}), 400

    if not validate_otp_format(otp):
        return jsonify({'error': 'OTP must be exactly 6 digits', 'error_code': 'INVALID_FORMAT'}), 400

    # Find user
    user = user_model.find_by_identifier(identifier)
    if not user:
        return jsonify({'error': 'No account found', 'error_code': 'USER_NOT_FOUND'}), 404

    user_id = str(user['_id'])

    # Check lock
    locked, locked_until = user_model.is_locked(user)
    if locked:
        return jsonify({
            'error': f'Account locked until {locked_until.strftime("%Y-%m-%d %H:%M")} UTC.',
            'error_code': 'ACCOUNT_LOCKED'
        }), 423

    # Normalize identifier (use what's stored)
    otp_identifier = user['email'] if channel == 'email' else user['phone']

    # Verify OTP
    result = otp_service.verify_otp(
        identifier=otp_identifier,
        entered_otp=otp,
        channel=channel,
        purpose='login',
        user_id=user_id,
        ip_address=ip,
        user_agent=ua
    )

    if not result['success']:
        total_failures = user_model.increment_failed_attempts(user_id)
        if total_failures >= MAX_DAILY_FAILURES:
            locked_until = user_model.lock_account(user_id, hours=LOCK_HOURS)
            return jsonify({
                'error': f'Account locked for {LOCK_HOURS} hours.',
                'error_code': 'ACCOUNT_LOCKED',
                'locked_until': locked_until.isoformat()
            }), 423
        return jsonify(result), 400

    # ── Login Success ─────────────────────────────────────────────────────────
    user_model.update_last_login(user_id=user_id)
    user_model.reset_failed_attempts(user_id)

    token = create_jwt_token(user_id, user.get('email', identifier))

    audit_model.log(
        identifier=identifier,
        action=AuditAction.LOGIN_SUCCESS,
        channel=channel,
        success=True,
        ip_address=ip,
        user_agent=ua,
        user_id=user_id
    )

    return jsonify({
        'success': True,
        'message': 'Login successful!',
        'token': token,
        'user': user_model.serialize_user(user)
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE 7: STATUS CHECK
# GET /api/auth/status
# Headers: Authorization: Bearer <token>
# ──────────────────────────────────────────────────────────────────────────────

@otp_auth_bp.route('/status', methods=['GET'])
@token_required
def auth_status():
    """Get verification status for authenticated user"""
    user = user_model.find_by_id(request.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'user_id': str(user['_id']),
        'email': user.get('email'),
        'phone': user.get('phone'),
        'email_verified': user.get('email_verified', False),
        'phone_verified': user.get('phone_verified', False),
        'registration_completed': user.get('registration_completed', False)
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE 8 & 9: USER PROFILE
# GET  /api/auth/user/profile — Get profile
# PUT  /api/auth/user/profile — Update profile
# ──────────────────────────────────────────────────────────────────────────────

@otp_auth_bp.route('/user/profile', methods=['GET'])
@token_required
def get_profile():
    """Get authenticated user's profile"""
    user = user_model.find_by_id(request.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user_model.serialize_user(user)}), 200


@otp_auth_bp.route('/user/profile', methods=['PUT'])
@token_required
def update_profile():
    """Update authenticated user's profile (name, date_of_birth only)"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    success = user_model.update_profile(request.user_id, data)
    if success:
        user = user_model.find_by_id(request.user_id)
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user_model.serialize_user(user)
        }), 200
    return jsonify({'error': 'Failed to update profile'}), 500


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE 10: VERIFY TOKEN
# GET /api/auth/verify
# ──────────────────────────────────────────────────────────────────────────────

@otp_auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token_route():
    """Verify if current JWT token is valid"""
    user = user_model.find_by_id(request.user_id)
    return jsonify({
        'valid': True,
        'user': user_model.serialize_user(user)
    }), 200


@otp_auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    Logout — JWT is stateless so we can't invalidate server-side.
    Client must delete the token from localStorage.
    In production, use a token blacklist (Redis) for true invalidation.
    """
    return jsonify({'message': 'Logged out. Please delete your token.'}), 200
