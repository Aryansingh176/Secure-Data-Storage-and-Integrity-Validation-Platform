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

from flask import Blueprint, request, jsonify, make_response
from werkzeug.utils import secure_filename
import hashlib
import io
import os
from datetime import datetime
from bson import ObjectId

from models.data_model import DataModel
from models.audit_log_model import AuditLogModel, AuditAction
from services.auth_service import token_required, get_client_ip, get_user_agent

# PDF certificate generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

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
    print('[OK] Integrity routes initialized  (/api/upload  /api/verify  /api/records  /api/dashboard/stats  /api/public/record/<verification_id>)')


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


def _public_verification_link(verification_id: str) -> str:
    """Create absolute public verification URL on static verify page."""
    base = (
        os.getenv('PUBLIC_VERIFY_BASE_URL')
        or os.getenv('FRONTEND_URL')
        or 'https://secure-data-storage-and-integrity-v.vercel.app'
    ).rstrip('/')
    return f'{base}/verify.html?id={verification_id}'


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
        'verification_id': record.get('verification_id'),
        'verification_link': _public_verification_link(record.get('verification_id', '')),
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


# == GET /api/public/record/<verification_id> ==================================

@integrity_bp.route('/public/record/<verification_id>', methods=['GET'])
@integrity_bp.route('/public/verify/<verification_id>', methods=['GET'])
def public_record_info(verification_id):
    """
    Public endpoint — returns record metadata for the public verification page.
    No authentication required; exposes only non-sensitive fields.
    """
    record = _data_model.get_record_by_verification_id(verification_id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404

    return jsonify({
        'success':          True,
        'verification_id':  verification_id,
        'verification_link': _public_verification_link(verification_id),
        'original_filename': record.get('original_filename', ''),
        'upload_date':      record.get('created_at', ''),
        'file_type':        record.get('file_type', ''),
        'file_size':        record.get('file_size', 0),
        'hash_algorithm':   record.get('hash_algorithm', 'SHA-256'),
        'upload_method':    record.get('upload_method', ''),
        'created_at':       record.get('created_at', ''),
        'verification_count': record.get('verification_count', 0),
        'last_verification_status': record.get('last_verification_status'),
    }), 200


# == POST /api/public/verify/<verification_id> =================================

@integrity_bp.route('/public/verify/<verification_id>', methods=['POST'])
def public_verify(verification_id):
    """
    Public endpoint — anyone can upload a file/text and check it against the
    stored hash. No authentication required (public sharing).

    File → multipart/form-data field: "file"
    Text → application/json    field: "text"
    """
    record = _data_model.get_record_by_verification_id(verification_id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404

    record_id     = record['_id']
    upload_method = record.get('upload_method', 'file')
    stored_hash   = record.get('data_hash', '')
    content_type  = request.content_type or ''
    ip_address    = get_client_ip()
    user_agent    = get_user_agent()

    if upload_method == 'file':
        if 'multipart/form-data' not in content_type:
            return jsonify({'error': 'This verification link expects a file upload'}), 400
        if 'file' not in request.files or not request.files['file'].filename:
            return jsonify({'error': 'No file provided'}), 400
        uploaded_file = request.files['file']
        filename = secure_filename(uploaded_file.filename)
        file_bytes = uploaded_file.read()
        if not file_bytes:
            return jsonify({'error': 'File is empty'}), 400
        valid, error_msg = DataModel.validate_file(filename, len(file_bytes))
        if not valid:
            return jsonify({'error': error_msg}), 400
        computed = hashlib.sha256(file_bytes).hexdigest()
    else:
        body = request.get_json(silent=True) or {}
        text = (body.get('text') or '').strip()
        if not text:
            return jsonify({'error': '"text" is required'}), 400
        computed = hashlib.sha256(text.encode('utf-8')).hexdigest()

    matched = (computed == stored_hash)
    status  = 'verified' if matched else 'tampered'

    # Update record stats (no user_id check — public verification)
    _data_model._do_verify_public(record_id, computed)

    # Log the attempt
    _data_model.log_verification_attempt(record_id, status, ip_address)
    _log(
        user_id=record.get('user_id'),
        action=AuditAction.VERIFY_RECORD,
        record_id=record_id,
        success=matched,
        details={
            'status': status,
            'public': True,
            'verification_id': verification_id,
            'ip_address': ip_address,
            'upload_method': upload_method,
        },
    )

    return jsonify({
        'status':        status,
        'matched':       matched,
        'message':       ('Integrity verified — No tampering detected'
                          if matched else
                          'TAMPERED — Hash mismatch detected!'),
        'stored_hash':   stored_hash,
        'computed_hash': computed,
        'verification_count': _get_verification_count(str(record_id)),
    }), 200


# == GET /api/records/<id>/certificate =========================================

@integrity_bp.route('/records/<record_id>/certificate', methods=['GET'])
@token_required
def download_certificate(record_id):
    """
    Generate and download a PDF integrity certificate for a verified record.
    """
    if not REPORTLAB_AVAILABLE:
        return jsonify({'error': 'PDF generation not available. Install reportlab.'}), 500

    user_id = request.user_id
    record  = _data_model.get_record_by_id(record_id, user_id)
    if not record:
        return jsonify({'error': 'Record not found or access denied'}), 404

    pdf_bytes = _generate_certificate_pdf(record)

    filename = f"integrity_certificate_{record_id[:8]}.pdf"
    response = make_response(pdf_bytes)
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _generate_certificate_pdf(record: dict) -> bytes:
    """Build and return the PDF bytes for an integrity certificate."""
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2.5*cm, rightMargin=2.5*cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('title', parent=styles['Title'],
                                 fontSize=22, spaceAfter=6, textColor=colors.HexColor('#1a237e'))
    sub_style   = ParagraphStyle('sub', parent=styles['Normal'],
                                 fontSize=11, spaceAfter=4, textColor=colors.HexColor('#555555'),
                                 alignment=TA_CENTER)
    label_style = ParagraphStyle('label', parent=styles['Normal'],
                                 fontSize=10, textColor=colors.HexColor('#1565c0'), fontName='Helvetica-Bold')
    value_style = ParagraphStyle('value', parent=styles['Normal'],
                                 fontSize=10, textColor=colors.HexColor('#212121'))
    hash_style  = ParagraphStyle('hash', parent=styles['Code'],
                                 fontSize=8,  textColor=colors.HexColor('#37474f'),
                                 backColor=colors.HexColor('#f5f5f5'), leading=14)

    status = record.get('last_verification_status', 'not_verified')
    if status == 'verified':
        status_color, status_text = colors.HexColor('#2e7d32'), 'VERIFIED ✓'
    elif status == 'tampered':
        status_color, status_text = colors.HexColor('#c62828'), 'TAMPERED ✗'
    else:
        status_color, status_text = colors.HexColor('#757575'), 'NOT VERIFIED'

    status_style = ParagraphStyle('status', parent=styles['Normal'],
                                  fontSize=16, fontName='Helvetica-Bold',
                                  textColor=status_color, alignment=TA_CENTER, spaceAfter=6)

    created_at = record.get('created_at', '')
    if created_at:
        try:
            dt = datetime.fromisoformat(str(created_at).replace('Z', ''))
            created_at = dt.strftime('%d %B %Y, %H:%M UTC')
        except Exception:
            pass

    elements = [
        Paragraph('Data Integrity Platform', title_style),
        Paragraph('Cryptographic Integrity Certificate', sub_style),
        HRFlowable(width='100%', thickness=2, color=colors.HexColor('#1a237e')),
        Spacer(1, 0.5*cm),
        Paragraph(status_text, status_style),
        Spacer(1, 0.4*cm),
    ]

    table_data = [
        [Paragraph('File Name',       label_style), Paragraph(record.get('original_filename', '—'), value_style)],
        [Paragraph('File Type',       label_style), Paragraph(record.get('file_type', '—'), value_style)],
        [Paragraph('File Size',       label_style), Paragraph(_fmt_size(record.get('file_size', 0)), value_style)],
        [Paragraph('Hash Algorithm',  label_style), Paragraph(record.get('hash_algorithm', 'SHA-256'), value_style)],
        [Paragraph('Upload Date',     label_style), Paragraph(str(created_at), value_style)],
        [Paragraph('Verifications',   label_style), Paragraph(str(record.get('verification_count', 0)), value_style)],
    ]

    t = Table(table_data, colWidths=[4.5*cm, 11*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
        ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph('SHA-256 Hash', label_style))
    elements.append(Spacer(1, 0.15*cm))
    elements.append(Paragraph(record.get('data_hash', ''), hash_style))
    elements.append(Spacer(1, 0.6*cm))
    elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e0e0e0')))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(
        f'Generated on {datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")} &nbsp;|&nbsp; Data Integrity Platform — BTech CSE Final Year Project',
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=8,
                       textColor=colors.HexColor('#9e9e9e'), alignment=TA_CENTER)
    ))

    doc.build(elements)
    return buf.getvalue()


def _fmt_size(n: int) -> str:
    if not n:
        return '—'
    if n < 1024:
        return f'{n} B'
    if n < 1024 * 1024:
        return f'{n/1024:.1f} KB'
    return f'{n/(1024*1024):.1f} MB'


# == GET /api/activity =========================================================

@integrity_bp.route('/activity', methods=['GET'])
@token_required
def recent_activity():
    """Return recent audit_log entries for the authenticated user."""
    user_id = request.user_id
    try:
        from bson import ObjectId as ObjId
        logs = list(
            _audit_model.collection
            .find({'user_id': ObjId(user_id)})
            .sort('timestamp', -1)
            .limit(15)
        )
        result = []
        for log in logs:
            log['_id'] = str(log['_id'])
            if log.get('user_id'):
                log['user_id'] = str(log['user_id'])
            if log.get('record_id'):
                log['record_id'] = str(log['record_id'])
            if log.get('timestamp') and hasattr(log['timestamp'], 'isoformat'):
                log['timestamp'] = log['timestamp'].isoformat()
            result.append(log)
        return jsonify({'success': True, 'activity': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
