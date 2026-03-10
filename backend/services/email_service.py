"""
Email Service
=============
Sends OTP emails via Gmail SMTP using a professional HTML template.

SETUP REQUIRED (read before viva!):
1. Enable 2-Step Verification on your Gmail account
2. Go to: Google Account → Security → 2-Step Verification → App passwords
3. Create an App Password for "Mail" on "Windows Computer"
4. Copy the 16-character password to your .env file as EMAIL_APP_PASSWORD

WHY app password and not regular password?
- Gmail blocks "less secure apps" by default since May 2022
- App passwords bypass this for SMTP usage
- They can be revoked independently without changing your main password

WHY SMTP over Gmail API?
- SMTP requires zero OAuth setup for sending
- Gmail API requires complex OAuth credentials
- For a BTech project, SMTP is simpler and equally effective
- Industry uses dedicated services (SendGrid, Mailgun) but SMTP is fine for demos

SMTP Technical Details:
- Server: smtp.gmail.com
- Port 465: SMTP over SSL (secure from the start)
- Port 587: STARTTLS (starts plain, upgrades to SSL)
- We use 465+SSL (more straightforward configuration)
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def _is_configured(val):
    """Return True only if the value is a real credential, not a placeholder."""
    if not val:
        return False
    placeholders = {'your-gmail@gmail.com', 'xxxx-xxxx-xxxx-xxxx', 'your_email@gmail.com',
                    'your-email@gmail.com', 'placeholder', 'change_me', 'changeme'}
    if val.strip().lower() in placeholders:
        return False
    if val.startswith('xxxx') or 'xxxx-xxxx' in val:
        return False
    return True


def get_email_config():
    """Load email configuration from environment variables"""
    return {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 465,               # SSL port
        'email_user': os.getenv('EMAIL_USER'),
        'email_password': os.getenv('EMAIL_APP_PASSWORD'),  # 16-char app password
    }


def build_otp_email_html(otp, user_name, channel_label, expiry_minutes, purpose):
    """
    Build a professional HTML email template.

    Design principles:
    - Large, clear OTP display (easy to read on mobile)
    - Security warning (don't share OTP)
    - Expiry time (creates urgency, reduces window for attack)
    - Project branding (professional impression)
    - Table-based layout (best email client compatibility)
    """
    purpose_title = "Verify Your Email" if purpose == "registration" else "Login OTP"
    action_text = "complete your registration" if purpose == "registration" else "log in to your account"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTP - Data Integrity Platform</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f7f9;font-family:'Segoe UI',Arial,sans-serif;">

    <!-- Wrapper -->
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7f9;padding:40px 0;">
        <tr>
            <td align="center">

                <!-- Card -->
                <table width="560" cellpadding="0" cellspacing="0"
                       style="background:#ffffff;border-radius:12px;
                              box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">

                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
                                   padding:36px 40px;text-align:center;">
                            <h1 style="margin:0;color:#e94560;font-size:22px;font-weight:700;
                                       letter-spacing:1px;">
                                🔐 Data Integrity Platform
                            </h1>
                            <p style="margin:8px 0 0;color:#a0a8c0;font-size:14px;">
                                BTech CSE Final Year Project
                            </p>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding:40px;">

                            <!-- Greeting -->
                            <p style="margin:0 0 8px;color:#2d3748;font-size:16px;">
                                Hello {user_name or 'there'},
                            </p>
                            <p style="margin:0 0 28px;color:#4a5568;font-size:15px;line-height:1.6;">
                                Please use the following OTP to {action_text}.
                                This code is valid for <strong>{expiry_minutes} minutes</strong>.
                            </p>

                            <!-- OTP Box -->
                            <table width="100%" cellpadding="0" cellspacing="0"
                                   style="margin-bottom:28px;">
                                <tr>
                                    <td align="center" style="background:#f8f9ff;
                                                              border:2px dashed #4299e1;
                                                              border-radius:12px;
                                                              padding:28px;">
                                        <p style="margin:0 0 8px;color:#718096;
                                                  font-size:12px;text-transform:uppercase;
                                                  letter-spacing:2px;font-weight:600;">
                                            Your OTP Code
                                        </p>
                                        <p style="margin:0;color:#1a1a2e;font-size:42px;
                                                  font-weight:800;letter-spacing:12px;
                                                  font-family:'Courier New',monospace;">
                                            {otp}
                                        </p>
                                        <p style="margin:10px 0 0;color:#e53e3e;
                                                  font-size:13px;font-weight:500;">
                                            ⏱ Expires in {expiry_minutes} minutes
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Security Notice -->
                            <table width="100%" cellpadding="0" cellspacing="0"
                                   style="margin-bottom:24px;">
                                <tr>
                                    <td style="background:#fff5f5;border-left:4px solid #fc8181;
                                               padding:14px 16px;border-radius:0 8px 8px 0;">
                                        <p style="margin:0;color:#c53030;font-size:13px;
                                                  line-height:1.5;">
                                            <strong>⚠ Security Warning:</strong> Never share this OTP with anyone.
                                            Our team will NEVER ask for your OTP. If you didn't request this,
                                            please ignore this email and your account remains safe.
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin:0;color:#718096;font-size:14px;line-height:1.6;">
                                If you're having trouble, contact us at
                                <a href="mailto:{os.getenv('EMAIL_USER', 'support@example.com')}"
                                   style="color:#4299e1;">{os.getenv('EMAIL_USER', 'support@example.com')}</a>
                            </p>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background:#f8f9fa;padding:20px 40px;
                                   border-top:1px solid #e2e8f0;text-align:center;">
                            <p style="margin:0;color:#a0aec0;font-size:12px;">
                                © 2026 Data Integrity Platform | BTech CSE Project<br>
                                This is an automated message — please do not reply.
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

</body>
</html>
"""


def send_email_otp(to_email, otp, user_name=None, expiry_minutes=10,
                   purpose='registration'):
    """
    Send OTP email via Gmail SMTP.

    Parameters:
        to_email       : Recipient email address
        otp            : Raw 6-digit OTP string
        user_name      : User's name for personalization (optional)
        expiry_minutes : How long OTP is valid (10 for email)
        purpose        : "registration" or "login" (affects email subject/text)

    Returns:
        tuple: (success: bool, message: str)

    DEVELOPMENT MODE:
    If EMAIL_USER or EMAIL_APP_PASSWORD not set in .env,
    the OTP is printed to console instead. This allows testing
    without any email configuration.
    """
    config = get_email_config()

    # ── Development Fallback ──────────────────────────────────────────────────
    if not _is_configured(config['email_user']) or not _is_configured(config['email_password']):
        print(f"\n{'='*60}")
        print(f"📧 EMAIL OTP (Development Mode — No SMTP Config)")
        print(f"{'='*60}")
        print(f"  To      : {to_email}")
        print(f"  OTP     : {otp}")
        print(f"  Purpose : {purpose}")
        print(f"  Expires : {expiry_minutes} minutes")
        print(f"{'='*60}\n")
        return True, "OTP printed to console (development mode)"

    # ── Real Email Sending ────────────────────────────────────────────────────
    try:
        # Build email message
        msg = MIMEMultipart('alternative')  # 'alternative' = plain + HTML versions
        msg['Subject'] = (
            f"{'Registration' if purpose == 'registration' else 'Login'} OTP - "
            f"Data Integrity Platform"
        )
        msg['From'] = f"Data Integrity Platform <{config['email_user']}>"
        msg['To'] = to_email

        # Plaintext fallback (for email clients that don't render HTML)
        plain_text = (
            f"Your OTP for Data Integrity Platform: {otp}\n"
            f"Valid for {expiry_minutes} minutes.\n"
            f"Do NOT share this OTP with anyone."
        )

        # HTML version
        html_content = build_otp_email_html(
            otp=otp,
            user_name=user_name,
            channel_label='Email',
            expiry_minutes=expiry_minutes,
            purpose=purpose
        )

        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        # Send via Gmail SMTP with SSL
        # WHY smtplib.SMTP_SSL and not smtplib.SMTP?
        # SMTP_SSL: connects with SSL from the start (port 465) — always encrypted
        # SMTP + starttls: starts plain then upgrades — extra handshake step
        with smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port']) as server:
            server.login(config['email_user'], config['email_password'])
            server.sendmail(
                config['email_user'],
                to_email,
                msg.as_string()
            )

        print(f"✅ Email OTP sent to {to_email}")
        return True, "Email sent successfully"

    except smtplib.SMTPAuthenticationError:
        # Fall back to console so the user can still test the OTP flow
        error_msg = (
            "Email authentication failed — using console fallback.\n"
            "To fix: set EMAIL_USER and EMAIL_APP_PASSWORD in backend/.env\n"
            "(Enable Gmail 2FA → Security → App passwords → generate 16-char code)"
        )
        print(f"\n⚠️  {error_msg}")
        print(f"\n{'='*60}")
        print(f"📧 EMAIL OTP (Console Fallback — Auth Failed)")
        print(f"{'='*60}")
        print(f"  To      : {to_email}")
        print(f"  OTP     : {otp}")
        print(f"  Purpose : {purpose}")
        print(f"  Expires : {expiry_minutes} minutes")
        print(f"{'='*60}\n")
        return True, "OTP printed to console (email auth failed — see server logs)"

    except smtplib.SMTPException as e:
        error_msg = f"SMTP error: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Email sending failed: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
