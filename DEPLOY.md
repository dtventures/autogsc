# 🚀 How to Deploy AutoGSC to Production

Your app is ready for the world. Here is how to deploy it securely for others to use.

## 1. Prerequisites
- A Google Cloud Project (where you got your API keys)
- A domain name (optional, but recommended for HTTPS)
- GitHub account (for most deployment platforms)

## 2. Security Check 🔒
Before deploying, make sure you:
1.  **Switch to HTTPS**: In `app_oauth.py` or `app_saas.py`, remove or set `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'`. OAuth requires HTTPS in production.
2.  **Secret Key**: Change `app.secret_key` to a secure environment variable (use `os.environ.get('SECRET_KEY', secrets.token_hex(32))`).
3.  **Redirect URI**: Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and add your production URL to the **Authorized redirect URIs**:
    *   `https://your-app-name.com/oauth/callback`
    *   `https://your-app-name.vercel.app/oauth/callback` (if using Vercel)
    *   `https://your-app-name.onrender.com/oauth/callback` (if using Render)

## 3. Deployment Options

### Option A: Google Cloud Run (Recommended for Google APIs) ⭐
**Best for**: Production apps, auto-scaling, integrated with Google services
**Cost**: Pay per use (~$0.40 per million requests, free tier: 2M requests/month)
**Pros**: Native Google integration, auto-scaling, HTTPS included
**Cons**: Requires Google Cloud setup

1.  **Install gunicorn**: `pip install gunicorn` and update requirements: `pip freeze > requirements.txt`
2.  **Enable Container Registry**: In Google Cloud Console, search for "Container Registry" and enable it.
3.  **Deploy via CLI**:
    ```bash
    # 1. Build the container
    gcloud builds submit --tag gcr.io/PROJECT-ID/autogsc

    # 2. Deploy
    gcloud run deploy autogsc \
      --image gcr.io/PROJECT-ID/autogsc \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated
    ```
4.  **Environment Variables**:
    - In Cloud Run dashboard: "Edit & Deploy New Revision" → "Variables & Secrets"
    - Add `GOOGLE_CLIENT_SECRET` with contents of `client_secret.json` (as JSON string)
    - Add `SECRET_KEY` with a secure random string
    - Set `OAUTHLIB_INSECURE_TRANSPORT=0`

### Option B: Render (Easiest for Beginners) 🎯
**Best for**: Quick deployment, free tier available
**Cost**: Free tier (spins down after inactivity), $7/month for always-on
**Pros**: Simple setup, auto-deploy from GitHub, free SSL
**Cons**: Free tier has cold starts

1.  **Push code to GitHub** (make repo private if including secrets)
2.  **Create New Web Service** on [Render](https://render.com)
3.  **Connect GitHub repo**
4.  **Configure**:
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: `gunicorn app_oauth:app --bind 0.0.0.0:$PORT`
    - **Environment**: `Python 3`
5.  **Environment Variables**:
    - `GOOGLE_CLIENT_SECRET`: Contents of `client_secret.json` (as JSON string)
    - `SECRET_KEY`: Random secure string
    - `OAUTHLIB_INSECURE_TRANSPORT`: `0`
    - `PORT`: `10000` (Render auto-sets this, but good to have)
6.  **Update redirect URI** in Google Cloud Console to: `https://your-app.onrender.com/oauth/callback`

### Option C: Railway (Great Developer Experience) 🚂
**Best for**: Modern apps, great DX, PostgreSQL included
**Cost**: $5/month + usage, $5 free credit monthly
**Pros**: Great UI, auto-deploy, database included
**Cons**: Costs more than free options

1.  **Push code to GitHub**
2.  **Create New Project** on [Railway](https://railway.app)
3.  **Deploy from GitHub**
4.  **Configure**:
    - **Start Command**: `gunicorn app_oauth:app --bind 0.0.0.0:$PORT`
5.  **Environment Variables**: Same as Render
6.  **Update redirect URI** in Google Cloud Console

### Option D: Vercel (For Serverless) ⚡
**Best for**: Serverless architecture, edge functions
**Cost**: Free tier available, $20/month for Pro
**Pros**: Fast global CDN, great for static + API
**Cons**: Requires serverless function setup

1.  **Install Vercel CLI**: `npm i -g vercel`
2.  **Create `vercel.json`**:
    ```json
    {
      "version": 2,
      "builds": [
        {
          "src": "app_oauth.py",
          "use": "@vercel/python"
        }
      ],
      "routes": [
        {
          "src": "/(.*)",
          "dest": "app_oauth.py"
        }
      ]
    }
    ```
3.  **Deploy**: `vercel --prod`
4.  **Environment Variables**: Set in Vercel dashboard

### Option E: Heroku (Classic Choice) 🟣
**Best for**: Traditional hosting, familiar platform
**Cost**: $7/month (Eco Dyno), free tier discontinued
**Pros**: Well-documented, add-ons available
**Cons**: More expensive, no free tier

1.  **Install Heroku CLI**
2.  **Create `Procfile`**: `web: gunicorn app_oauth:app --bind 0.0.0.0:$PORT`
3.  **Deploy**:
    ```bash
    heroku create your-app-name
    git push heroku main
    ```
4.  **Set environment variables**: `heroku config:set GOOGLE_CLIENT_SECRET="..."`

### Option F: DigitalOcean App Platform (Balanced) 🌊
**Best for**: Full control, predictable pricing
**Cost**: $5/month minimum
**Pros**: Predictable pricing, good performance
**Cons**: More setup required

1.  **Connect GitHub repo** in DigitalOcean dashboard
2.  **Configure build/run commands**
3.  **Set environment variables**

## 4. Production Code Updates

### Update OAuth Redirect URI Dynamically
Update `app_oauth.py` or `app_saas.py` to read redirect URI from environment:

```python
import os

# Get redirect URI from environment or use default
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/oauth/callback')

def get_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
```

### Read Client Secret from Environment (Safer)
```python
import os
import json

# Read from environment variable if available, otherwise file
if os.environ.get('GOOGLE_CLIENT_SECRET'):
    client_config = json.loads(os.environ.get('GOOGLE_CLIENT_SECRET'))
    CLIENT_SECRETS_FILE = None  # Don't use file
else:
    CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secret.json")

def get_flow():
    if CLIENT_SECRETS_FILE:
        return Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    else:
        return Flow.from_client_secrets(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
```

### Update Secret Key
```python
import os
import secrets

app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
```

## 5. Multi-User Setup (SaaS Version)

If deploying `app_saas.py` for multiple users:

1.  **Database**: SQLite works for small scale, but consider PostgreSQL for production:
    - Railway: Includes PostgreSQL
    - Render: Add PostgreSQL add-on
    - Heroku: Add Postgres add-on
2.  **Update database connection** in `app_saas.py` to use PostgreSQL if needed
3.  **Session storage**: Consider Redis for production (available on most platforms)

## 6. Verification Checklist

Once deployed:
- [ ] Open production URL
- [ ] Login with Google works
- [ ] OAuth callback redirects correctly
- [ ] "Mission Control" dashboard loads
- [ ] Can connect to Google Search Console
- [ ] Can submit URLs to Indexing API
- [ ] HTTPS is working (check for lock icon)
- [ ] Environment variables are set correctly

## 7. Monitoring & Maintenance

- **Logs**: Check platform logs for errors
- **Quotas**: Monitor Google API quotas in Cloud Console
- **Database**: Backup SQLite database regularly (or use managed DB)
- **Updates**: Set up auto-deploy from GitHub for easy updates

## Quick Start Recommendation

**For fastest deployment**: Use **Render** (Option B)
1. Push to GitHub
2. Connect to Render
3. Set environment variables
4. Deploy

**For production scale**: Use **Google Cloud Run** (Option A)
1. Build Docker image
2. Deploy to Cloud Run
3. Set up Secret Manager for credentials
