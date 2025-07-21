# Supabase Google OAuth Testing Guide

This guide shows you how to test Supabase's built-in Google OAuth integration directly, without needing a custom API endpoint.

## 🚀 Quick Start (HTML Test Page)

### 1. Open the Test Page

```bash
# Open oauth_test.html in your browser
open oauth_test.html
# or serve it via a simple HTTP server for local testing
python -m http.server 8080
# Then visit: http://localhost:8080/oauth_test.html
```

### 2. Configure Supabase

- Enter your Supabase Project URL
- Enter your Supabase Anon Key  
- These can be found in your Supabase Dashboard → Settings → API

### 3. Test the OAuth Flow

1. Click "🚀 Sign in with Google" in the HTML page
2. Complete Google authentication
3. You'll be redirected back with a Supabase session
4. Test the Supabase auth methods with the provided buttons

## 🔗 Real Google OAuth Testing

### Step 1: Set up Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Go to **APIs & Services > Credentials**
4. Click **Create credentials > OAuth 2.0 Client ID**
5. Choose **Web application**
6. Add authorized origins:
   - `http://localhost:8080` (for test page)
   - `https://your-domain.com` (for production)
7. Add redirect URIs:
   - `https://your-project.supabase.co/auth/v1/callback`

### Step 2: Configure Supabase Authentication

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to **Authentication > Providers**
4. Enable **Google** provider
5. Add your Google Client ID and Secret from Step 1

### Step 3: Get Your Supabase Credentials

From your Supabase Dashboard → Settings → API:

```bash
# You'll need these for the HTML test page
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```
### Step 4: Test with Real OAuth Flow

Use the provided HTML test page (`oauth_test.html`):

1. **Open the test page**: `oauth_test.html` in your browser
2. **Configure settings**:
   - Enter your Supabase URL and Anon Key
   - Verify redirect URI (auto-filled)
3. **Start OAuth flow**: Click "🚀 Sign in with Google"
4. **Complete authentication**: Allow Google permissions
5. **View results**: See Supabase session and user info
6. **Test methods**: Use "Get Current User", "Get Session", and "Sign Out" buttons

The HTML page provides:
- ✅ Supabase client initialization  
- ✅ Google OAuth via Supabase
- ✅ Automatic session management
- ✅ Real-time auth state changes
- ✅ Session and user data display
- ✅ Error handling and logging

## 📋 What You'll See

### Supabase User Object
After successful OAuth, you'll get a user object like:
```json
{
  "id": "12345678-1234-1234-1234-123456789012",
  "email": "user@example.com",
  "email_confirmed_at": "2024-01-01T00:00:00Z",
  "phone": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "last_sign_in_at": "2024-01-01T00:00:00Z",
  "app_metadata": {
    "provider": "google",
    "providers": ["google"]
  },
  "user_metadata": {
    "avatar_url": "https://lh3.googleusercontent.com/...",
    "email": "user@example.com",
    "email_verified": true,
    "full_name": "John Doe",
    "iss": "https://accounts.google.com",
    "name": "John Doe",
    "picture": "https://lh3.googleusercontent.com/...",
    "provider_id": "123456789012345678901",
    "sub": "123456789012345678901"
  }
}
```

### Supabase Session Object
The session includes access tokens and metadata:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "refresh_token_here",
  "expires_in": 3600,
  "expires_at": 1706745600,
  "token_type": "bearer",
  "user": { /* user object above */ }
}
```

### Common Error Scenarios

**Invalid Supabase Configuration:**
- Check your Supabase URL and Anon Key
- Verify Google OAuth is enabled in Supabase Dashboard
- Ensure redirect URI matches exactly

**Google OAuth Errors:**
- Verify Google Client ID and Secret in Supabase
- Check authorized origins in Google Cloud Console
- Ensure redirect URI is `https://your-project.supabase.co/auth/v1/callback`

## 🔍 Debugging Tips

1. **Check Browser Console**: Look for JavaScript errors and auth state changes
2. **Verify Supabase Configuration**: Test connection with simple `getUser()` call
3. **Test Google OAuth Setup**: Use Google's OAuth Playground to verify credentials
4. **Use Browser DevTools**: Monitor network requests during OAuth flow
5. **Check Supabase Dashboard**: View Authentication logs for failed attempts

## 🎯 Next Steps

Once OAuth is working, you can:
- Use the Supabase session to authenticate API requests to your backend
- Extract the `access_token` from the session as a JWT for your API
- Set up Row Level Security (RLS) policies using the user's ID
- Build protected routes in your frontend application
5. **Validate JWT**: Use [jwt.io](https://jwt.io) to decode and verify JWT tokens 