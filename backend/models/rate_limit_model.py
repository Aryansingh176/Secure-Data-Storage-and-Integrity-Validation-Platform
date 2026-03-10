"""
Rate Limit Model - Collection: rate_limits
==========================================
Implements sliding-window rate limiting in MongoDB.

WHY THREE-LAYER RATE LIMITING:
1. Per-OTP attempt: After 3 wrong OTPs → that OTP is dead
2. Per-channel send: After 3 OTP sends in 15 min → channel blocked
3. Account lockout: After 5 total failures in 24h → account locked

This model handles Layer 2 (channel request limiting).
Layers 1 & 3 are handled in the OTPModel and UserModel respectively.

HOW SLIDING WINDOW WORKS:
- Each identifier+request_type has a count + window_start
- If (now - window_start) > window_duration → reset window
- If count >= limit within window → blocked
- This is "fixed window" (simpler than true sliding window, good enough for BTech project)
"""

from datetime import datetime, timedelta
from bson import ObjectId


class RateLimitModel:
    """Handles rate limiting records in MongoDB"""

    def __init__(self, db):
        """Initialize with database, create indexes"""
        self.collection = db['rate_limits']

        # Fast lookup by identifier + request type
        self.collection.create_index([
            ('identifier', 1),
            ('request_type', 1)
        ], unique=True)

        # Auto-delete expired rate limit records (TTL index)
        self.collection.create_index('expires_at', expireAfterSeconds=0)

    def check_and_increment(self, identifier, request_type, limit=3, window_minutes=15):
        """
        Core rate limiting logic — check + increment atomically.

        ALGORITHM:
        1. Find existing rate limit record for this identifier+type
        2. If record is outside the time window → reset it (new window)
        3. If count >= limit → request is BLOCKED
        4. Otherwise → increment count, REQUEST ALLOWED

        Parameters:
            identifier    : email or phone number being rate-limited
            request_type  : "otp_send_email", "otp_send_phone", "otp_verify"
            limit         : max requests allowed in window (default: 3)
            window_minutes: length of time window (default: 15 min)

        Returns:
            dict with keys:
              - allowed (bool): whether to proceed
              - count (int): current request count
              - remaining (int): requests left in window
              - reset_at (datetime): when the window resets
        """
        now = datetime.utcnow()
        window_start = now
        reset_at = now + timedelta(minutes=window_minutes)

        # Try to find existing record
        existing = self.collection.find_one({
            'identifier': identifier,
            'request_type': request_type
        })

        if existing:
            # Check if the window has expired (time elapsed > window duration)
            window_elapsed = (now - existing['window_start']).total_seconds() / 60
            if window_elapsed > window_minutes:
                # Window expired — reset with fresh count of 1
                self.collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {
                        'count': 1,
                        'window_start': now,
                        'expires_at': reset_at
                    }}
                )
                return {
                    'allowed': True,
                    'count': 1,
                    'remaining': limit - 1,
                    'reset_at': reset_at
                }
            else:
                # Within same window — check against limit
                current_count = existing['count']
                if current_count >= limit:
                    # BLOCKED: too many requests in this window
                    time_until_reset = window_minutes - window_elapsed
                    actual_reset = existing['window_start'] + timedelta(minutes=window_minutes)
                    return {
                        'allowed': False,
                        'count': current_count,
                        'remaining': 0,
                        'reset_at': actual_reset,
                        'minutes_remaining': round(time_until_reset, 1)
                    }
                else:
                    # ALLOWED: increment count
                    self.collection.update_one(
                        {'_id': existing['_id']},
                        {'$inc': {'count': 1}}
                    )
                    return {
                        'allowed': True,
                        'count': current_count + 1,
                        'remaining': limit - (current_count + 1),
                        'reset_at': existing['window_start'] + timedelta(minutes=window_minutes)
                    }
        else:
            # First request ever — create new rate limit record
            self.collection.insert_one({
                'identifier': identifier,
                'request_type': request_type,
                'count': 1,
                'window_start': now,
                'window_duration_minutes': window_minutes,
                'expires_at': reset_at
            })
            return {
                'allowed': True,
                'count': 1,
                'remaining': limit - 1,
                'reset_at': reset_at
            }

    def get_status(self, identifier, request_type, limit=3, window_minutes=15):
        """
        Get rate limit status without incrementing.
        Used to show cooldown information to the user.
        """
        existing = self.collection.find_one({
            'identifier': identifier,
            'request_type': request_type
        })

        if not existing:
            return {'count': 0, 'remaining': limit, 'blocked': False}

        now = datetime.utcnow()
        window_elapsed = (now - existing['window_start']).total_seconds() / 60

        if window_elapsed > window_minutes:
            return {'count': 0, 'remaining': limit, 'blocked': False}

        count = existing['count']
        return {
            'count': count,
            'remaining': max(0, limit - count),
            'blocked': count >= limit,
            'reset_at': existing['window_start'] + timedelta(minutes=window_minutes)
        }

    def reset(self, identifier, request_type):
        """
        Manually reset rate limit for an identifier.
        Used by admin or after successful verification.
        """
        self.collection.delete_one({
            'identifier': identifier,
            'request_type': request_type
        })
