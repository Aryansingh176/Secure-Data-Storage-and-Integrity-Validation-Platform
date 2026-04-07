"""
User Model - Collection: users
================================
Extended user schema supporting OTP-based multi-channel authentication.

Schema Design Decisions (Good viva points!):
- email_verified / phone_verified: Track each channel independently
  → Allows partial verification (email done, phone pending)
- failed_attempts_today: Reset at midnight, triggers account lockout
- locked_until: None means not locked; a datetime means locked until then
- registration_completed: True only when BOTH email + phone are verified
  → Ensures complete identity verification before granting full access
"""

from datetime import datetime
from bson import ObjectId


class User:
    """User model for OTP-based multi-channel authentication"""

    def __init__(self, db):
        """Initialize with database, create indexes"""
        self.collection = db['users']
        # Unique constraint on email (sparse allows null values)
        try:
            self.collection.create_index('email', unique=True)
        except Exception:
            pass  # Index already exists with compatible options
        # Unique constraint on phone — one account per phone number
        try:
            self.collection.create_index('phone', unique=True, sparse=True)
        except Exception:
            pass  # Index already exists
    
    # ──────────────────────────────────────────────
    # CREATE
    # ──────────────────────────────────────────────

    def create_user(self, email=None, phone=None, name=None,
                    google_id=None, profile_picture=None):
        """
        Create a new user. For OTP registration, email and phone start UNVERIFIED.
        registration_completed becomes True only after both channels verified.
        """
        user_data = {
            'name': name,
            'email': email,
            'google_id': google_id,
            'profile_picture': profile_picture,
            'email_verified': False,
            'phone_verified': False,
            'is_active': True,
            'failed_attempts_today': 0,         # increments on OTP failure
            'locked_until': None,               # None = not locked
            'registration_completed': False,    # True when both channels verified
            'created_at': datetime.utcnow(),
            'last_login': None,
            'date_of_birth': None,
        }
        if phone:
            user_data['phone'] = phone  # E.164 format: +91XXXXXXXXXX
        try:
            result = self.collection.insert_one(user_data)
            user_data['_id'] = result.inserted_id
            return user_data
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    # ──────────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────────

    def find_by_email(self, email):
        """Find user by email address"""
        return self.collection.find_one({'email': email})

    def find_by_phone(self, phone):
        """Find user by phone number (E.164 format)"""
        return self.collection.find_one({'phone': phone})

    def find_by_identifier(self, identifier):
        """Find user by email OR phone — used in login flow"""
        import re
        if re.match(r'^\+?\d{7,15}$', identifier.replace(' ', '')):
            return self.find_by_phone(identifier)
        return self.find_by_email(identifier)

    def find_by_google_id(self, google_id):
        """Find user by Google OAuth ID (legacy support)"""
        return self.collection.find_one({'google_id': google_id})

    def find_by_id(self, user_id):
        """Find user by MongoDB ObjectId"""
        try:
            return self.collection.find_one({'_id': ObjectId(user_id)})
        except Exception as e:
            print(f"Error finding user by ID: {e}")
            return None

    def is_locked(self, user):
        """
        Check if account is locked.
        Returns (is_locked: bool, locked_until: datetime or None)
        Lock auto-expires: if locked_until <= now, clear it.
        """
        if not user.get('locked_until'):
            return False, None
        now = datetime.utcnow()
        if user['locked_until'] > now:
            return True, user['locked_until']
        # Lock expired — clear it
        self.collection.update_one(
            {'_id': user['_id']},
            {'$set': {'locked_until': None, 'failed_attempts_today': 0}}
        )
        return False, None

    # ──────────────────────────────────────────────
    # UPDATE — Verification
    # ──────────────────────────────────────────────

    def mark_email_verified(self, user_id):
        """Mark email verified; auto-completes registration if phone also verified"""
        user = self.find_by_id(user_id)
        if not user:
            return False
        update = {'email_verified': True}
        if user.get('phone_verified'):
            update['registration_completed'] = True
        self.collection.update_one({'_id': ObjectId(user_id)}, {'$set': update})
        return True

    def mark_phone_verified(self, user_id):
        """Mark phone verified; auto-completes registration if email also verified"""
        user = self.find_by_id(user_id)
        if not user:
            return False
        update = {'phone_verified': True}
        if user.get('email_verified'):
            update['registration_completed'] = True
        self.collection.update_one({'_id': ObjectId(user_id)}, {'$set': update})
        return True

    # ──────────────────────────────────────────────
    # UPDATE — Security
    # ──────────────────────────────────────────────

    def increment_failed_attempts(self, user_id):
        """Increment failed OTP counter. Returns new total."""
        result = self.collection.find_one_and_update(
            {'_id': ObjectId(user_id)},
            {'$inc': {'failed_attempts_today': 1}},
            return_document=True
        )
        return result['failed_attempts_today'] if result else 0

    def lock_account(self, user_id, hours=24):
        """Lock account for N hours. Returns the locked_until datetime."""
        from datetime import timedelta
        locked_until = datetime.utcnow() + timedelta(hours=hours)
        self.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'locked_until': locked_until}}
        )
        return locked_until

    def reset_failed_attempts(self, user_id):
        """Reset failure counter after successful login"""
        self.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'failed_attempts_today': 0}}
        )

    def update_last_login(self, user_id=None, email=None):
        """Record last successful login time"""
        if user_id:
            self.collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'last_login': datetime.utcnow()}}
            )
        elif email:
            self.collection.update_one(
                {'email': email},
                {'$set': {'last_login': datetime.utcnow()}}
            )

    def update_user(self, email, update_data):
        """Generic update by email (used by legacy OAuth flow)"""
        update_data['updated_at'] = datetime.utcnow()
        return self.collection.update_one(
            {'email': email},
            {'$set': update_data}
        )

    def update_profile(self, user_id, profile_data):
        """Update whitelisted profile fields"""
        try:
            update_data = {'updated_at': datetime.utcnow()}
            for field in ['name', 'date_of_birth', 'phone']:
                if field in profile_data:
                    update_data[field] = profile_data[field]
            result = self.collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False

    # ──────────────────────────────────────────────
    # SERIALIZATION
    # ──────────────────────────────────────────────

    def serialize_user(self, user):
        """Convert MongoDB doc to JSON-safe dict. Never expose sensitive fields."""
        if not user:
            return None
        profile_completed = bool(
            user.get('name') and
            user.get('phone') and
            user.get('date_of_birth')
        )
        return {
            'id': str(user['_id']),
            'name': user.get('name'),
            'email': user.get('email'),
            'phone': user.get('phone'),
            'profile_picture': user.get('profile_picture'),
            'date_of_birth': str(user['date_of_birth']) if user.get('date_of_birth') else None,
            'email_verified': user.get('email_verified', False),
            'phone_verified': user.get('phone_verified', False),
            'registration_completed': user.get('registration_completed', False),
            'profile_completed': profile_completed,
            'is_active': user.get('is_active', True),
            'created_at': user['created_at'].isoformat() if user.get('created_at') else None,
            'last_login': user['last_login'].isoformat() if user.get('last_login') else None,
            'is_locked': (
                user.get('locked_until') is not None and
                user['locked_until'] > datetime.utcnow()
            )
        }
