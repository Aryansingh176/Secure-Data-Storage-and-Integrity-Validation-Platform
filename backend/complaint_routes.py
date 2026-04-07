"""
Complaint Routes
================
Complaint token system for user submissions and admin management.
"""

import os
import re
import jwt
import random
import string
from datetime import datetime, timedelta
from functools import wraps

from bson import ObjectId
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from models.data_model import DataModel
from services.auth_service import token_required

complaint_bp = Blueprint('complaints', __name__)

complaints_col = None
records_col = None

COMPLAINT_CATEGORIES = {
    'File Not Found',
    'Verification Failed',
    'Upload Issue',
    'Account Issue',
    'Data Mismatch',
    'Other',
}

COMPLAINT_PRIORITIES = {'Low', 'Medium', 'High'}
COMPLAINT_STATUSES = {'Open', 'In Progress', 'Resolved', 'Rejected'}

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads', 'complaints')


def init_complaint_routes(db):
    """Initialize complaint collections and indexes."""
    global complaints_col, records_col
    complaints_col = db['complaints']
    records_col = db['data_records']

    complaints_col.create_index('complaint_id', unique=True)
    complaints_col.create_index([('user_id', 1), ('created_at', -1)])
    complaints_col.create_index([('status', 1), ('created_at', -1)])
    complaints_col.create_index([('category', 1), ('priority', 1)])

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    print('[OK] Complaint routes initialized  (/api/complaints, /api/admin/complaints)')


def _jwt_secret():
    return os.getenv('JWT_SECRET_KEY', 'dev-secret-change-in-production')


def _decode_admin_token(token):
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def admin_required(f):
    """Require admin JWT with role=admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Admin token missing', 'error_code': 'NO_TOKEN'}), 401

        payload = _decode_admin_token(auth_header[7:])
        if not payload:
            return jsonify({'error': 'Admin token invalid or expired', 'error_code': 'INVALID_TOKEN'}), 401
        if payload.get('role') != 'admin':
            return jsonify({'error': 'Forbidden — admin access only', 'error_code': 'FORBIDDEN'}), 403

        request.admin_username = payload.get('username')
        return f(*args, **kwargs)

    return decorated


def _serialize_complaint(doc):
    return {
        'complaint_id': doc.get('complaint_id'),
        'user_id': str(doc.get('user_id')) if doc.get('user_id') else None,
        'user_email': doc.get('user_email'),
        'title': doc.get('title'),
        'description': doc.get('description'),
        'category': doc.get('category'),
        'priority': doc.get('priority'),
        'status': doc.get('status'),
        'stored_filename': doc.get('stored_filename'),
        'stored_file_found': bool(doc.get('stored_file_found', False)),
        'stored_file_format': doc.get('stored_file_format'),
        'verification_file': doc.get('verification_file'),
        'verification_file_format': doc.get('verification_file_format'),
        'format_match': bool(doc.get('format_match', False)),
        'admin_response': doc.get('admin_response', ''),
        'created_at': doc.get('created_at').isoformat() if doc.get('created_at') else None,
        'updated_at': doc.get('updated_at').isoformat() if doc.get('updated_at') else None,
    }


def _generate_complaint_id():
    for _ in range(10):
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        complaint_id = f'CPL-{suffix}'
        if complaints_col.count_documents({'complaint_id': complaint_id}, limit=1) == 0:
            return complaint_id
    return f"CPL-{datetime.utcnow().strftime('%H%M%S')}"


def _file_ext(filename):
    ext = DataModel.get_extension(filename or '')
    return ext.lower() if ext else None


def _record_format(record):
    ext = _file_ext(record.get('original_filename'))
    if ext in DataModel.ALLOWED_EXTENSIONS:
        return ext

    reverse_labels = {v: k for k, v in DataModel.EXTENSION_LABELS.items()}
    file_type = record.get('file_type')
    if file_type in reverse_labels:
        return reverse_labels[file_type]
    if file_type == 'Text':
        return 'txt'
    return None


def _save_verification_file(complaint_id, file_storage, file_bytes):
    original = secure_filename(file_storage.filename)
    saved_name = f"{complaint_id}_{original}"
    path = os.path.join(UPLOAD_DIR, saved_name)
    with open(path, 'wb') as f:
        f.write(file_bytes)
    return saved_name


@complaint_bp.route('/api/complaints/check-file', methods=['GET'])
@token_required
def check_stored_file():
    """Check if stored filename exists for authenticated user."""
    stored_filename = (request.args.get('stored_filename') or '').strip()
    if not stored_filename:
        return jsonify({'error': 'stored_filename is required'}), 400

    user_oid = ObjectId(request.user_id)
    record = records_col.find_one(
        {'user_id': user_oid, 'original_filename': stored_filename},
        {'original_filename': 1, 'file_type': 1}
    )

    if not record:
        return jsonify({'success': True, 'found': False, 'stored_file_format': None}), 200

    return jsonify({
        'success': True,
        'found': True,
        'stored_file_format': _record_format(record)
    }), 200


@complaint_bp.route('/api/complaints/submit', methods=['POST'])
@token_required
def submit_complaint():
    """Submit a new complaint token."""
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    category = (request.form.get('category') or '').strip()
    priority = (request.form.get('priority') or '').strip()
    stored_filename = (request.form.get('stored_filename') or '').strip()

    if not title:
        return jsonify({'error': 'Complaint title is required'}), 400
    if len(description) < 20:
        return jsonify({'error': 'Description must be at least 20 characters'}), 400
    if category not in COMPLAINT_CATEGORIES:
        return jsonify({'error': 'Invalid complaint category'}), 400
    if priority not in COMPLAINT_PRIORITIES:
        return jsonify({'error': 'Invalid complaint priority'}), 400
    if not stored_filename:
        return jsonify({'error': 'stored_filename is required'}), 400
    if 'verification_file' not in request.files:
        return jsonify({'error': 'verification_file is required'}), 400

    verification_file = request.files['verification_file']
    if not verification_file.filename:
        return jsonify({'error': 'No verification file selected'}), 400

    file_bytes = verification_file.read()
    valid, err = DataModel.validate_file(verification_file.filename, len(file_bytes))
    if not valid:
        return jsonify({'error': err}), 400

    verification_ext = _file_ext(verification_file.filename)

    user_oid = ObjectId(request.user_id)
    record = records_col.find_one(
        {'user_id': user_oid, 'original_filename': stored_filename},
        {'original_filename': 1, 'file_type': 1}
    )

    stored_found = record is not None
    stored_format = _record_format(record) if record else None

    if stored_found and stored_format and verification_ext != stored_format:
        return jsonify({
            'error': (
                f'Format mismatch: your stored file is {stored_format} '
                f'but you uploaded {verification_ext}. Please upload a {stored_format} file.'
            )
        }), 400

    complaint_id = _generate_complaint_id()
    saved_verification_file = _save_verification_file(complaint_id, verification_file, file_bytes)

    now = datetime.utcnow()
    complaint_doc = {
        'complaint_id': complaint_id,
        'user_id': user_oid,
        'user_email': request.user_email,
        'title': title,
        'description': description,
        'category': category,
        'priority': priority,
        'status': 'Open',
        'stored_filename': stored_filename,
        'stored_file_found': stored_found,
        'stored_file_format': stored_format,
        'verification_file': saved_verification_file,
        'verification_file_format': verification_ext,
        'format_match': bool(stored_found and stored_format == verification_ext),
        'admin_response': '',
        'created_at': now,
        'updated_at': now,
    }

    complaints_col.insert_one(complaint_doc)

    return jsonify({
        'success': True,
        'message': 'Complaint submitted successfully',
        'complaint_id': complaint_id,
    }), 201


@complaint_bp.route('/api/complaints/my-complaints', methods=['GET'])
@token_required
def my_complaints():
    user_oid = ObjectId(request.user_id)
    complaints = list(
        complaints_col.find({'user_id': user_oid}).sort('created_at', -1)
    )
    return jsonify({
        'success': True,
        'count': len(complaints),
        'complaints': [_serialize_complaint(c) for c in complaints],
    }), 200


@complaint_bp.route('/api/complaints/status/<complaint_id>', methods=['GET'])
@token_required
def complaint_status(complaint_id):
    user_oid = ObjectId(request.user_id)
    complaint = complaints_col.find_one({'complaint_id': complaint_id, 'user_id': user_oid})
    if not complaint:
        return jsonify({'error': 'Complaint not found'}), 404
    return jsonify({'success': True, 'complaint': _serialize_complaint(complaint)}), 200


@complaint_bp.route('/api/admin/complaints', methods=['GET'])
@admin_required
def admin_get_complaints():
    # Pagination
    try:
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(max(int(request.args.get('limit', 10)), 1), 100)
    except (TypeError, ValueError):
        page, limit = 1, 10
    skip = (page - 1) * limit

    # Filters
    status = (request.args.get('status') or '').strip()
    category = (request.args.get('category') or '').strip()
    priority = (request.args.get('priority') or '').strip()
    date_from = (request.args.get('from') or '').strip()
    date_to = (request.args.get('to') or '').strip()
    search = (request.args.get('search') or '').strip()

    query = {}
    if status:
        query['status'] = status
    if category:
        query['category'] = category
    if priority:
        query['priority'] = priority

    if date_from or date_to:
        date_filter = {}
        try:
            if date_from:
                date_filter['$gte'] = datetime.strptime(date_from, '%Y-%m-%d')
            if date_to:
                date_filter['$lte'] = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        query['created_at'] = date_filter

    if search:
        safe = re.escape(search)
        query['$or'] = [
            {'complaint_id': {'$regex': safe, '$options': 'i'}},
            {'user_email': {'$regex': safe, '$options': 'i'}},
        ]

    total = complaints_col.count_documents(query)
    complaints = list(
        complaints_col.find(query).sort('created_at', -1).skip(skip).limit(limit)
    )

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    summary = {
        'total': complaints_col.count_documents({}),
        'open': complaints_col.count_documents({'status': 'Open'}),
        'in_progress': complaints_col.count_documents({'status': 'In Progress'}),
        'resolved_today': complaints_col.count_documents({
            'status': 'Resolved',
            'updated_at': {'$gte': today_start}
        }),
    }

    return jsonify({
        'success': True,
        'page': page,
        'limit': limit,
        'total': total,
        'totalPages': (total + limit - 1) // limit,
        'summary': summary,
        'complaints': [_serialize_complaint(c) for c in complaints],
    }), 200


@complaint_bp.route('/api/admin/complaints/<complaint_id>', methods=['PUT'])
@admin_required
def admin_update_complaint(complaint_id):
    body = request.get_json(silent=True) or {}
    status = (body.get('status') or '').strip()
    admin_response = (body.get('admin_response') or '').strip()

    update = {'updated_at': datetime.utcnow()}
    if status:
        if status not in COMPLAINT_STATUSES:
            return jsonify({'error': 'Invalid complaint status'}), 400
        update['status'] = status

    if 'admin_response' in body:
        update['admin_response'] = admin_response

    result = complaints_col.update_one({'complaint_id': complaint_id}, {'$set': update})
    if result.matched_count == 0:
        return jsonify({'error': 'Complaint not found'}), 404

    complaint = complaints_col.find_one({'complaint_id': complaint_id})
    return jsonify({
        'success': True,
        'message': 'Complaint updated successfully',
        'complaint': _serialize_complaint(complaint),
    }), 200


@complaint_bp.route('/api/admin/complaints/file/<complaint_id>', methods=['GET'])
@admin_required
def admin_download_complaint_file(complaint_id):
    complaint = complaints_col.find_one({'complaint_id': complaint_id}, {'verification_file': 1})
    if not complaint or not complaint.get('verification_file'):
        return jsonify({'error': 'Verification file not found'}), 404

    return send_from_directory(UPLOAD_DIR, complaint['verification_file'], as_attachment=True)
