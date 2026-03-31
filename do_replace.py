import io

def main():
    try:
        with open('profile.html', 'r', encoding='utf-8') as f:
            text = f.read()

        start_tag = '<main class="dashboard-main">'
        end_tag = '</main>'
        
        start_idx = text.find(start_tag)
        end_idx = text.find(end_tag, start_idx)
        
        if start_idx == -1 or end_idx == -1:
            print("Tags not found!")
            return
            
        end_idx += len(end_tag)

        new_styles = '''
        /* Udemy Style Overrides */
        body, .dashboard-body { background-color: #f7f8fa !important; }
        .dashboard-main { padding: 0 !important; background: transparent !important; }
        
        .udemy-layout {
            display: flex;
            flex-direction: column;
            gap: 2rem;
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        @media (min-width: 900px) {
            .udemy-layout { flex-direction: row; align-items: flex-start; }
            .udemy-sidebar { flex: 0 0 280px; position: sticky; top: 100px; }
            .udemy-content { flex: 1 1 auto; min-width: 0; }
        }
        
        .avatar-card-ud {
            background: #fff;
            padding: 24px;
            text-align: center;
            border: 1px solid #d1d5db;
        }
        .avatar-circle-ud {
            width: 96px; height: 96px;
            border-radius: 50%;
            background: #1c1d1f; color: #fff;
            display: flex; align-items: center; justify-content: center;
            font-size: 32px; font-weight: 700;
            margin: 0 auto 16px auto;
        }
        .avatar-name-ud { font-weight: 700; font-size: 19px; color: #1c1d1f; margin-bottom: 4px; }
        .avatar-role-ud { font-size: 13px; color: #6b7280; margin-bottom: 16px; }
        
        .sidebar-menu-ud {
            list-style: none; padding: 0; margin: 0;
            background: #fff;
            border: 1px solid #d1d5db;
            border-top: none;
        }
        .sidebar-menu-ud li { margin: 0; border-bottom: 1px solid #d1d5db;}
        .sidebar-menu-ud li:last-child { border-bottom: none; }
        
        .sidebar-menu-ud a {
            display: block; padding: 16px 20px;
            color: #1c1d1f; text-decoration: none;
            font-weight: 500; font-size: 15px;
            transition: background 0.2s, color 0.2s;
            cursor: pointer;
            border-left: 4px solid transparent;
        }
        .sidebar-menu-ud a:hover { background: #f3f4f6; }
        .sidebar-menu-ud a.active { background: #f3f4f6; border-left-color: #5022c3; font-weight: 700; }
        
        .content-header-ud { margin-bottom: 32px; text-align: left; border-bottom: 1px solid #d1d5db; padding-bottom: 24px;}
        .content-title-ud { font-size: 32px; font-weight: 700; color: #1c1d1f; margin-bottom: 8px; margin-top:0; }
        .content-subtitle-ud { color: #1c1d1f; font-size: 16px; margin:0; }
        
        .udemy-card {
            background: #ffffff;
            margin-bottom: 32px;
            border: 1px solid #d1d5db;
            scroll-margin-top: 100px;
        }
        .udemy-card-header { border-bottom: 1px solid #d1d5db; padding: 24px; background: #fff;}
        .udemy-card-title { font-size: 20px; font-weight: 700; color: #1c1d1f; margin: 0 0 8px 0; }
        .udemy-card-subtitle { font-size: 15px; color: #6b7280; margin:0;}
        .udemy-card-body { padding: 24px; background: #fff; }
        
        .form-group-ud { margin-bottom: 24px; }
        .form-label-ud { display: block; font-weight: 700; font-size: 15px; margin-bottom: 8px; color: #1c1d1f; }
        .form-input-ud {
            width: 100%; padding: 14px 16px;
            border: 1px solid #1c1d1f;
            border-radius: 0;
            font-size: 15px;
            color: #1c1d1f;
            transition: background 0.2s;
            font-family: inherit;
            box-sizing: border-box;
            background: #fff;
        }
        .form-input-ud:focus {
            outline: none; background: #fff; border-color: #5022c3; box-shadow: 0 0 0 2px rgba(80,34,195,0.15);
        }
        .form-input-ud:disabled, .form-input-ud[readonly] { background-color: #f3f4f6; color: #6b7280; cursor: not-allowed; border-color: #d1d5db; }
        .form-hint-ud { display: block; font-size: 13px; color: #6b7280; margin-top: 8px; }
        .required-star { color: #dc2626; }
        
        .save-btn-container-ud { text-align: left; padding: 24px 0 40px 0; border-top: 1px solid #d1d5db; margin-top: 32px; }
        .udemy-save-btn {
            background: #1c1d1f; color: white;
            border: none; padding: 16px 24px;
            font-size: 16px; font-weight: 700;
            cursor: pointer;
            display: inline-flex; align-items: center; justify-content: center; gap: 8px;
            min-width: 160px;
            transition: background 0.2s;
        }
        .udemy-save-btn:hover { background: #000; }
        .udemy-save-btn:disabled { opacity: 0.7; cursor: not-allowed; }
        
        .message-box { padding: 16px; border-radius: 4px; margin-bottom: 24px; font-weight: 700; font-size: 15px; display:none; }
        .message-success { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
        .message-error { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }

        .udemy-verify-card {
            border: 1px solid #d1d5db; padding: 24px; margin-bottom: 24px; background: #fff;
        }
        .udemy-verify-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; }
        .udemy-verify-icon { font-size: 24px; margin-right: 16px; color: #1c1d1f; }
        .udemy-verify-title-group { display: flex; align-items: flex-start; }
        .udemy-verify-title { font-weight: 700; color: #1c1d1f; font-size: 18px; margin: 0 0 4px 0; }
        
        .udemy-badge { font-size: 12px; font-weight: 700; padding: 6px 12px; border-radius: 4px; letter-spacing: 0.5px; }
        .udemy-badge-pending { background: #fef08a; color: #854d0e; }
        .udemy-badge-verified { background: #dcfce7; color: #166534; }
        
        .udemy-btn-secondary { background: transparent; color: #1c1d1f; border: 1px solid #1c1d1f; padding: 12px 20px; font-size: 15px; font-weight: 700; cursor: pointer; transition: background 0.2s;}
        .udemy-btn-secondary:hover { background: rgba(0,0,0,0.05); }
        .udemy-btn-primary { background: #5022c3; color: white; border: none; padding: 12px 20px; font-size: 15px; font-weight: 700; cursor: pointer; transition: background 0.2s;}
        .udemy-btn-primary:hover { background: #3e1b99; }
        
        .email-verified-badge {
            display: none; align-items: center; justify-content: flex-start;
            color: #16a34a; font-weight: 700; font-size: 14px; margin-top: 8px;
        }
        .email-verified-badge svg { width: 18px; height: 18px; margin-right: 6px; }

        .otp-inputs { display: flex; gap: 10px; margin: 16px 0; }
        .otp-digit {
            width: 50px; height: 60px;
            border: 1px solid #1c1d1f;
            text-align: center;
            font-size: 24px; font-weight: 700;
            outline: none;
            background: #fff;
        }
        .otp-digit:focus { border-color: #5022c3; box-shadow: 0 0 0 2px rgba(80,34,195,0.15); }
        
        /* Smooth scrolling */
        html { scroll-behavior: smooth; }
    </style>
'''

        new_main = """<main class="dashboard-main">
        <div class="udemy-layout">
            <!-- Left Sidebar -->
            <aside class="udemy-sidebar">
                <div class="avatar-card-ud">
                    <div class="avatar-circle-ud">AS</div>
                    <div class="avatar-name-ud" id="sidebarAvatarName">My Profile</div>
                    <div class="avatar-role-ud">Data Platform User</div>
                </div>
                <ul class="sidebar-menu-ud">
                    <li><a href="#section-personal" class="sidebar-link active" onclick="activateLink(this)">Profile</a></li>
                    <li><a href="#section-contact" class="sidebar-link" onclick="activateLink(this)">Contact Info</a></li>
                    <li><a href="#section-account" class="sidebar-link" onclick="activateLink(this)">Account Setup</a></li>
                    <li><a href="#section-verification" class="sidebar-link" onclick="activateLink(this)">Security & Identity</a></li>
                </ul>
            </aside>

            <!-- Right Main Content -->
            <div class="udemy-content">
                <div class="content-header-ud">
                    <h1 class="content-title-ud">Public profile</h1>
                    <p class="content-subtitle-ud">Add information about yourself</p>
                </div>

                <!-- Success/Error Message -->
                <div class="message-box" id="messageBox" style="display:none;"></div>

                <form id="profileForm">
                    <!-- Personal Information -->
                    <div class="udemy-card" id="section-personal">
                        <div class="udemy-card-header">
                            <h2 class="udemy-card-title">Basics</h2>
                            <p class="udemy-card-subtitle">Information visible across the platform</p>
                        </div>
                        <div class="udemy-card-body">
                            <div class="form-group-ud">
                                <label for="fullName" class="form-label-ud">Full Name <span class="required-star">*</span></label>
                                <input type="text" id="fullName" name="fullName" class="form-input-ud" required maxlength="60">
                            </div>
                            <div class="form-group-ud">
                                <label for="email" class="form-label-ud">Email Address <span class="required-star">*</span></label>
                                <input type="email" id="email" name="email" class="form-input-ud" required>
                                <div class="email-verified-badge" id="emailFieldVerifiedBadge">
                                    <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                                    Email verified successfully.
                                </div>
                            </div>
                            <div class="form-group-ud">
                                <label for="dateOfBirth" class="form-label-ud">Date of Birth</label>
                                <input type="date" id="dateOfBirth" name="dateOfBirth" class="form-input-ud">
                            </div>
                        </div>
                    </div>

                    <!-- Contact Details -->
                    <div class="udemy-card" id="section-contact">
                        <div class="udemy-card-header">
                            <h2 class="udemy-card-title">Contact Information</h2>
                            <p class="udemy-card-subtitle">Help us reach out for important notifications</p>
                        </div>
                        <div class="udemy-card-body">
                            <div class="form-group-ud">
                                <label for="phoneNumber" class="form-label-ud">Phone Number</label>
                                <input type="tel" id="phoneNumber" name="phoneNumber" class="form-input-ud" placeholder="+91 XXXXX XXXXX">
                            </div>
                        </div>
                    </div>

                    <!-- System Information -->
                    <div class="udemy-card" id="section-account">
                        <div class="udemy-card-header">
                            <h2 class="udemy-card-title">System Info</h2>
                            <p class="udemy-card-subtitle">Automated records attached to your profile</p>
                        </div>
                        <div class="udemy-card-body">
                            <div style="display:flex;gap:20px;">
                                <div style="flex:1;">
                                    <label class="form-label-ud">Member Since</label>
                                    <input type="text" id="memberSince" class="form-input-ud" readonly>
                                </div>
                                <div style="flex:1;">
                                    <label class="form-label-ud">Last Login</label>
                                    <input type="text" id="lastLogin" class="form-input-ud" readonly>
                                </div>
                            </div>
                            <div class="form-group-ud" style="margin-top:24px;">
                                <label class="form-label-ud">Google Connect</label>
                                <input type="text" id="googleId" class="form-input-ud" readonly placeholder="Not connected via Google">
                            </div>
                        </div>
                    </div>

                    <!-- Security & Identity -->
                    <div class="udemy-card" id="section-verification" style="border:none;background:transparent;padding:0;margin-bottom:0;">
                        <h2 style="font-size:24px;font-weight:700;color:#1c1d1f;margin:0 0 8px 0;">Identity Verification</h2>
                        <p style="font-size:16px;color:#1c1d1f;margin:0 0 24px 0;">Add a layer of security to your data integrity profile</p>

                        <!-- Email Verification -->
                        <div class="udemy-verify-card">
                            <div class="udemy-verify-header">
                                <div class="udemy-verify-title-group">
                                    <span class="udemy-verify-icon">✉️</span>
                                    <div>
                                        <p class="udemy-verify-title">Email Verification</p>
                                        <p class="udemy-card-subtitle" id="emailVerifyHint">Send an OTP to verify your email address</p>
                                    </div>
                                </div>
                                <span id="emailVerifyBadge" class="udemy-badge udemy-badge-pending">PENDING</span>
                            </div>
                            <div id="emailSendStep">
                                <button type="button" onclick="sendOtp('email')" id="sendEmailOtpBtn" class="udemy-btn-secondary">Send Verification Code</button>
                            </div>
                            <div id="emailVerifyStep" style="display:none; margin-top:20px;">
                                <p style="font-size:15px;color:#1c1d1f;font-weight:700;margin-bottom:12px;">Enter 6-digit code</p>
                                <div id="emailOtpDigitRow" class="otp-inputs">
                                    <input class="otp-digit" data-channel="email" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="email" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="email" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="email" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="email" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="email" type="text" maxlength="1" inputmode="numeric">
                                </div>
                                <div id="emailOtpError" class="otp-inline-error"></div>
                                <div id="emailOtpSuccess" class="otp-inline-success"></div>
                                <div style="display:flex;gap:16px;align-items:center; margin-top: 10px;">
                                    <button type="button" onclick="verifyOtp('email')" id="verifyEmailOtpBtn" class="udemy-btn-primary">Verify</button>
                                    <button type="button" onclick="resetOtpStep('email')" style="background:none;border:none;color:#5022c3;font-size:15px;cursor:pointer;font-weight:700;">Resend Code</button>
                                </div>
                            </div>
                        </div>

                        <!-- Phone Verification -->
                        <div class="udemy-verify-card" style="margin-bottom:0;">
                            <div class="udemy-verify-header">
                                <div class="udemy-verify-title-group">
                                    <span class="udemy-verify-icon">📱</span>
                                    <div>
                                        <p class="udemy-verify-title">Phone Verification</p>
                                        <p class="udemy-card-subtitle" id="phoneVerifyHint">Send an OTP to verify your phone number</p>
                                    </div>
                                </div>
                                <span id="phoneVerifyBadge" class="udemy-badge udemy-badge-pending">PENDING</span>
                            </div>
                            <div id="phoneSendStep">
                                <button type="button" onclick="sendOtp('phone')" id="sendPhoneOtpBtn" class="udemy-btn-secondary">Send Verification Code</button>
                            </div>
                            <div id="phoneVerifyStep" style="display:none; margin-top:20px;">
                                <p style="font-size:15px;color:#1c1d1f;font-weight:700;margin-bottom:12px;">Enter 6-digit code</p>
                                <div id="phoneOtpDigitRow" class="otp-inputs">
                                    <input class="otp-digit" data-channel="phone" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="phone" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="phone" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="phone" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="phone" type="text" maxlength="1" inputmode="numeric">
                                    <input class="otp-digit" data-channel="phone" type="text" maxlength="1" inputmode="numeric">
                                </div>
                                <div id="phoneOtpError" class="otp-inline-error"></div>
                                <div id="phoneOtpSuccess" class="otp-inline-success"></div>
                                <div style="display:flex;gap:16px;align-items:center; margin-top: 10px;">
                                    <button type="button" onclick="verifyOtp('phone')" id="verifyPhoneOtpBtn" class="udemy-btn-primary">Verify</button>
                                    <button type="button" onclick="resetOtpStep('phone')" style="background:none;border:none;color:#5022c3;font-size:15px;cursor:pointer;font-weight:700;">Resend Code</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Submit -->
                    <div class="save-btn-container-ud">
                        <button type="submit" class="udemy-save-btn" id="saveBtn">
                            <span id="saveBtnText">Save Settings</span>
                            <span id="saveBtnLoader" style="display:none;"><i class="fas fa-spinner fa-spin"></i></span>
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </main>
    <script>
        function activateLink(element) {
            document.querySelectorAll('.sidebar-link').forEach(link => link.classList.remove('active'));
            element.classList.add('active');
        }
        
        const uiFullName = document.getElementById('fullName');
        if(uiFullName) {
            uiFullName.addEventListener('input', function(e) {
                const val = (e.target.value || '').trim() || 'User Profile';
                const sidebarAvatarName = document.getElementById('sidebarAvatarName');
                if(sidebarAvatarName) sidebarAvatarName.textContent = val;
                
                const nameParts = val.split(' ');
                let initials = 'U';
                if (nameParts.length > 0 && nameParts[0].length > 0) {
                    initials = nameParts[0].charAt(0).toUpperCase();
                }
                if(nameParts.length > 1 && nameParts[nameParts.length - 1].length > 0) {
                    initials += nameParts[nameParts.length - 1].charAt(0).toUpperCase();
                }
                const avatarCircle = document.querySelector('.avatar-circle-ud');
                if(avatarCircle) avatarCircle.textContent = initials;
            });
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                if(uiFullName) {
                    const evt = new Event('input', { bubbles: true });
                    uiFullName.dispatchEvent(evt);
                }
            }, 600);
        });
    </script>
"""

        new_text = text[:start_idx] + new_main + text[end_idx:]

        if "    </style>" in new_text:
            new_text = new_text.replace("    </style>", new_styles)
        else:
            print("Warning: </style> not found")

        with open('profile.html', 'w', encoding='utf-8') as f:
            f.write(new_text)

        print("SUCCESSFULLY REPLACED HTML")

    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    main()