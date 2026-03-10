"""
SMS Service
============
Sends OTP via SMS using Twilio, with console fallback for development.

TWILIO SETUP (for production/demo):
1. Sign up at https://twilio.com (free trial — $15 credit)
2. Get Account SID and Auth Token from Console Dashboard
3. Buy a phone number (or use Trial number)
4. Add credentials to .env file

TWILIO TRIAL LIMITATIONS:
- SMS can only be sent to VERIFIED numbers (add in Twilio Console)
- Messages start with "Sent from your Twilio trial account"
- $15 credit ≈ 2000 SMS messages

DEVELOPMENT MODE (default):
- If TWILIO credentials not set, OTP prints to console
- Perfect for demos and local testing
- Zero cost, zero setup required

E.164 Phone Format (important for Twilio!):
- India: +91XXXXXXXXXX (10 digits after +91)
- US: +1XXXXXXXXXX
- Always include country code
- No spaces, dashes, or brackets
- Validated in auth routes before calling this service

COST ANALYSIS (good viva point!):
- Twilio rate India: ~$0.0075 USD per SMS
- In INR: ~₹0.60 per SMS
- 1000 users: ~₹600 total
- Acceptable for a production platform
"""

import os


def get_twilio_config():
    """Load Twilio configuration from environment variables"""
    return {
        'account_sid': os.getenv('TWILIO_ACCOUNT_SID'),
        'auth_token': os.getenv('TWILIO_AUTH_TOKEN'),
        'phone_number': os.getenv('TWILIO_PHONE_NUMBER'),
    }


def send_sms_otp(to_phone, otp, expiry_minutes=5, purpose='registration'):
    """
    Send OTP via Twilio SMS.

    Parameters:
        to_phone       : Recipient phone in E.164 format (+91XXXXXXXXXX)
        otp            : Raw 6-digit OTP string
        expiry_minutes : OTP validity (5 min for phone — SMS is instant)
        purpose        : "registration" or "login"

    Returns:
        tuple: (success: bool, message: str)

    FLOW:
    1. Check if Twilio credentials exist in .env
    2. If yes → try Twilio → return result
    3. If no (or Twilio error) → print to console (development fallback)
    4. Development fallback always returns True (simulate success)

    WHY fallback returns True:
    - In development, we want to test the verification flow
    - Console shows the OTP so dev can copy-paste it
    - Doesn't break the flow when Twilio isn't configured
    """
    config = get_twilio_config()

    # ── Development Fallback ──────────────────────────────────────────────────
    if not config['account_sid'] or not config['auth_token'] or not config['phone_number']:
        _print_console_otp(to_phone, otp, expiry_minutes, purpose)
        return True, "OTP printed to console (development mode — Twilio not configured)"

    # ── Real SMS Sending via Twilio ───────────────────────────────────────────
    try:
        from twilio.rest import Client

        # Build professional SMS message
        purpose_text = "Registration" if purpose == 'registration' else "Login"
        message_body = (
            f"[Data Integrity Platform] {purpose_text} OTP: {otp}\n"
            f"Valid for {expiry_minutes} minutes. Do NOT share this code.\n"
            f"If you didn't request this, ignore this message."
        )

        client = Client(config['account_sid'], config['auth_token'])

        message = client.messages.create(
            body=message_body,
            from_=config['phone_number'],   # Your Twilio number
            to=to_phone                      # Recipient (E.164 format)
        )

        print(f"✅ SMS OTP sent to {to_phone[:6]}****{to_phone[-2:]} | SID: {message.sid}")
        return True, "SMS sent successfully"

    except ImportError:
        # twilio package not installed — use console fallback
        print("⚠  twilio package not installed. Using console fallback.")
        print("   Install it: pip install twilio")
        _print_console_otp(to_phone, otp, expiry_minutes, purpose)
        return True, "OTP printed to console (twilio not installed)"

    except Exception as e:
        # Twilio error (bad credentials, unverified number, etc.)
        error_str = str(e)
        print(f"❌ Twilio SMS error: {error_str}")

        # Common errors and how to fix them:
        if '21211' in error_str:
            print("   → Invalid 'To' phone number. Use E.164 format: +91XXXXXXXXXX")
        elif '21608' in error_str:
            print("   → Phone number not verified. Add it in Twilio Console (trial accounts).")
        elif '20003' in error_str:
            print("   → Invalid Twilio credentials. Check TWILIO_ACCOUNT_SID and AUTH_TOKEN.")

        # Fall back to console so development continues
        print("\n📱 Falling back to console output:")
        _print_console_otp(to_phone, otp, expiry_minutes, purpose)

        # Return True with a note so registration/login can continue in dev
        return True, f"SMS failed ({error_str}), OTP printed to console"


def _print_console_otp(to_phone, otp, expiry_minutes, purpose):
    """
    Print OTP to console for development/testing.
    Used when Twilio is not configured or fails.
    """
    print(f"\n{'='*60}")
    print(f"📱 SMS OTP (Development / Console Mode)")
    print(f"{'='*60}")
    print(f"  To      : {to_phone}")
    print(f"  OTP     : {otp}")
    print(f"  Purpose : {purpose}")
    print(f"  Expires : {expiry_minutes} minutes")
    print(f"{'='*60}")
    print(f"  ↑ Use this OTP to complete verification")
    print(f"{'='*60}\n")


def validate_phone_e164(phone):
    """
    Validate phone number is in E.164 format.

    E.164 format: + followed by 7-15 digits
    Examples:
      ✓ +919876543210 (India)
      ✓ +14155551234  (US)
      ✗ 9876543210   (missing + and country code)
      ✗ +91 98765 43210 (spaces not allowed in E.164)

    Returns: (is_valid: bool, normalized: str or None)
    """
    import re
    # Remove spaces and dashes (user-friendly cleanup)
    cleaned = phone.replace(' ', '').replace('-', '')

    if re.match(r'^\+[1-9]\d{6,14}$', cleaned):
        return True, cleaned

    # Try adding India country code if 10-digit number provided
    if re.match(r'^[6-9]\d{9}$', cleaned):
        # 10-digit Indian mobile (starts with 6,7,8,9)
        return True, f'+91{cleaned}'

    return False, None
