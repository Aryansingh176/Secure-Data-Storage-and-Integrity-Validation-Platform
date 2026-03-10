# Google Login Quick Start Guide

## ✅ What's Been Set Up

1. **Login Page** - [login.html](login.html) with Google OAuth button
2. **Backend Authentication** - Complete Google OAuth and JWT authentication
3. **Required Packages** - All Python dependencies installed

## 🚀 Quick Start (5 minutes)

### Step 1: Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Go to **APIs & Services** → **Credentials**
5. Create **OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Authorized JavaScript origins: `http://localhost:5000` and `http://localhost:8000`
   - Authorized redirect URIs: `http://localhost:5000/api/auth/google/callback`
6. Copy the **Client ID** and **Client Secret**

### Step 2: Configure Environment Variables

Open [backend/.env](backend/.env) and update these lines:

```env
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
```

### Step 3: Start the Application

**Terminal 1 - Start MongoDB:**
```bash
mongod
```

**Terminal 2 - Start Backend:**
```bash
cd backend
python app.py
```

**Terminal 3 - Start Frontend (if needed):**
```bash
# If using Python's HTTP server:
python -m http.server 8000

# Or if using VS Code Live Server, just open login.html
```

### Step 4: Test Google Login

1. Open http://localhost:8000/login.html
2. Click "Continue with Google"
3. Sign in with your Google account
4. You'll be redirected to the main page after successful login

## 📁 Files Created/Modified

### New Files:
- `login.html` - Beautiful login page with Google OAuth button
- `backend/routes/auth_routes.py` - Authentication endpoints
- `backend/models/user_model.py` - User database model
- `GOOGLE_OAUTH_SETUP.md` - Detailed setup guide

### Modified Files:
- `backend/app.py` - Added authentication routes
- `backend/requirements.txt` - Added OAuth packages
- `backend/.env` - Added Google OAuth configuration

## 🔐 Authentication Features

### Available Endpoints:

- `GET /api/auth/google/login` - Initiate Google OAuth
- `GET /api/auth/google/callback` - OAuth callback handler
- `POST /api/auth/login` - Email/password login (for later)
- `GET /api/auth/verify` - Verify JWT token
- `GET /api/auth/user/profile` - Get user profile

### How It Works:

1. User clicks "Continue with Google"
2. Backend redirects to Google OAuth consent screen
3. User authorizes the application
4. Google redirects back to backend with authorization code
5. Backend exchanges code for user info
6. Backend creates or updates user in MongoDB
7. Backend generates JWT token
8. User is redirected to frontend with token
9. Frontend stores token in localStorage
10. Token is used for authenticated API requests

## 🛡️ Security Features

- JWT tokens with expiration (24 hours)
- Secure session handling
- CORS configured for localhost
- MongoDB user storage
- Profile picture from Google

## 📝 Next Steps

1. **Protect Main Pages**: Add authentication check to index.html
2. **Profile Display**: Show user name and picture in header
3. **Logout**: Add logout button
4. **Password Login**: Implement email/password authentication
5. **Production**: Update OAuth settings for production domain

## 🐛 Troubleshooting

### "Google OAuth not configured"
- Make sure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in .env
- Restart the backend server after updating .env

### "redirect_uri_mismatch"
- Check that redirect URI in Google Console matches exactly: `http://localhost:5000/api/auth/google/callback`

### Backend won't start
- Make sure MongoDB is running
- Check that all packages are installed: `pip install -r requirements.txt`

### Can't login with Google
- Make sure you've added your email as a test user in Google Console
- Check browser console for errors

## 📚 Full Documentation

See [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md) for detailed setup instructions and production deployment guide.

## 🎉 You're Ready!

Your data integrity platform now has professional Google authentication. Users can securely log in with their Google accounts!
