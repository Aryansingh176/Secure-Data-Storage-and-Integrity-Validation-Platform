"""
Integrity Routes
=================
BTech CSE Final Year Project - Data Integrity Platform

Clean, simple API routes for file upload and integrity verification.

Routes
------
  POST   /api/upload              Upload file or text -> store SHA-256 hash
  POST   /api/verify              Verify a file/text against a stored record
  GET    /api/records             Get all records for the logged-in user
  DELETE /api/records/<id>        Delete a record (owner only)
  GET    /api/dashboard/stats     Dashboard statistics for the logged-in user

How SHA-256 Integrity Works (VIVA NOTE)
-----------------------------------------
1. User uploads a file. Backend reads raw bytes, computes SHA-256 hash.
2. Hash + metadata are stored in MongoDB. The file itself is discarded.
3. To verify later, user re-uploads the same file.
4. Backend recomputes SHA-256. If it matches stored hash → VERIFIED.
5. Any modification to the file (even 1 byte) changes the hash entirely
   (avalanche effect), so tampering is instantly detected.

Security Checks Applied
-----------------------
- File extension whitelist  (.pdf .docx .xlsx .jpg .jpeg .png .txt)
- File size limit           (10 MB)
- JWT authentication        (all routes require Bearer token)
- Ownership enforcement     (users can only access their own records)
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import hashlib
from datetime import datetime
from bson import ObjectId

from models.data_model import DataModel
from models.audit_log_model import AuditLogModel, AuditAction
from services.auth_service import token_required, get_client_ip, get_user_agent

# Blueprint prefix: /api
integrity_bp = Blueprint('integrity', __name__, url_prefix='/api')

# Injected on startup
_data_model: DataModel = None
_audit_model: AuditLogModel = None

# ── Allowed file types ────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'jpg', 'jpeg', 'png', 'txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

EXTENSION_LABELS = {
    'pdf':  'PDF Document',
    'docx': 'Word Document',
    'xlsx': 'Excel Spreadsheet',
    'jpg':  'JPEG Image',
    'jpeg': 'JPEG Image',
    'png':  'PNG Image',
    'txt':  'Text File',
}


def init_integrity_routes(db):
    """Called from app.py after MongoDB connects."""
    global _data_model, _audit_model
    _data_model  = DataModel(db)
    _audit_model = AuditLogModel(db)
    print('[OK] Integrity routes initialized  (/api/upload  /api/verify  /api/records  /api/dashboard/stats)')


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ext(filename: str):
    """Return lowercase extension without the dot, or empty string."""
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def _sha256_bytes(data: bytes) -> str:
    """SHA-256 of raw bytes (files)."""
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    """SHA-256 of UTF-8 encoded text."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _log(user_id, action, record_id=None, success=True, details=None):
    """Append one row to audit_logs (silently ignore errors)."""
    try:
        _audit_model.log_data_action(
            user_id=user_id,
            action=action,
            record_id=record_id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            success=success,
            details=details or {},
        )
    except Exception as exc:
        print(f'[AuditLog] write failed: {exc}')


# == POST /api/upload ==========================================================

@integrity_bp.route('/upload', methods=['POST'])
@token_required
def upload():
    """
    Store a SHA-256 fingerprint of a file OR raw text.

    File upload  → multipart/form-data  field: "file"
    Text input   → application/json     fields: "text", "label" (optional)

    Workflow:
      1. Detect content type (file vs text)
      2. Validate extension / size
      3. Compute SHA-256 hash
      4. Store metadata + hash in MongoDB (NOT the file content)
      5. Write audit log
      6. Return record

    Response 201:
      {
        "success": true,
        "message": "Record stored",
        "hash": "<64-char hex>",
        "record": { ... }
      }
    """
    user_id      = request.user_id
    content_type = request.content_type or ''

    # ── Branch: file upload ───────────────────────────────────────────────────
    if 'multipart/form-data' in content_type:
        if 'file' not in request.files or not request.files['file'].filename:
            return jsonify({'error': 'No file provided. Send multipart/form-data with field "file"'}), 400

        uploaded = request.files['file']
        filename  = secure_filename(uploaded.filename)
        ext       = _ext(filename)

        if ext not in ALLOWED_EXTENSIONS:
            allowed_str = ', '.join(f'.{e}' for e in sorted(ALLOWED_EXTENSIONS))
            return jsonify({'error': f'File type .{ext} not allowed. Allowed: {allowed_str}'}), 400

        file_bytes = uploaded.read()

        if len(file_bytes) == 0:
            return jsonify({'error': 'File is empty'}), 400

        if len(file_bytes) > MAX_FILE_SIZE:
            mb = len(file_bytes) / (1024 * 1024)
            return jsonify({'error': f'File size {mb:.1f} MB exceeds 10 MB limit'}), 400

        data_hash = _sha256_bytes(file_bytes)
        record    = _data_model.create_file_record(user_id, filename, file_bytes)

    # ── Branch: text input ────────────────────────────────────────────────────
    else:
        body = request.get_json(silent=True) or {}
        text  = (body.get('text') or '').strip()
        label = (body.get('label') or '').strip() or None

        if not text:
            return jsonify({'error': '"text" field is required for text input'}), 400

        if len(text.encode('utf-8')) > MAX_FILE_SIZE:
            return jsonify({'error': 'Text exceeds 10 MB limit'}), 400

        data_hash = _sha256_text(text)
        record    = _data_model.create_text_record(user_id, text, label)

    if not record:
        return jsonify({'error': 'Database error while saving record'}), 500

    _log(user_id, AuditAction.UPLOAD_RECORD, record_id=record.get('_id'))

    return jsonify({
        'success': True,
        'message': 'Record stored',
        'hash':    data_hash,
        'record':  record,
    }), 201


# == POST /api/verify ==========================================================

@integrity_bp.route('/verify', methods=['POST'])
@token_required
def verify():
    """
    Verify a file or text against a previously stored fingerprint.

    Always requires the record ID:
      - JSON field   "record_id"  for text verification
      - Form field   "record_id"  for file verification

    File verify → multipart/form-data  fields: "file", "record_id"
    Text verify → application/json     fields: "text", "record_id"

    Workflow:
      1. Read record_id → load stored hash from MongoDB
      2. Recompute SHA-256 from the submitted file/text
      3. Compare hashes
      4. Update verification_count + last_verification_status
      5. Write audit log
      6. Return result

    Response 200:
      {
        "status": "verified" | "tampered",
        "matched": true | false,
        "message": "...",
        "stored_hash": "...",
        "computed_hash": "...",
        "verification_count": N
      }
    """
    user_id      = request.user_id
    content_type = request.content_type or ''

    # ── Branch: file ──────────────────────────────────────────────────────────
    if 'multipart/form-data' in content_type:
        record_id = request.form.get('record_id', '').strip()
        if not record_id:
            return jsonify({'error': '"record_id" form field is required'}), 400

        if 'file' not in request.files or not request.files['file'].filename:
            return jsonify({'error': 'No file provided. Send multipart/form-data with field "file"'}), 400

        file_bytes = request.files['file'].read()
        if not file_bytes:
            return jsonify({'error': 'Uploaded file is empty'}), 400

        result = _data_model.verify_file(record_id, user_id, file_bytes)

    # ── Branch: text ──────────────────────────────────────────────────────────
    else:
        body      = request.get_json(silent=True) or {}
        record_id = (body.get('record_id') or '').strip()
        text      = (body.get('text') or '')

        if not record_id:
            return jsonify({'error': '"record_id" is required'}), 400
        if not text:
            return jsonify({'error': '"text" is required'}), 400

        result = _data_model.verify_text(record_id, user_id, text)

    if not result.get('success'):
        return jsonify({'error': result.get('message', 'Verification failed')}), 400

    _log(
        user_id,
        AuditAction.VERIFY_RECORD,
        record_id=record_id,
        success=(result['status'] == 'verified'),
        details={'status': result['status']},
    )

    return jsonify({
        'status':             result['status'],
        'matched':            result['matched'],
        'message':            result['message'],
        'stored_hash':        result['stored_hash'],
        'computed_hash':      result['computed_hash'],
        'filename':           result.get('filename', ''),
        'upload_method':      result.get('upload_method', ''),
        'verification_count': _get_verification_count(record_id),
    }), 200


# == GET /api/records ==========================================================

@integrity_bp.route('/records', methods=['GET'])
@token_required
def get_records():
    """
    Return all integrity records owned by the authenticated user.

    Sorted newest-first.
    Optional query param:  ?limit=50  (default 100)

    Response 200:
      {
        "success": true,
        "count": N,
        "records": [ { ... }, ... ]
      }
    """
    user_id = request.user_id
    try:
        limit   = min(int(request.args.get('limit', 100)), 500)
    except (ValueError, TypeError):
        limit = 100

    records = _data_model.get_user_records(user_id, limit=limit)

    return jsonify({
        'success': True,
        'count':   len(records),
        'records': records,
    }), 200


# == DELETE /api/records/<id> ==================================================

@integrity_bp.route('/records/<record_id>', methods=['DELETE'])
@token_required
def delete_record(record_id):
    """
    Delete one integrity record.

    Only the owning user can delete their own records.

    Response 200:
      { "success": true, "message": "Record deleted" }
    """
    user_id = request.user_id
    deleted = _data_model.delete_record(record_id, user_id)

    if not deleted:
        return jsonify({'error': 'Record not found or access denied'}), 404

    _log(user_id, AuditAction.UPLOAD_RECORD, record_id=record_id,
         details={'action': 'delete'})

    return jsonify({'success': True, 'message': 'Record deleted'}), 200


# == GET /api/dashboard/stats ==================================================

@integrity_bp.route('/dashboard/stats', methods=['GET'])
@token_required
def dashboard_stats():
    """
    Return dashboard statistics for the authenticated user.

    Uses a single MongoDB aggregation query — efficient and avoids N+1 queries.

    Response 200:
      {
        "success": true,
        "stats": {
          "total_records":        N,
          "total_verifications":  N,
          "verified_count":       N,
          "tampered_count":       N,
          "file_records":         N,
          "text_records":         N
        },
        "recent_uploads": [ { ... }, ... ]
      }
    """
    user_id = request.user_id

    stats          = _data_model.get_user_statistics(user_id)
    recent_uploads = _data_model.get_user_records(user_id, limit=5)

    return jsonify({
        'success':        True,
        'stats':          stats,
        'recent_uploads': recent_uploads,
    }), 200


# ── Private helper ─────────────────────────────────────────────────────────────

def _get_verification_count(record_id: str) -> int:
    """Read the updated verification_count back from MongoDB after verify."""
    try:
        record = _data_model.get_record_by_id(record_id)
        return record.get('verification_count', 0) if record else 0
    except Exception:
        return 0
