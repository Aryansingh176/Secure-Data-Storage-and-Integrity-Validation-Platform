"""
OTP Service
============
Core OTP generation, hashing, and verification logic.

This service is the heart of the authentication system.
It orchestrates:
  1. Generating cryptographically secure 6-digit OTPs
  2. Hashing OTPs before storage (security)
  3. Verifying entered OTPs against stored hashes
  4. Enforcing attempt limits and expiry

SECURITY DESIGN (viva points!):
- Use secrets.randbelow() not random.randint() — secrets is CSPRNG
  (Cryptographically Secure Pseudo-Random Number Generator)
  random module is predictable; secrets is not
- Store only pbkdf2:sha256 hash, never the raw OTP
  → Even if MongoDB is dumped, OTPs can't be recovered
- Auto-invalidate after 3 wrong attempts
  → 10^6 OTPs possible; 3 attempts = 0.0003% brute force chance
"""

import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Import models
from models.otp_model import OTPModel
from models.audit_log_model import AuditLogModel, AuditAction


def generate_otp():
    """
    Generate a 6-digit cryptographically secure OTP.

    WHY secrets.randbelow() and not random.randint()?
    - random module uses Mersenne Twister — predictable with enough samples
    - secrets module uses OS-level CSPRNG (urandom) — truly unpredictable
    - For security-critical codes like OTPs, always use secrets

    Returns: str like "483920" (always 6 digits, zero-padded)
    """
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


def hash_otp(otp):
    """
    Hash an OTP before storing in the database.

    Using werkzeug's pbkdf2:sha256 with automatic salt generation.
    WHY HASH OTPs?
    - Database breach protection: stolen DB cannot reveal active OTPs
    - Privacy: OTPs are effectively one-time passwords — treat them as such
    - Industry practice: Same reason passwords are hashed

    Note: bcrypt would also work (slightly slower = more brute-force resistant)
    pbkdf2:sha256 is faster and sufficient for 6-digit codes (short-lived)
    """
    return generate_password_hash(otp, method='pbkdf2:sha256')


def verify_otp_hash(entered_otp, stored_hash):
    """
    Verify a raw OTP against its stored hash.
    Returns True if match, False otherwise.

    check_password_hash handles timing-safe comparison internally.
    (Prevents timing attacks where response time reveals partial matches)
    """
    try:
        return check_password_hash(stored_hash, entered_otp)
    except Exception:
        return False


class OTPService:
    """
    Orchestrates the full OTP lifecycle:
    send → verify → expire → audit
    """

    def __init__(self, db):
        """Initialize with all models needed"""
        self.otp_model = OTPModel(db)
        self.audit_model = AuditLogModel(db)

    def create_and_store_otp(self, user_id, identifier, channel,
                              purpose, ip_address=None, user_agent=None):
        """
        Generate a new OTP, hash it, and store in DB.

        Parameters:
            user_id    : MongoDB user ObjectId
            identifier : Email or phone used for this OTP
            channel    : "email" or "phone"
            purpose    : "registration" or "login"

        Returns:
            tuple: (raw_otp: str, otp_doc: dict)
            raw_otp is passed to the email/SMS service for sending.
            We immediately discard it — only the hash lives in DB.

        EXPIRY POLICY:
        - Email: 10 minutes (email can be delayed by spam filters/servers)
        - Phone: 5 minutes (SMS is instant; shorter = more secure)
        """
        # Calculate expiry based on channel
        if channel == 'email':
            expires_at = datetime.utcnow() + timedelta(minutes=10)
        else:
            expires_at = datetime.utcnow() + timedelta(minutes=5)

        # Generate and hash
        raw_otp = generate_otp()
        otp_hash = hash_otp(raw_otp)

        # Store hashed version
        otp_doc = self.otp_model.create_otp(
            user_id=user_id,
            identifier=identifier,
            otp_hash=otp_hash,
            channel=channel,
            purpose=purpose,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Log the OTP send event (without the OTP itself!)
        self.audit_model.log(
            identifier=identifier,
            action=AuditAction.OTP_SENT,
            channel=channel,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=str(user_id),
            details={'purpose': purpose, 'expires_at': expires_at.isoformat()}
        )

        # Return raw OTP to caller (for sending via email/SMS)
        # After this function returns, forget the raw OTP
        return raw_otp, otp_doc

    def verify_otp(self, identifier, entered_otp, channel, purpose,
                   user_id=None, ip_address=None, user_agent=None):
        """
        Verify a user-entered OTP against the stored hash.

        VERIFICATION FLOW:
        1. Find active OTP (not expired, not used, attempts < 3)
        2. If not found → OTP expired or doesn't exist
        3. Check hash match
        4. If wrong → increment attempts, check if exhausted
        5. If correct → mark as used, return success

        Returns:
            dict with keys:
              - success (bool)
              - error_code (str): machine-readable error
              - message (str): human-readable message
              - attempts_remaining (int): tries left (on failure)
        """
        # Step 1: Find active OTP
        otp_doc = self.otp_model.find_active_otp(identifier, channel, purpose)

        if not otp_doc:
            # Check if there's an expired/exhausted OTP (for better error message)
            self.audit_model.log(
                identifier=identifier,
                action=AuditAction.OTP_EXPIRED,
                channel=channel,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=user_id,
                details={'reason': 'No active OTP found'}
            )
            return {
                'success': False,
                'error_code': 'OTP_NOT_FOUND',
                'message': 'OTP has expired or is invalid. Please request a new one.',
                'attempts_remaining': 0
            }

        # Step 2: Verify hash
        is_correct = verify_otp_hash(entered_otp, otp_doc['otp_hash'])

        if not is_correct:
            # Increment failed attempt counter
            self.otp_model.increment_attempts(otp_doc['_id'])
            new_attempts = otp_doc['attempts'] + 1
            remaining = otp_doc['max_attempts'] - new_attempts

            if remaining <= 0:
                # OTP exhausted — log and return
                self.audit_model.log(
                    identifier=identifier,
                    action=AuditAction.OTP_EXHAUSTED,
                    channel=channel,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    user_id=user_id,
                    details={'attempts': new_attempts}
                )
                return {
                    'success': False,
                    'error_code': 'OTP_EXHAUSTED',
                    'message': 'Too many incorrect attempts. Please request a new OTP.',
                    'attempts_remaining': 0
                }

            # Still has attempts remaining
            self.audit_model.log(
                identifier=identifier,
                action=AuditAction.OTP_FAILED,
                channel=channel,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=user_id,
                details={'attempts': new_attempts, 'remaining': remaining}
            )
            return {
                'success': False,
                'error_code': 'OTP_INVALID',
                'message': f'Incorrect OTP. {remaining} attempt{"s" if remaining > 1 else ""} remaining.',
                'attempts_remaining': remaining
            }

        # Step 3: OTP is CORRECT — mark as used (prevent replay attacks)
        self.otp_model.mark_as_used(otp_doc['_id'])

        self.audit_model.log(
            identifier=identifier,
            action=AuditAction.OTP_VERIFIED,
            channel=channel,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            details={'purpose': purpose}
        )

        return {
            'success': True,
            'error_code': None,
            'message': f'{channel.title()} verified successfully!',
            'attempts_remaining': None
        }

    def get_expiry_seconds(self, channel):
        """Return expiry duration in seconds for frontend countdown timer"""
        return 600 if channel == 'email' else 300  # 10 min or 5 min
