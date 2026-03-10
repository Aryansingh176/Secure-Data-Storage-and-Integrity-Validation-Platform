"""
Audit Log Model - Collection: audit_logs
=========================================
Immutable security audit trail for all authentication events.

WHY AUDIT LOGGING MATTERS (Great viva point!):
- Security forensics: "Who tried to login to this account at 3am?"
- Compliance: Many regulations (GDPR, SOC2) require audit trails
- Incident response: Know exactly what happened before a breach
- Debugging: Trace exactly why an OTP failed
- ML/Analytics: Detect anomalous login patterns

IMMUTABILITY: Audit logs are NEVER updated or deleted.
They are an append-only record of truth.
(MongoDB TTL can clean old logs after 90 days in production)
"""

from datetime import datetime
from bson import ObjectId


# Action types — well-defined constants prevent typos
class AuditAction:
    OTP_SENT = 'otp_sent'                   # OTP was sent to user
    OTP_VERIFIED = 'otp_verified'           # OTP was verified successfully
    OTP_FAILED = 'otp_failed'              # Wrong OTP entered
    OTP_EXPIRED = 'otp_expired'            # OTP was expired when checked
    OTP_EXHAUSTED = 'otp_exhausted'        # Max attempts reached
    RATE_LIMITED = 'rate_limited'          # Request blocked by rate limiter
    ACCOUNT_LOCKED = 'account_locked'      # Account locked after too many failures
    LOGIN_SUCCESS = 'login_success'        # Successful login
    REGISTRATION = 'registration'          # New user registered
    EMAIL_VERIFIED = 'email_verified'      # Email channel verified
    PHONE_VERIFIED = 'phone_verified'      # Phone channel verified
    RESEND_OTP = 'resend_otp'             # User requested OTP resend
    SUSPICIOUS_ACTIVITY = 'suspicious_activity'  # Anomalous pattern detected
    # Data integrity actions
    UPLOAD_RECORD = 'upload_record'        # User stored a file/text fingerprint
    VERIFY_RECORD = 'verify_record'        # User verified a record's integrity
    PROFILE_UPDATE = 'profile_update'      # User updated their profile
    OTP_REQUEST = 'otp_request'            # OTP explicitly requested


class AuditLogModel:
    """Handles audit log records — append-only security trail"""

    def __init__(self, db):
        """Initialize with database, create indexes"""
        self.collection = db['audit_logs']

        # Index for querying by user (most common lookup)
        self.collection.create_index('user_id')

        # Index for querying by identifier (email/phone) — for security checks
        self.collection.create_index('identifier')

        # Index for querying by action type — for dashboards
        self.collection.create_index('action')

        # Index for time-based queries — "show logs from last 24h"
        self.collection.create_index('timestamp')

        # Compound: user + time range queries
        self.collection.create_index([('user_id', 1), ('timestamp', -1)])

    def log(self, identifier, action, channel, success,
            ip_address=None, user_agent=None, user_id=None, details=None):
        """
        Record an authentication event.

        ALWAYS CALL THIS for every auth action — good or bad.
        Never skip logging failures — they're the most important!

        Parameters:
            identifier  : Email or phone number involved
            action      : One of AuditAction constants
            channel     : "email", "phone", or "system"
            success     : True if action succeeded, False if it failed
            ip_address  : Requester's IP address
            user_agent  : Browser/client info
            user_id     : MongoDB ObjectId (None if user not yet authenticated)
            details     : dict with extra context (reason, error, etc.)

        Returns:
            Inserted document ID
        """
        doc = {
            # Who — None before authentication, ObjectId after
            'user_id': ObjectId(user_id) if user_id and isinstance(user_id, str) else user_id,

            # What target — email or phone
            'identifier': identifier,

            # What happened
            'action': action,

            # Which channel
            'channel': channel,

            # Did it succeed?
            'success': success,

            # From where
            'ip_address': ip_address,
            'user_agent': user_agent,

            # When (UTC always — convert to local in frontend)
            'timestamp': datetime.utcnow(),

            # Extra context — reason for failure, OTP attempt count, etc.
            'details': details or {}
        }

        result = self.collection.insert_one(doc)
        return result.inserted_id

    def get_recent_failures(self, identifier, hours=24):
        """
        Count failed attempts for an identifier in the last N hours.

        USED FOR: Account lockout decision (Layer 3 rate limiting).
        After 5 failures in 24h, lock the account.
        """
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(hours=hours)

        return self.collection.count_documents({
            'identifier': identifier,
            'success': False,
            'action': {'$in': [AuditAction.OTP_FAILED, AuditAction.OTP_EXHAUSTED]},
            'timestamp': {'$gte': since}
        })

    def get_user_logs(self, user_id, limit=50):
        """Get recent audit logs for a user (for profile page / admin dashboard)"""
        return list(
            self.collection
            .find({'user_id': ObjectId(user_id)})
            .sort('timestamp', -1)
            .limit(limit)
        )

    def get_logs_by_identifier(self, identifier, limit=50):
        """Get logs by email/phone — useful before user is authenticated"""
        return list(
            self.collection
            .find({'identifier': identifier})
            .sort('timestamp', -1)
            .limit(limit)
        )

    def log_data_action(self, user_id, action, record_id=None,
                        ip_address=None, user_agent=None, success=True, details=None):
        """
        Record a data-integrity action (upload, verify, delete).

        Simpler than the auth log() method — no channel/identifier needed.

        Parameters:
            user_id    : MongoDB ObjectId or str of the authenticated user
            action     : AuditAction constant (e.g. AuditAction.UPLOAD_RECORD)
            record_id  : str _id of the affected data_record (optional)
            ip_address : requester IP
            user_agent : browser user-agent
            success    : True = action succeeded, False = it failed
            details    : extra context dict
        """
        from bson import ObjectId as _ObjId
        try:
            uid = _ObjId(user_id) if user_id and isinstance(user_id, str) else user_id
            rid = None
            if record_id:
                try:
                    rid = _ObjId(record_id)
                except Exception:
                    rid = record_id  # keep as-is if invalid
            doc = {
                'user_id':    uid,
                'action':     action,
                'record_id':  rid,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'success':    success,
                'timestamp':  datetime.utcnow(),
                'details':    details or {},
            }
            result = self.collection.insert_one(doc)
            return result.inserted_id
        except Exception as e:
            print(f'[AuditLog] Failed to write data action log: {e}')
            return None
