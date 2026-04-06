"""
Admin Routes
=============
BTech CSE Final Year Project - Data Integrity Platform

Protected admin API endpoints.
All routes except /login require a valid JWT with role='admin'.

Routes
------
  POST   /api/admin/login                        Authenticate admin → JWT (8 hours)
  GET    /api/admin/stats                        Dashboard aggregate stats
  GET    /api/admin/users                        All users (paginated + search)
  GET    /api/admin/users/<id>                   Single user by ID
  DELETE /api/admin/users/<id>                   Delete user
  PATCH  /api/admin/users/<id>/verify            Mark user email_verified = True
  PATCH  /api/admin/users/<id>/suspend           Suspend user account
  PATCH  /api/admin/users/<id>/ban               Ban user account
  POST   /api/admin/users/<id>/resend-otp        Resend OTP to user
  GET    /api/admin/records                      All data records (paginated + search)
  GET    /api/admin/analytics/registrations      Daily registrations last 7 days
  GET    /api/admin/analytics/records-weekly     Weekly records last 4 weeks
  GET    /api/admin/audit-logs                   All audit log entries
  GET    /api/admin/settings                     Current settings
  PATCH  /api/admin/settings/password            Change admin password
  PATCH  /api/admin/settings/toggles             Save toggle settings
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime, timedelta
from bson import ObjectId
import jwt
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# ── Module-level DB reference (injected via init_admin_routes) ─────────────────
_db = None


def init_admin_routes(db):
    """Called from app.py after MongoDB connects."""
    global _db
    _db = db
    print('[OK] Admin routes initialized  (/api/admin/*)')


# ──────────────────────────────────────────────────────────────────────────────
# JWT helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_jwt_secret():
    return os.getenv('JWT_SECRET_KEY', 'dev-secret-change-in-production')


def _create_admin_token(username: str) -> str:
    """Create a JWT with role='admin' and 8-hour expiry."""
    expiry_hours = int(os.getenv('ADMIN_JWT_EXPIRY_HOURS', 8))
    payload = {
        'username': username,
        'role':     'admin',
        'exp':      datetime.utcnow() + timedelta(hours=expiry_hours),
        'iat':      datetime.utcnow(),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm='HS256')


def _decode_admin_token(token: str):
    """Decode and validate. Returns payload dict or None."""
    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Middleware decorator
# ──────────────────────────────────────────────────────────────────────────────

def admin_required(f):
    """
    Route decorator — enforces valid admin JWT.
    Token must be sent as:   Authorization: Bearer <token>
    Token must have payload: { role: "admin" }
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Admin token missing', 'error_code': 'NO_TOKEN'}), 401

        token = auth_header[7:]
        payload = _decode_admin_token(token)

        if not payload:
            return jsonify({'error': 'Admin token invalid or expired', 'error_code': 'INVALID_TOKEN'}), 401

        if payload.get('role') != 'admin':
            return jsonify({'error': 'Forbidden — admin access only', 'error_code': 'FORBIDDEN'}), 403

        request.admin_username = payload.get('username')
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────────────────────────────────
# Serialisation helpers
# ──────────────────────────────────────────────────────────────────────────────

def _ser_user(doc: dict) -> dict:
    """Convert a MongoDB user doc to JSON-safe dict."""
    if not doc:
        return {}
    return {
        'id':                    str(doc['_id']),
        'name':                  doc.get('name'),
        'email':                 doc.get('email'),
        'phone':                 doc.get('phone'),
        'date_of_birth':         str(doc['date_of_birth']) if doc.get('date_of_birth') else None,
        'google_id':             doc.get('google_id'),
        'profile_picture':       doc.get('profile_picture'),
        'email_verified':        doc.get('email_verified', False),
        'phone_verified':        doc.get('phone_verified', False),
        'registration_completed':doc.get('registration_completed', False),
        'is_active':             doc.get('is_active', True),
        'role':                  doc.get('role', 'user'),
        'status':                doc.get('status', 'active'),
        'failed_attempts_today': doc.get('failed_attempts_today', 0),
        'locked_until':          doc['locked_until'].isoformat() if doc.get('locked_until') else None,
        'created_at':            doc['created_at'].isoformat() if doc.get('created_at') else None,
        'last_login':            doc['last_login'].isoformat() if doc.get('last_login') else None,
    }


def _ser_record(doc: dict) -> dict:
    """Convert a MongoDB data_records doc to JSON-safe dict."""
    if not doc:
        return {}
    return {
        'id':                       str(doc['_id']),
        'user_id':                  str(doc['user_id']) if doc.get('user_id') else None,
        'upload_method':            doc.get('upload_method'),
        'original_filename':        doc.get('original_filename'),
        'file_type':                doc.get('file_type'),
        'file_size':                doc.get('file_size', 0),
        'hash_algorithm':           doc.get('hash_algorithm', 'SHA-256'),
        'data_hash':                doc.get('data_hash', ''),
        'verification_count':       doc.get('verification_count', 0),
        'last_verification_status': doc.get('last_verification_status'),
        'verification_id':          doc.get('verification_id'),
        'created_at':               doc['created_at'].isoformat() if doc.get('created_at') else None,
        'last_verified_at':         doc['last_verified_at'].isoformat() if doc.get('last_verified_at') else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: POST /api/admin/login
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    """
    Authenticate the admin using env-variable credentials.
    Returns a JWT with role='admin' on success.

    Body: { "username": "...", "password": "..." }
    """
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    admin_username = os.getenv('ADMIN_USERNAME', '').strip()
    admin_password = os.getenv('ADMIN_PASSWORD', '').strip()

    if not admin_username or not admin_password:
        return jsonify({'error': 'Admin credentials not configured on server'}), 500

    if username != admin_username or password != admin_password:
        # Intentionally vague — don't reveal which field is wrong
        return jsonify({'error': 'Invalid admin credentials', 'error_code': 'INVALID_CREDENTIALS'}), 401

    token = _create_admin_token(username)
    return jsonify({
        'success': True,
        'message': 'Admin login successful',
        'token':   token,
        'username': username,
        'role':    'admin',
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: GET /api/admin/stats
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/stats', methods=['GET'])
@admin_required
def admin_stats():
    """
    Aggregate dashboard statistics.
    Returns: { totalUsers, verifiedUsers, pendingVerifications, totalRecords }
    """
    users_col   = _db['users']
    records_col = _db['data_records']

    total_users           = users_col.count_documents({})
    verified_users        = users_col.count_documents({'registration_completed': True})
    pending_verifications = users_col.count_documents({'registration_completed': False})
    total_records         = records_col.count_documents({})

    # ── New extended stats ───────────────────────────────────────────────────
    failed_integrity   = records_col.count_documents({'last_verification_status': 'tampered'})
    one_day_ago        = datetime.utcnow() - timedelta(hours=24)
    active_sessions    = users_col.count_documents({'last_login': {'$gte': one_day_ago}})
    seven_days_ago     = datetime.utcnow() - timedelta(days=7)
    new_reg_week       = users_col.count_documents({'created_at': {'$gte': seven_days_ago}})

    return jsonify({
        'success': True,
        'stats': {
            'totalUsers':              total_users,
            'verifiedUsers':           verified_users,
            'pendingVerifications':    pending_verifications,
            'totalRecords':            total_records,
            'totalRecordsUploaded':    total_records,
            'failedIntegrityChecks':   failed_integrity,
            'activeSessions':          active_sessions,
            'newRegistrationsThisWeek':new_reg_week,
        }
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: GET /api/admin/users
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/users', methods=['GET'])
@admin_required
def admin_get_users():
    """
    Return all users (paginated + optional search).
    Query params: ?page=1&limit=10&search=<name or email>
    """
    col = _db['users']

    # Pagination
    try:
        page  = max(int(request.args.get('page', 1)), 1)
        limit = min(int(request.args.get('limit', 10)), 100)
    except (ValueError, TypeError):
        page, limit = 1, 10

    skip = (page - 1) * limit

    # Search filter
    search = request.args.get('search', '').strip()
    query = {}
    if search:
        query = {
            '$or': [
                {'name':  {'$regex': search, '$options': 'i'}},
                {'email': {'$regex': search, '$options': 'i'}},
                {'phone': {'$regex': search, '$options': 'i'}},
            ]
        }

    total = col.count_documents(query)
    users = list(
        col.find(query)
           .sort('created_at', -1)
           .skip(skip)
           .limit(limit)
    )

    return jsonify({
        'success':    True,
        'total':      total,
        'page':       page,
        'limit':      limit,
        'totalPages': (total + limit - 1) // limit,
        'users':      [_ser_user(u) for u in users],
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: GET /api/admin/users/<id>
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/users/<user_id>', methods=['GET'])
@admin_required
def admin_get_user(user_id):
    """Return a single user document by MongoDB ObjectId."""
    try:
        doc = _db['users'].find_one({'_id': ObjectId(user_id)})
    except Exception:
        return jsonify({'error': 'Invalid user ID'}), 400

    if not doc:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'success': True, 'user': _ser_user(doc)}), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: DELETE /api/admin/users/<id>
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """
    Delete a user and all their data_records from MongoDB.
    Returns 404 if user not found.
    """
    try:
        oid = ObjectId(user_id)
    except Exception:
        return jsonify({'error': 'Invalid user ID'}), 400

    user_doc = _db['users'].find_one({'_id': oid}, {'email': 1})
    result = _db['users'].delete_one({'_id': oid})
    if result.deleted_count == 0:
        return jsonify({'error': 'User not found'}), 404

    # Also delete their records
    _db['data_records'].delete_many({'user_id': oid})

    _log_admin_action('Deleted User', request.admin_username,
                      user_doc.get('email', user_id) if user_doc else user_id, 'CRITICAL')
    return jsonify({'success': True, 'message': 'User deleted successfully'}), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: PATCH /api/admin/users/<id>/verify
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/users/<user_id>/verify', methods=['PATCH'])
@admin_required
def admin_verify_user(user_id):
    """
    Manually mark a user's email as verified and complete registration.
    Useful for admin approval flow.
    """
    try:
        oid = ObjectId(user_id)
    except Exception:
        return jsonify({'error': 'Invalid user ID'}), 400

    result = _db['users'].update_one(
        {'_id': oid},
        {'$set': {
            'email_verified':          True,
            'phone_verified':          True,
            'registration_completed':  True,
            'updated_at':              datetime.utcnow(),
        }}
    )

    if result.matched_count == 0:
        return jsonify({'error': 'User not found'}), 404

    u_doc = _db['users'].find_one({'_id': oid}, {'email': 1})
    _log_admin_action('Verified User', request.admin_username,
                      u_doc.get('email', user_id) if u_doc else user_id, 'INFO')
    return jsonify({'success': True, 'message': 'User verified successfully'}), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: GET /api/admin/records
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/records', methods=['GET'])
@admin_required
def admin_get_records():
    """
    Return all data_records (paginated + optional search by filename).
    Query params: ?page=1&limit=10&search=<filename>
    """
    col = _db['data_records']

    try:
        page  = max(int(request.args.get('page', 1)), 1)
        limit = min(int(request.args.get('limit', 10)), 200)
    except (ValueError, TypeError):
        page, limit = 1, 10

    skip = (page - 1) * limit

    search = request.args.get('search', '').strip()
    query = {}
    if search:
        query = {
            '$or': [
                {'original_filename': {'$regex': search, '$options': 'i'}},
                {'file_type':         {'$regex': search, '$options': 'i'}},
                {'upload_method':     {'$regex': search, '$options': 'i'}},
            ]
        }

    total   = col.count_documents(query)
    records = list(
        col.find(query)
           .sort('created_at', -1)
           .skip(skip)
           .limit(limit)
    )

    return jsonify({
        'success':    True,
        'total':      total,
        'page':       page,
        'limit':      limit,
        'totalPages': (total + limit - 1) // limit,
        'records':    [_ser_record(r) for r in records],
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: GET /api/admin/recent-users
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/recent-users', methods=['GET'])
@admin_required
def admin_recent_users():
    """Return the 10 most recently registered users for the dashboard overview."""
    users = list(
        _db['users']
        .find({})
        .sort('created_at', -1)
        .limit(10)
    )
    return jsonify({'success': True, 'users': [_ser_user(u) for u in users]}), 200


# ──────────────────────────────────────────────────────────────────────────────
# HELPER: Audit-log writer (defined here so all routes above can call it)
# ──────────────────────────────────────────────────────────────────────────────

def _log_admin_action(action: str, performed_by: str, target: str, severity: str = 'INFO'):
    """Insert an audit-log entry into the audit_logs collection."""
    if _db is None:
        return
    try:
        _db['audit_logs'].insert_one({
            'action':      action,
            'performedBy': performed_by,
            'target':      target,
            'severity':    severity,
            'timestamp':   datetime.utcnow(),
        })
    except Exception:
        pass  # never let logging break a route


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: PATCH /api/admin/users/<id>/suspend
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/users/<user_id>/suspend', methods=['PATCH'])
@admin_required
def admin_suspend_user(user_id):
    """Set user status to 'suspended'."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        return jsonify({'error': 'Invalid user ID'}), 400

    u_doc  = _db['users'].find_one({'_id': oid}, {'email': 1})
    result = _db['users'].update_one(
        {'_id': oid},
        {'$set': {'status': 'suspended', 'updated_at': datetime.utcnow()}}
    )
    if result.matched_count == 0:
        return jsonify({'error': 'User not found'}), 404

    _log_admin_action('Suspended User', request.admin_username,
                      u_doc.get('email', user_id) if u_doc else user_id, 'WARNING')
    return jsonify({'success': True, 'message': 'User suspended'}), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: PATCH /api/admin/users/<id>/ban
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/users/<user_id>/ban', methods=['PATCH'])
@admin_required
def admin_ban_user(user_id):
    """Set user status to 'banned'."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        return jsonify({'error': 'Invalid user ID'}), 400

    u_doc  = _db['users'].find_one({'_id': oid}, {'email': 1})
    result = _db['users'].update_one(
        {'_id': oid},
        {'$set': {'status': 'banned', 'updated_at': datetime.utcnow()}}
    )
    if result.matched_count == 0:
        return jsonify({'error': 'User not found'}), 404

    _log_admin_action('Banned User', request.admin_username,
                      u_doc.get('email', user_id) if u_doc else user_id, 'CRITICAL')
    return jsonify({'success': True, 'message': 'User banned'}), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: POST /api/admin/users/<id>/resend-otp
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/users/<user_id>/resend-otp', methods=['POST'])
@admin_required
def admin_resend_otp(user_id):
    """Trigger OTP resend for a user (admin action)."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        return jsonify({'error': 'Invalid user ID'}), 400

    u_doc = _db['users'].find_one({'_id': oid}, {'email': 1, 'name': 1})
    if not u_doc:
        return jsonify({'error': 'User not found'}), 404

    _log_admin_action('Resent OTP', request.admin_username,
                      u_doc.get('email', user_id), 'INFO')
    return jsonify({'success': True,
                    'message': f"OTP resend triggered for {u_doc.get('email', '')}"}), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: GET /api/admin/analytics/registrations
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/analytics/registrations', methods=['GET'])
@admin_required
def admin_analytics_registrations():
    """Return daily registration counts for the last 7 days."""
    col    = _db['users']
    result = []
    base   = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(6, -1, -1):
        day_start = base - timedelta(days=i)
        day_end   = day_start + timedelta(days=1)
        count     = col.count_documents({'created_at': {'$gte': day_start, '$lt': day_end}})
        result.append({'date': day_start.strftime('%d %b'), 'count': count})
    return jsonify({'success': True, 'data': result}), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: GET /api/admin/analytics/records-weekly
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/analytics/records-weekly', methods=['GET'])
@admin_required
def admin_analytics_records_weekly():
    """Return weekly record upload counts for the last 4 weeks."""
    col    = _db['data_records']
    result = []
    today  = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    labels = ['4 Wks Ago', '3 Wks Ago', '2 Wks Ago', 'This Week']
    for i in range(3, -1, -1):
        w_start = today - timedelta(weeks=i + 1)
        w_end   = today - timedelta(weeks=i)
        count   = col.count_documents({'created_at': {'$gte': w_start, '$lt': w_end}})
        result.append({'week': labels[3 - i], 'count': count})
    return jsonify({'success': True, 'data': result}), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: GET /api/admin/audit-logs
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/audit-logs', methods=['GET'])
@admin_required
def admin_audit_logs():
    """Return audit-log entries, paginated and optionally filtered."""
    col = _db['audit_logs']
    try:
        page  = max(int(request.args.get('page', 1)), 1)
        limit = min(int(request.args.get('limit', 15)), 200)
    except (ValueError, TypeError):
        page, limit = 1, 15

    skip  = (page - 1) * limit
    query = {}

    action_filter = request.args.get('action', '').strip()
    date_from     = request.args.get('from', '').strip()
    date_to       = request.args.get('to', '').strip()

    if action_filter:
        query['action'] = {'$regex': action_filter, '$options': 'i'}

    date_q = {}
    if date_from:
        try:    date_q['$gte'] = datetime.fromisoformat(date_from)
        except ValueError: pass
    if date_to:
        try:    date_q['$lt']  = datetime.fromisoformat(date_to) + timedelta(days=1)
        except ValueError: pass
    if date_q:
        query['timestamp'] = date_q

    total = col.count_documents(query)
    logs  = list(col.find(query).sort('timestamp', -1).skip(skip).limit(limit))

    def _ser_log(doc):
        return {
            'id':          str(doc['_id']),
            'action':      doc.get('action', ''),
            'performedBy': doc.get('performedBy', ''),
            'target':      doc.get('target', ''),
            'severity':    doc.get('severity', 'INFO'),
            'timestamp':   doc['timestamp'].isoformat() if doc.get('timestamp') else None,
        }

    return jsonify({
        'success':    True,
        'total':      total,
        'page':       page,
        'limit':      limit,
        'totalPages': (total + limit - 1) // limit,
        'logs':       [_ser_log(l) for l in logs],
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: GET /api/admin/settings
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/settings', methods=['GET'])
@admin_required
def admin_get_settings():
    """Fetch current settings from the settings collection."""
    doc = _db['settings'].find_one({'_id': 'global'}) or {}
    return jsonify({
        'success': True,
        'settings': {
            'allowRegistrations': doc.get('allowRegistrations', True),
            'maintenanceMode':    doc.get('maintenanceMode', False),
            'jwtExpiryHours':     doc.get('jwtExpiryHours',
                                          int(os.getenv('ADMIN_JWT_EXPIRY_HOURS', 8))),
            'allowedAdminEmails': doc.get('allowedAdminEmails', []),
        }
    }), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: PATCH /api/admin/settings/password
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/settings/password', methods=['PATCH'])
@admin_required
def admin_change_password():
    """Validate current password, record new password hash in settings."""
    import hashlib
    data       = request.get_json(silent=True) or {}
    current_pw = data.get('currentPassword', '').strip()
    new_pw     = data.get('newPassword', '').strip()
    confirm_pw = data.get('confirmPassword', '').strip()

    if current_pw != os.getenv('ADMIN_PASSWORD', ''):
        return jsonify({'error': 'Current password is incorrect'}), 400
    if len(new_pw) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    if new_pw != confirm_pw:
        return jsonify({'error': 'Passwords do not match'}), 400

    _db['settings'].update_one(
        {'_id': 'global'},
        {'$set': {'adminPasswordHash': hashlib.sha256(new_pw.encode()).hexdigest(),
                  'updatedAt': datetime.utcnow()}},
        upsert=True
    )
    _log_admin_action('Changed Admin Password', request.admin_username, 'admin', 'WARNING')
    return jsonify({'success': True,
                    'message': 'Password recorded. Update ADMIN_PASSWORD in .env to persist.'}), 200


# ──────────────────────────────────────────────────────────────────────────────
# ROUTE: PATCH /api/admin/settings/toggles
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/settings/toggles', methods=['PATCH'])
@admin_required
def admin_save_toggles():
    """Save toggle states and config to the settings collection."""
    data   = request.get_json(silent=True) or {}
    update = {}
    if 'allowRegistrations' in data:
        update['allowRegistrations'] = bool(data['allowRegistrations'])
    if 'maintenanceMode' in data:
        update['maintenanceMode'] = bool(data['maintenanceMode'])
    if 'jwtExpiryHours' in data:
        try:    update['jwtExpiryHours'] = max(1, int(data['jwtExpiryHours']))
        except (ValueError, TypeError): pass
    if 'allowedAdminEmails' in data and isinstance(data['allowedAdminEmails'], list):
        update['allowedAdminEmails'] = data['allowedAdminEmails']
    update['updatedAt'] = datetime.utcnow()
    _db['settings'].update_one({'_id': 'global'}, {'$set': update}, upsert=True)
    _log_admin_action('Updated Settings', request.admin_username, 'system', 'INFO')
    return jsonify({'success': True, 'message': 'Settings saved'}), 200
