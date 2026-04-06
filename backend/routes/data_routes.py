"""
Data Routes - File Upload & Integrity Verification
====================================================
BTech CSE Final Year Project - Data Integrity Platform

New authenticated routes:
  POST   /api/data/upload          Upload file -> SHA-256 -> store metadata
  POST   /api/data/text            Hash raw text -> store metadata
  GET    /api/data/my-records      Current user's records
  GET    /api/data/my-statistics   Current user's dashboard stats
  POST   /api/data/<id>/verify     Verify file or text against stored hash
  DELETE /api/data/<id>            Delete record (owner only)

Legacy routes (kept for backward compatibility):
  GET    /api/data/                Get all records (no auth)
  POST   /api/data/                Create text record (no auth)
  GET    /api/data/statistics      Global stats
  DELETE /api/data/clear           Clear all records
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os

from models.data_model import DataModel
from models.audit_log_model import AuditLogModel, AuditAction
from services.auth_service import token_required, get_client_ip, get_user_agent

# Blueprint: all routes start with /api/data
data_bp = Blueprint('data', __name__, url_prefix='/api/data')

# Module-level instances (injected via init_routes)
data_model = None
audit_model = None


def init_routes(db):
    """Called from app.py after MongoDB connects."""
    global data_model, audit_model
    data_model = DataModel(db)
    audit_model = AuditLogModel(db)
    print('[OK] Data routes initialized')


# == Internal helper ===========================================================

def _log(user_id, action, record_id=None, success=True, details=None):
    """Write an audit log entry for a data operation."""
    if audit_model:
        audit_model.log_data_action(
            user_id=user_id,
            action=action,
            record_id=record_id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            success=success,
            details=details or {},
        )


def _public_verification_link(verification_id: str) -> str:
    """Create absolute public verification URL: /verify/<verification_id>."""
    base = os.getenv('PUBLIC_VERIFY_BASE_URL', 'http://localhost:5000').rstrip('/')
    return f'{base}/verify/{verification_id}'


# == FILE UPLOAD ===============================================================

@data_bp.route('/upload', methods=['POST'])
@token_required
def upload_file():
    """
    Upload a file -> compute SHA-256 -> store hash + metadata.

    POST /api/data/upload
    Content-Type: multipart/form-data
    Authorization: Bearer <token>
    Form field: file

    The file content is NEVER stored on disk or in the database.
    Only the SHA-256 fingerprint and metadata are persisted.

    Returns 201 with the created record (including hash).
    """
    user_id = request.user_id

    if 'file' not in request.files:
        return jsonify({'error': 'No file part. Use multipart/form-data with field name "file"'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    file_bytes = file.read()

    valid, error_msg = DataModel.validate_file(filename, len(file_bytes))
    if not valid:
        return jsonify({'error': error_msg}), 400

    record = data_model.create_file_record(user_id, filename, file_bytes)
    if not record:
        return jsonify({'error': 'Failed to store record'}), 500

    _log(user_id, AuditAction.UPLOAD_RECORD, record_id=record['_id'])

    return jsonify({
        'success': True,
        'message': 'File fingerprint stored. SHA-256: ' + record['data_hash'],
        'verification_id': record.get('verification_id'),
        'verification_link': _public_verification_link(record.get('verification_id', '')),
        'record':  record,
    }), 201


# == TEXT HASHING ==============================================================

@data_bp.route('/text', methods=['POST'])
@token_required
def hash_text():
    """
    Hash raw text input and store the fingerprint.

    POST /api/data/text
    Content-Type: application/json
    Authorization: Bearer <token>
    Body: { "text": "...", "label": "optional label" }

    The text is NOT stored. Only its SHA-256 hash is persisted.
    To verify later, the user re-submits the same text.
    """
    user_id = request.user_id

    body = request.get_json()
    if not body or 'text' not in body:
        return jsonify({'error': '"text" field is required'}), 400

    text = body['text'].strip()
    if not text:
        return jsonify({'error': 'Text cannot be empty'}), 400

    if len(text.encode('utf-8')) > 1_000_000:  # 1 MB text limit
        return jsonify({'error': 'Text exceeds 1 MB limit'}), 400

    label = (body.get('label') or '').strip() or None
    record = data_model.create_text_record(user_id, text, label)
    if not record:
        return jsonify({'error': 'Failed to store record'}), 500

    _log(user_id, AuditAction.UPLOAD_RECORD, record_id=record['_id'])

    return jsonify({
        'success': True,
        'message': 'Text fingerprint stored. SHA-256: ' + record['data_hash'],
        'verification_id': record.get('verification_id'),
        'verification_link': _public_verification_link(record.get('verification_id', '')),
        'record':  record,
    }), 201


# == VERIFY ====================================================================

@data_bp.route('/<record_id>/verify', methods=['POST'])
@token_required
def verify_record(record_id):
    """
    Verify data integrity by comparing a freshly computed hash with the stored one.

    POST /api/data/<record_id>/verify
    Authorization: Bearer <token>

    For FILE records  -> multipart/form-data with field "file"
    For TEXT records  -> application/json with field "text"

    Result:
      status = "verified"  -> hashes match, data is authentic
      status = "tampered"  -> hashes differ, data was modified
    """
    user_id = request.user_id
    content_type = request.content_type or ''

    if 'multipart/form-data' in content_type:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided. Send multipart/form-data with field "file"'}), 400
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        file_bytes = file.read()
        if not file_bytes:
            return jsonify({'error': 'Uploaded file is empty'}), 400
        result = data_model.verify_file(record_id, user_id, file_bytes)
    else:
        body = request.get_json()
        if not body or 'text' not in body:
            return jsonify({'error': 'Provide "text" in JSON body, or upload a file (multipart/form-data)'}), 400
        text = body['text']
        if not text:
            return jsonify({'error': 'Text cannot be empty'}), 400
        result = data_model.verify_text(record_id, user_id, text)

    if not result.get('success'):
        return jsonify(result), 400

    _log(
        user_id, AuditAction.VERIFY_RECORD,
        record_id=record_id,
        success=(result['status'] == 'verified'),
        details={'status': result['status']},
    )
    return jsonify(result), 200


# == USER RECORDS & STATS ======================================================

@data_bp.route('/my-records', methods=['GET'])
@token_required
def get_my_records():
    """Return all records belonging to the authenticated user."""
    user_id = request.user_id
    records = data_model.get_user_records(user_id)
    stats   = data_model.get_user_statistics(user_id)
    return jsonify({
        'success':    True,
        'count':      len(records),
        'statistics': stats,
        'records':    records,
    }), 200


@data_bp.route('/my-statistics', methods=['GET'])
@token_required
def get_my_statistics():
    """Return dashboard statistics for the authenticated user."""
    stats = data_model.get_user_statistics(request.user_id)
    return jsonify({'success': True, 'statistics': stats}), 200


@data_bp.route('/<record_id>', methods=['GET'])
@token_required
def get_record_by_id(record_id):
    """Get a single record (user must own it)."""
    record = data_model.get_record_by_id(record_id, request.user_id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    return jsonify({'success': True, 'record': record}), 200


@data_bp.route('/<record_id>', methods=['DELETE'])
@token_required
def delete_record(record_id):
    """Delete one record (owner only)."""
    deleted = data_model.delete_record(record_id, request.user_id)
    if not deleted:
        return jsonify({'error': 'Record not found'}), 404
    return jsonify({'success': True, 'message': 'Record deleted'}), 200


# == LEGACY ROUTES (no auth, backward compatibility) ===========================

@data_bp.route('/', methods=['GET'])
def get_all_data():
    """Legacy: return all records without user filter."""
    try:
        records = data_model.get_all_records()
        stats   = data_model.get_statistics()
        return jsonify({'success': True, 'count': len(records),
                        'statistics': stats, 'records': records}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@data_bp.route('/', methods=['POST'])
def create_data_legacy():
    """Legacy: create a text record without authentication (used by index.html)."""
    try:
        req_data = request.get_json()
        if not req_data or 'data' not in req_data:
            return jsonify({'error': 'data field is required'}), 400
        data = req_data['data'].strip()
        if not data:
            return jsonify({'error': 'Data cannot be empty'}), 400
        record = data_model.create_record(data)
        return jsonify({'success': True, 'message': 'Stored', 'record': record}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@data_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Legacy: global stats across all users."""
    try:
        stats = data_model.get_statistics()
        return jsonify({'success': True, 'statistics': stats}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@data_bp.route('/clear', methods=['DELETE'])
def clear_all_data():
    """Legacy: delete all records."""
    try:
        count = data_model.delete_all_records()
        return jsonify({'success': True, 'message': 'Deleted ' + str(count) + ' records', 'count': count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
