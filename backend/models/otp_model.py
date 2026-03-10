"""
OTP Model - Collection: otp_verifications
==========================================
Manages OTP records in MongoDB.

WHY THIS DESIGN:
- We never store plain OTPs — only bcrypt hashes (safe if DB is compromised)
- Each OTP belongs to a user + channel (email or phone) + purpose (register/login)
- `attempts` counter invalidates OTP after 3 wrong tries
- `used` flag prevents OTP reuse after successful verification
- `expires_at` enforces time-based expiry (10 min email, 5 min phone)

This model is queried heavily, so indexes are created on:
  - user_id (to find OTPs for a user)
  - identifier + channel (to verify OTPs by email/phone)
  - expires_at (MongoDB TTL — auto-deletes expired docs from DB)
"""

from datetime import datetime
from bson import ObjectId


class OTPModel:
    """Handles all OTP database operations"""

    def __init__(self, db):
        """Initialize with database, create necessary indexes"""
        self.collection = db['otp_verifications']

        # Index for fast lookups by user
        self.collection.create_index('user_id')

        # Compound index: find OTP by identifier + channel + purpose
        self.collection.create_index([
            ('identifier', 1),
            ('channel', 1),
            ('purpose', 1)
        ])

        # TTL index: MongoDB automatically deletes documents after expires_at
        # This is a background cleanup — no manual purging needed
        self.collection.create_index('expires_at', expireAfterSeconds=0)

    # ──────────────────────────────────────────────
    # CREATE
    # ──────────────────────────────────────────────

    def create_otp(self, user_id, identifier, otp_hash, channel,
                   purpose, expires_at, ip_address=None, user_agent=None):
        """
        Store a new OTP record in the database.

        Parameters:
            user_id     : MongoDB ObjectId of the user
            identifier  : Email or phone number
            otp_hash    : pbkdf2 hash of the raw OTP (never store plain)
            channel     : "email" or "phone"
            purpose     : "registration" or "login"
            expires_at  : datetime when OTP expires
            ip_address  : Requester's IP (for audit trail)
            user_agent  : Browser info (for audit trail)

        SECURITY: Before inserting, we invalidate any existing OTP for
        the same identifier+channel+purpose — prevents having multiple
        active OTPs simultaneously.
        """
        # Invalidate any previous unused OTP for same target
        self.invalidate_existing(identifier, channel, purpose)

        doc = {
            'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id,
            'identifier': identifier,           # email or phone
            'otp_hash': otp_hash,               # hashed — not raw OTP
            'channel': channel,                 # "email" or "phone"
            'purpose': purpose,                 # "registration" or "login"
            'expires_at': expires_at,           # datetime (MongoDB TTL uses this)
            'attempts': 0,                      # failed verification attempts
            'max_attempts': 3,                  # lock after 3 failures
            'used': False,                      # becomes True after success
            'created_at': datetime.utcnow(),
            'ip_address': ip_address,
            'user_agent': user_agent,
            'verified_at': None                 # set when OTP is verified
        }

        result = self.collection.insert_one(doc)
        doc['_id'] = result.inserted_id
        return doc

    # ──────────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────────

    def find_active_otp(self, identifier, channel, purpose):
        """
        Find a valid (unexpired, unused, not exhausted) OTP.

        WHY THIS QUERY:
        - used: False — OTP hasn't been verified yet
        - attempts < max_attempts — still has tries left
        - expires_at > now — not expired
        """
        now = datetime.utcnow()
        return self.collection.find_one({
            'identifier': identifier,
            'channel': channel,
            'purpose': purpose,
            'used': False,
            'attempts': {'$lt': 3},
            'expires_at': {'$gt': now}
        })

    # ──────────────────────────────────────────────
    # UPDATE
    # ──────────────────────────────────────────────

    def increment_attempts(self, otp_id):
        """
        Increment failed attempt counter.
        When attempts reaches max_attempts (3), find_active_otp won't
        return this OTP anymore — effectively invalidating it.
        """
        self.collection.update_one(
            {'_id': ObjectId(otp_id)},
            {'$inc': {'attempts': 1}}
        )

    def mark_as_used(self, otp_id):
        """
        Mark OTP as used after successful verification.
        Prevents the same OTP from being reused (replay attack protection).
        """
        self.collection.update_one(
            {'_id': ObjectId(otp_id)},
            {'$set': {
                'used': True,
                'verified_at': datetime.utcnow()
            }}
        )

    def invalidate_existing(self, identifier, channel, purpose):
        """
        Invalidate all previous unused OTPs for this identifier+channel+purpose.
        Called before creating a new OTP to ensure only one active OTP exists.
        """
        self.collection.update_many(
            {
                'identifier': identifier,
                'channel': channel,
                'purpose': purpose,
                'used': False
            },
            {'$set': {'used': True}}
        )

    # ──────────────────────────────────────────────
    # UTILITY
    # ──────────────────────────────────────────────

    def get_otp_attempts(self, otp_id):
        """Get current attempt count for an OTP"""
        doc = self.collection.find_one({'_id': ObjectId(otp_id)}, {'attempts': 1})
        return doc['attempts'] if doc else 0
