# Google OAuth Setup Guide

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: "Data Integrity Platform"
4. Click "Create"

## Step 2: Enable Google+ API

1. In the left sidebar, go to "APIs & Services" → "Library"
2. Search for "Google+ API"
3. Click on it and press "Enable"

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" (for testing)
3. Fill in the required fields:
   - **App name**: Data Integrity Platform
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Click "Save and Continue"
5. Skip "Scopes" (click "Save and Continue")
6. Add test users (your email address)
7. Click "Save and Continue"

## Step 4: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Web application"
4. Configure:
   - **Name**: Data Integrity Platform Web Client
   - **Authorized JavaScript origins**:
     - `http://localhost:5000`
     - `http://localhost:8000`
   - **Authorized redirect URIs**:
     - `http://localhost:5000/api/auth/google/callback`
5. Click "Create"
6. Copy the **Client ID** and **Client Secret**

## Step 5: Update Backend .env File

1. Copy `backend/.env.example` to `backend/.env`
2. Fill in your Google credentials:

```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
```

3. Generate secure secret keys:

```bash
# For FLASK_SECRET_KEY and JWT_SECRET_KEY, use random strings:
python -c "import secrets; print(secrets.token_hex(32))"
```

## Step 6: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Step 7: Run the Application

```bash
# Start MongoDB (in a separate terminal)
mongod

# Start the backend server
python app.py
```

## Step 8: Test Google Login

1. Open `http://localhost:8000/login.html`
2. Click "Continue with Google"
3. Sign in with your Google account
4. You should be redirected to the main page

## Troubleshooting

### Error: "redirect_uri_mismatch"
- Make sure the redirect URI in Google Console exactly matches: `http://localhost:5000/api/auth/google/callback`
- No trailing slashes!

### Error: "Access blocked: This app's request is invalid"
- Make sure you've added your email as a test user in OAuth consent screen

### Error: "Google OAuth not configured"
- Check that GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in .env file
- Restart the backend server after updating .env

## Security Notes for Production

When deploying to production:

1. Change authorized origins to your actual domain:
   - `https://yourdomain.com`

2. Change redirect URI to:
   - `https://yourdomain.com/api/auth/google/callback`

3. Generate strong secret keys (don't use dev keys)

4. Set OAuth consent screen to "Internal" or get verification for "External"

5. Use HTTPS everywhere
