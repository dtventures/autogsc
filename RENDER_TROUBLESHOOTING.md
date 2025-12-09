# Render OAuth Error Troubleshooting

## Quick Fix Checklist

### 1. Check Your Render Service URL
- Go to Render Dashboard → Your Service
- Note your service URL (e.g., `autogsc-xyz.onrender.com` or `autogsc.lighthouselaunch.com`)

### 2. Verify Environment Variables in Render

Go to: **Render Dashboard → Your Service → Environment**

Make sure these are set:

#### ✅ GOOGLE_CLIENT_SECRET
- Must be the **entire JSON** as a single-line string
- Format: `{"web":{"client_id":"...","client_secret":"...",...}}`
- No line breaks, no extra spaces

#### ✅ SECRET_KEY
- Any secure random 64-character hex string
- Example: `245c0f9ac1453af4ea6244b681b01199d79b900e8fff41f6682c8ab11d351b11`

#### ✅ OAUTHLIB_INSECURE_TRANSPORT
- Value: `0` (zero, not the letter O)

#### ✅ REDIRECT_URI (IMPORTANT!)
- If using custom domain: `https://autogsc.lighthouselaunch.com/oauth/callback`
- If using Render subdomain: `https://your-app-name.onrender.com/oauth/callback`
- **Must match exactly** what's in Google OAuth console

### 3. Update Google OAuth Console

Go to: [Google Cloud Console](https://console.cloud.google.com/apis/credentials)

1. Click on your **OAuth 2.0 Client ID**
2. Under **Authorized redirect URIs**, add:
   - If custom domain: `https://autogsc.lighthouselaunch.com/oauth/callback`
   - If Render subdomain: `https://your-app-name.onrender.com/oauth/callback`
3. **Save** the changes

### 4. Check Render Logs

1. Go to **Render Dashboard → Your Service → Logs**
2. Look for error messages when you click "Sign in with Google"
3. Common errors:
   - `Redirect URI mismatch` → Fix in Google Console
   - `Invalid client secret` → Check GOOGLE_CLIENT_SECRET format
   - `File not found` → GOOGLE_CLIENT_SECRET not set

### 5. Redeploy After Changes

**After updating environment variables:**
1. Go to **Render Dashboard → Your Service**
2. Click **"Manual Deploy"** → **"Deploy latest commit"**
3. Wait for deployment to complete

**After updating Google OAuth:**
- No redeploy needed, but wait 1-2 minutes for Google to update

### 6. Test the Debug Endpoint

Visit: `https://your-render-url.com/debug/oauth-config`

This will show:
- Whether GOOGLE_CLIENT_SECRET is set
- Current REDIRECT_URI
- Configuration status

## Common Issues & Solutions

### Issue: "Internal Server Error" when clicking Sign in

**Solution:**
1. Check Render logs for the actual error
2. Verify `GOOGLE_CLIENT_SECRET` is set correctly (entire JSON string)
3. Verify `REDIRECT_URI` matches Google Console exactly
4. Make sure `OAUTHLIB_INSECURE_TRANSPORT=0`

### Issue: "Redirect URI mismatch"

**Solution:**
1. Copy the exact redirect URI from the error message
2. Add it to Google OAuth Console → Authorized redirect URIs
3. Make sure it matches `REDIRECT_URI` in Render environment variables

### Issue: "Invalid client secret"

**Solution:**
1. Check that `GOOGLE_CLIENT_SECRET` is valid JSON
2. Make sure it's all on one line (no line breaks)
3. Verify it includes all required fields: `client_id`, `client_secret`, `project_id`, etc.

### Issue: App works locally but not on Render

**Solution:**
1. Make sure all environment variables are set in Render (not just locally)
2. Check that `REDIRECT_URI` uses `https://` (not `http://`)
3. Verify `OAUTHLIB_INSECURE_TRANSPORT=0` (not `1`)

## Step-by-Step Fix

1. **Get your Render URL**
   - Render Dashboard → Your Service → Copy the URL

2. **Set REDIRECT_URI in Render**
   - Environment → Add: `REDIRECT_URI` = `https://your-render-url.com/oauth/callback`

3. **Add to Google OAuth Console**
   - Same URL: `https://your-render-url.com/oauth/callback`

4. **Redeploy**
   - Manual Deploy → Deploy latest commit

5. **Test**
   - Visit your Render URL
   - Click "Sign in with Google"
   - Should redirect to Google OAuth

