# Vercel Deployment Guide: lighthouselaunch.com/autogsc

## Prerequisites
- Vercel account (free tier works)
- GitHub repo connected to Vercel
- Access to lighthouselaunch.com DNS settings

## Step 1: Install Vercel CLI (Optional but Recommended)

```bash
npm i -g vercel
```

## Step 2: Deploy to Vercel

### Option A: Via Vercel Dashboard (Easiest)

1. **Go to [Vercel Dashboard](https://vercel.com/dashboard)**
2. **Click "Add New Project"**
3. **Import your GitHub repository**: `dtventures/autogsc`
4. **Configure Project**:
   - Framework Preset: **Other** (or Python)
   - Root Directory: `.` (leave as is)
   - Build Command: Leave empty (Vercel auto-detects)
   - Output Directory: Leave empty
   - Install Command: `pip install -r requirements.txt`
5. **Click "Deploy"**

### Option B: Via CLI

```bash
cd /Users/macbookair/Desktop/AutoGSC
vercel login
vercel --prod
```

## Step 3: Configure Environment Variables

In Vercel Dashboard → Your Project → Settings → Environment Variables:

Add these variables:

1. **GOOGLE_CLIENT_SECRET**
   - Value: (Paste your entire client_secret.json content as a single-line JSON string)
   - Get this from: Google Cloud Console → APIs & Services → Credentials → Your OAuth 2.0 Client ID
   - Format: `{"web":{"client_id":"YOUR_CLIENT_ID.apps.googleusercontent.com",...}}`

2. **SECRET_KEY**
   - Value: (Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - Or use any secure random 64-character hex string

3. **OAUTHLIB_INSECURE_TRANSPORT**
   - Value: `0`

4. **REDIRECT_URI**
   - Value: `https://lighthouselaunch.com/autogsc/oauth/callback`

5. **APPLICATION_ROOT** (optional, already in vercel.json)
   - Value: `/autogsc`

## Step 4: Configure Custom Domain

1. **In Vercel Dashboard** → Your Project → Settings → Domains
2. **Add Domain**: `lighthouselaunch.com`
3. **Vercel will show DNS records** to add:
   - Usually a CNAME or A record
4. **Add DNS record** in your DNS provider (where lighthouselaunch.com is hosted):
   - Follow Vercel's instructions (usually CNAME to `cname.vercel-dns.com`)
5. **Wait for DNS propagation** (5-30 minutes)

## Step 5: Configure Path Rewrites

Vercel should automatically handle `/autogsc/*` routes based on `vercel.json`, but verify:

1. **In Vercel Dashboard** → Your Project → Settings → Deployment
2. **Check that routes are configured**:
   - `/autogsc/*` → `/api/autogsc.py`
   - `/autogsc` → `/api/autogsc.py`

## Step 6: Update Google OAuth

1. **Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)**
2. **Edit your OAuth 2.0 Client ID**
3. **Add Authorized redirect URI**:
   ```
   https://lighthouselaunch.com/autogsc/oauth/callback
   ```
4. **Save**

## Step 7: Redeploy

After adding environment variables:
1. **Go to Deployments tab**
2. **Click "Redeploy"** on the latest deployment
3. **Or push a new commit** to trigger auto-deploy

## Step 8: Test

1. Visit: `https://lighthouselaunch.com/autogsc`
2. Click "Login" or "Continue with Google"
3. You should be redirected to Google OAuth
4. After authorizing, you should be redirected back

## Troubleshooting

### Issue: 404 on /autogsc
- Check `vercel.json` routes are correct
- Verify `api/autogsc.py` exists
- Check deployment logs in Vercel

### Issue: OAuth redirect fails
- Verify `REDIRECT_URI` environment variable is set correctly
- Check Google OAuth redirect URI matches exactly
- Ensure HTTPS is working (Vercel provides this automatically)

### Issue: App not loading
- Check Vercel function logs: Project → Deployments → Click deployment → Functions tab
- Verify all environment variables are set
- Check that `requirements.txt` includes all dependencies

## Notes

- Vercel has a **10-second timeout** for free tier (upgrade to Pro for longer)
- Serverless functions have **cold starts** (first request may be slower)
- Static files in `/static` will be served automatically
- Database files (`.db`) won't persist between function invocations - consider using a database service

