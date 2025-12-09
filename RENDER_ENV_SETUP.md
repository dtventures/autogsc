# Render Environment Variables Setup

## How to Add Environment Variables to Render

1. **After creating your service on Render**, go to your service dashboard
2. Click on **"Environment"** in the left sidebar
3. Click **"Add Environment Variable"** for each variable below

## Required Environment Variables

Copy these **exact values** into Render:

### 1. GOOGLE_CLIENT_SECRET
**Value:**
```
Paste your entire client_secret.json content here as a single-line JSON string
Get this from: Google Cloud Console → APIs & Services → Credentials → Your OAuth 2.0 Client ID
```

### 2. SECRET_KEY
**Value:**
```
Generate a secure random key with: python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. OAUTHLIB_INSECURE_TRANSPORT
**Value:**
```
0
```

### 4. PORT
**Value:**
```
10000
```
*(Note: Render sets this automatically, but it's good to have it explicitly)*

## After Deployment

1. **Get your Render URL** (e.g., `https://your-app-name.onrender.com`)

2. **Update Google OAuth Redirect URI:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Find your OAuth 2.0 Client ID
   - Click Edit
   - Add to **Authorized redirect URIs**:
     ```
     https://your-app-name.onrender.com/oauth/callback
     ```
   - Save

3. **Update REDIRECT_URI in Render** (optional, if you add it as an env var):
   - Go to Render → Your Service → Environment
   - Add/Update `REDIRECT_URI` with your production URL:
     ```
     https://your-app-name.onrender.com/oauth/callback
     ```

## Testing

After deployment:
1. Visit your Render URL
2. Click "Login" or "Continue with Google"
3. You should be redirected to Google OAuth
4. After authorizing, you should be redirected back to your app


