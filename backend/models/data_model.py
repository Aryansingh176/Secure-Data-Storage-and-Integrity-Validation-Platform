"""
Data Model - Collection: data_records
=======================================
BTech CSE Final Year Project - Data Integrity Platform

Core Concept:
  We NEVER store actual file content or raw text.
  We only store the SHA-256 cryptographic hash + metadata.
  Verification = re-submit file/text → recompute hash → compare.

Schema:
  _id                     : ObjectId
  user_id                 : ObjectId  (owner; null for legacy records)
  upload_method           : "file" | "text"
  original_filename       : str       (filename or label)
  file_type               : str       (e.g. "PDF Document")
  file_size               : int       (bytes)
  hash_algorithm          : "SHA-256"
  data_hash               : str       (64-char hex)
  verification_count      : int
  last_verification_status: "verified" | "tampered" | null
  created_at              : datetime
  last_verified_at        : datetime  (updated on each verification)
"""

from datetime import datetime
from bson import ObjectId
import hashlib
import uuid


class DataModel:
    """Handles file/text hash storage and integrity verification."""

    # Whitelist of allowed file extensions
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'jpg', 'jpeg', 'png', 'txt'}

    # 10 MB maximum file size
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Human-readable labels for each extension
    EXTENSION_LABELS = {
        'pdf':  'PDF Document',
        'docx': 'Word Document',
        'xlsx': 'Excel Spreadsheet',
        'jpg':  'JPEG Image',
        'jpeg': 'JPEG Image',
        'png':  'PNG Image',
        'txt':  'Text File',
    }

    def __init__(self, db):
        self.collection = db['data_records']
        self.verification_logs = db['verification_logs']
        # Compound index: user-scoped queries sorted by newest first
        self.collection.create_index([('user_id', 1), ('created_at', -1)])
        # Index on hash for quick duplicate detection
        self.collection.create_index('data_hash')
        # Index on verification_id for public link lookups
        self.collection.create_index('verification_id', unique=True, sparse=True)
        # Index for verification_logs
        self.verification_logs.create_index([('record_id', 1), ('verified_at', -1)])

    # ── Validation ────────────────────────────────────────────────────────────

    @staticmethod
    def get_extension(filename):
        """Return lowercase extension of filename, or None."""
        if '.' not in filename:
            return None
        return filename.rsplit('.', 1)[1].lower()

    @classmethod
    def validate_file(cls, filename, file_size):
        """
        Check extension whitelist and size limit.
        Returns (True, None) on success, (False, error_string) on failure.
        """
        if not filename or not filename.strip():
            return False, 'Filename is required'

        ext = cls.get_extension(filename)
        if not ext:
            return False, 'File must have an extension'

        if ext not in cls.ALLOWED_EXTENSIONS:
            allowed = ', '.join(f'.{e}' for e in sorted(cls.ALLOWED_EXTENSIONS))
            return False, f'File type .{ext} not allowed. Allowed: {allowed}'

        if file_size == 0:
            return False, 'File is empty'

        if file_size > cls.MAX_FILE_SIZE:
            mb = file_size / (1024 * 1024)
            return False, f'File size {mb:.1f} MB exceeds the 10 MB limit'

        return True, None

    # ── Hashing ───────────────────────────────────────────────────────────────

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        """SHA-256 hash of raw bytes (used for files)."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_text(text: str) -> str:
        """SHA-256 hash of UTF-8 encoded text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    # Legacy alias kept for backward compatibility
    @staticmethod
    def generate_hash(data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    # ── Serialization ─────────────────────────────────────────────────────────

    def _serialize(self, record):
        """Convert MongoDB document to JSON-serializable dict."""
        record['_id'] = str(record['_id'])
        if record.get('user_id'):
            record['user_id'] = str(record['user_id'])
        for dt_field in ('created_at', 'last_verified_at'):
            if record.get(dt_field) and hasattr(record[dt_field], 'isoformat'):
                record[dt_field] = record[dt_field].isoformat()
        return record

    # ── Create ────────────────────────────────────────────────────────────────

    def create_file_record(self, user_id, filename, file_bytes):
        """
        Store SHA-256 fingerprint of an uploaded file.

        The file bytes are hashed and then discarded — we never persist
        file content, only the hash + metadata.

        Args:
            user_id    : str or ObjectId of the authenticated user
            filename   : original filename (sanitised before calling this)
            file_bytes : raw bytes read from the uploaded file

        Returns:
            dict: serialised record, or None on DB error
        """
        ext = self.get_extension(filename)
        file_type = self.EXTENSION_LABELS.get(ext, (ext.upper() if ext else 'Unknown'))
        data_hash = self.hash_bytes(file_bytes)

        record = {
            'user_id':                  ObjectId(user_id) if isinstance(user_id, str) else user_id,
            'upload_method':            'file',
            'original_filename':        filename,
            'file_type':                file_type,
            'file_size':                len(file_bytes),
            'hash_algorithm':           'SHA-256',
            'data_hash':                data_hash,
            'verification_count':       0,
            'last_verification_status': None,
            'last_verified_at':         None,
            'created_at':               datetime.utcnow(),
            'verification_id':          str(uuid.uuid4()),
        }

        try:
            result = self.collection.insert_one(record)
            record['_id'] = result.inserted_id
            return self._serialize(record)
        except Exception as e:
            print(f'[DataModel] Error inserting file record: {e}')
            return None

    def create_text_record(self, user_id, text, label=None):
        """
        Store SHA-256 fingerprint of a text input.

        Args:
            user_id : str or ObjectId of the authenticated user
            text    : raw text content (not stored, only hashed)
            label   : optional user-provided name for this record

        Returns:
            dict: serialised record, or None on DB error
        """
        data_hash = self.hash_text(text)

        record = {
            'user_id':                  ObjectId(user_id) if isinstance(user_id, str) else user_id,
            'upload_method':            'text',
            'original_filename':        label or 'Text Input',
            'file_type':                'Text',
            'file_size':                len(text.encode('utf-8')),
            'hash_algorithm':           'SHA-256',
            'data_hash':                data_hash,
            'verification_count':       0,
            'last_verification_status': None,
            'last_verified_at':         None,
            'created_at':               datetime.utcnow(),
            'verification_id':          str(uuid.uuid4()),
        }

        try:
            result = self.collection.insert_one(record)
            record['_id'] = result.inserted_id
            return self._serialize(record)
        except Exception as e:
            print(f'[DataModel] Error inserting text record: {e}')
            return None

    # ── Verification ──────────────────────────────────────────────────────────

    def _do_verify(self, record_id, user_id, computed_hash):
        """
        Internal helper: compare computed_hash against stored data_hash.
        Updates verification_count and last_verification_status.
        Returns result dict.
        """
        try:
            query = {'_id': ObjectId(record_id)}
            if user_id:
                query['user_id'] = ObjectId(user_id) if isinstance(user_id, str) else user_id
            record = self.collection.find_one(query)
        except Exception:
            return {'success': False, 'message': 'Invalid record ID'}

        if not record:
            return {'success': False, 'message': 'Record not found or access denied'}

        stored_hash = record['data_hash']
        matched = (computed_hash == stored_hash)
        status = 'verified' if matched else 'tampered'

        self.collection.update_one(
            {'_id': ObjectId(record_id)},
            {'$inc': {'verification_count': 1},
             '$set': {'last_verification_status': status,
                      'last_verified_at': datetime.utcnow()}}
        )

        return {
            'success':       True,
            'status':        status,
            'matched':       matched,
            'message':       ('Integrity verified — No tampering detected'
                               if matched else
                               'TAMPERED — Hash mismatch detected!'),
            'stored_hash':   stored_hash,
            'computed_hash': computed_hash,
            'filename':      record.get('original_filename', ''),
            'upload_method': record.get('upload_method', ''),
        }

    def _do_verify_public(self, record_id, computed_hash):
        """Update verification stats for a public (no-auth) verification."""
        record = self.collection.find_one({'_id': ObjectId(record_id) if isinstance(record_id, str) else record_id})
        if not record:
            return
        matched = (computed_hash == record.get('data_hash', ''))
        status  = 'verified' if matched else 'tampered'
        self.collection.update_one(
            {'_id': record['_id']},
            {'$inc': {'verification_count': 1},
             '$set': {'last_verification_status': status, 'last_verified_at': datetime.utcnow()}}
        )

    def verify_file(self, record_id, user_id, file_bytes):
        """
        Re-hash the uploaded file and compare against stored hash.

        VIVA POINT:
        The user re-uploads the same file. Backend computes a fresh
        SHA-256 hash and compares byte-for-byte with the stored hash.
        Even a single bit change produces a completely different hash
        (avalanche effect), so any tampering is instantly detected.
        """
        record = self.collection.find_one({'_id': ObjectId(record_id)})
        if record and record.get('upload_method') == 'text':
            return {'success': False,
                    'message': 'This record stores a text fingerprint. Use text verification.'}
        computed = self.hash_bytes(file_bytes)
        return self._do_verify(record_id, user_id, computed)

    def verify_text(self, record_id, user_id, text):
        """
        Re-hash the submitted text and compare against stored hash.
        """
        record = self.collection.find_one({'_id': ObjectId(record_id)})
        if record and record.get('upload_method') == 'file':
            return {'success': False,
                    'message': 'This record stores a file fingerprint. Upload the file to verify.'}
        computed = self.hash_text(text)
        return self._do_verify(record_id, user_id, computed)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_user_records(self, user_id, limit=100):
        """Return all records owned by user_id, newest first."""
        uid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        return [self._serialize(r)
                for r in self.collection.find({'user_id': uid})
                                         .sort('created_at', -1)
                                         .limit(limit)]

    def get_user_statistics(self, user_id):
        """
        Aggregate dashboard stats for a single user.

        Returns dict with:
          total_records, total_verifications,
          verified_count, tampered_count,
          file_records, text_records
        """
        uid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        pipeline = [
            {'$match': {'user_id': uid}},
            {'$group': {
                '_id': None,
                'total_records':       {'$sum': 1},
                'total_verifications': {'$sum': '$verification_count'},
                'verified_count': {'$sum': {'$cond': [{'$eq': ['$last_verification_status', 'verified']}, 1, 0]}},
                'tampered_count': {'$sum': {'$cond': [{'$eq': ['$last_verification_status', 'tampered']}, 1, 0]}},
                'file_records':   {'$sum': {'$cond': [{'$eq': ['$upload_method', 'file']}, 1, 0]}},
                'text_records':   {'$sum': {'$cond': [{'$eq': ['$upload_method', 'text']}, 1, 0]}},
            }}
        ]
        result = list(self.collection.aggregate(pipeline))
        if result:
            stats = result[0]
            stats.pop('_id', None)
            return stats
        return {
            'total_records': 0, 'total_verifications': 0,
            'verified_count': 0, 'tampered_count': 0,
            'file_records': 0,  'text_records': 0,
        }

    def get_record_by_id(self, record_id, user_id=None):
        """Get a single record; enforce ownership if user_id is provided."""
        try:
            query = {'_id': ObjectId(record_id)}
            if user_id:
                query['user_id'] = ObjectId(user_id) if isinstance(user_id, str) else user_id
            record = self.collection.find_one(query)
            return self._serialize(record) if record else None
        except Exception:
            return None

    def get_record_by_verification_id(self, verification_id):
        """Lookup a record by its public verification_id UUID."""
        record = self.collection.find_one({'verification_id': verification_id})
        return self._serialize(record) if record else None

    def log_verification_attempt(self, record_id, result, ip_address):
        """Save a verification attempt to the verification_logs collection."""
        try:
            self.verification_logs.insert_one({
                'record_id':   ObjectId(record_id) if isinstance(record_id, str) else record_id,
                'verified_at': datetime.utcnow(),
                'result':      result,       # 'verified' | 'tampered'
                'ip_address':  ip_address,
            })
        except Exception as e:
            print(f'[DataModel] verification_log write failed: {e}')

    def get_verification_logs(self, record_id, limit=20):
        """Return recent verification attempts for a record."""
        try:
            logs = list(
                self.verification_logs
                .find({'record_id': ObjectId(record_id)})
                .sort('verified_at', -1)
                .limit(limit)
            )
            for log in logs:
                log['_id'] = str(log['_id'])
                log['record_id'] = str(log['record_id'])
                if log.get('verified_at'):
                    log['verified_at'] = log['verified_at'].isoformat()
            return logs
        except Exception:
            return []

    def get_all_records(self):
        """Legacy: return all records without user filter (newest first)."""
        return [self._serialize(r)
                for r in self.collection.find().sort('created_at', -1).limit(200)]

    def get_statistics(self):
        """Legacy: global stats across all users."""
        total    = self.collection.count_documents({})
        verified = self.collection.count_documents({'last_verification_status': 'verified'})
        tampered = self.collection.count_documents({'last_verification_status': 'tampered'})
        return {'total_records': total, 'verified_count': verified, 'tampered_count': tampered}

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_record(self, record_id, user_id=None):
        """Delete one record; enforce ownership if user_id given."""
        try:
            query = {'_id': ObjectId(record_id)}
            if user_id:
                query['user_id'] = ObjectId(user_id) if isinstance(user_id, str) else user_id
            return self.collection.delete_one(query).deleted_count > 0
        except Exception:
            return False

    def delete_all_records(self):
        """Legacy: delete all records."""
        return self.collection.delete_many({}).deleted_count

    # ── Legacy create (text-only, no auth) used by index.html ─────────────────

    def create_record(self, data):
        """
        Legacy endpoint: hash text and store without user_id.
        Kept so existing index.html form still works.
        """
        data_hash = self.generate_hash(data)
        record = {
            'upload_method':            'text',
            'original_filename':        'Legacy Text Input',
            'file_type':                'Text',
            'file_size':                len(data.encode('utf-8')),
            'hash_algorithm':           'SHA-256',
            'data_hash':                data_hash,
            'verification_count':       0,
            'last_verification_status': None,
            'created_at':               datetime.utcnow(),
        }
        result = self.collection.insert_one(record)
        record['_id'] = str(result.inserted_id)
        record['created_at'] = record['created_at'].isoformat()
        return record

    def verify_integrity(self, record_id):
        """Legacy: verify by record_id only (no user scope)."""
        return self._do_verify(record_id, user_id=None,
                               computed_hash=None)  # not used anymore


