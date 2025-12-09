# Setting Up Custom Domain: lighthouselaunch.com/autogsc

You have two options for deploying to `lighthouselaunch.com/autogsc`:

## Option 1: Subdomain (Easiest) ⭐ Recommended
Deploy to `autogsc.lighthouselaunch.com` instead of a subpath.

### Steps:
1. **In Render Dashboard:**
   - Go to your service → Settings → Custom Domain
   - Add custom domain: `autogsc.lighthouselaunch.com`
   - Render will give you DNS records to add

2. **In your DNS provider (where lighthouselaunch.com is hosted):**
   - Add a CNAME record:
     - Name: `autogsc`
     - Value: `your-render-service.onrender.com` (or the hostname Render provides)

3. **Update Google OAuth Redirect URI:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Edit your OAuth 2.0 Client ID
   - Add: `https://autogsc.lighthouselaunch.com/oauth/callback`
   - Update `REDIRECT_URI` in Render environment variables

4. **Done!** Your app will be at `https://autogsc.lighthouselaunch.com`

---

## Option 2: Subpath /autogsc (Requires Reverse Proxy)

To serve at `lighthouselaunch.com/autogsc`, you need a reverse proxy on your main domain.

### Setup Steps:

#### 1. Configure Render Service
- In Render, your service will be at its Render URL (e.g., `your-app.onrender.com`)
- Add environment variable in Render:
  - Key: `REDIRECT_URI`
  - Value: `https://lighthouselaunch.com/autogsc/oauth/callback`

#### 2. Set Up Reverse Proxy on lighthouselaunch.com

**If using Nginx** (on your main server):
```nginx
location /autogsc {
    proxy_pass https://your-app.onrender.com;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header SCRIPT_NAME /autogsc;
    
    # WebSocket support (if needed)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

**If using Cloudflare Workers** (or similar):
- Create a worker that proxies `/autogsc/*` to your Render service
- Add the `SCRIPT_NAME` header: `/autogsc`

**If using Apache**:
```apache
<Location /autogsc>
    ProxyPass https://your-app.onrender.com/
    ProxyPassReverse https://your-app.onrender.com/
    ProxyPreserveHost On
    RequestHeader set SCRIPT_NAME "/autogsc"
</Location>
```

#### 3. Update Google OAuth
- Add redirect URI: `https://lighthouselaunch.com/autogsc/oauth/callback`

#### 4. Update Render Environment
- `REDIRECT_URI`: `https://lighthouselaunch.com/autogsc/oauth/callback`

---

## Quick Setup (Recommended: Subdomain)

1. **Render Dashboard** → Your Service → Settings → Custom Domain
2. **Add**: `autogsc.lighthouselaunch.com`
3. **Copy DNS records** from Render
4. **Add CNAME** in your DNS provider
5. **Update Google OAuth** redirect URI to: `https://autogsc.lighthouselaunch.com/oauth/callback`
6. **Update Render env var** `REDIRECT_URI`: `https://autogsc.lighthouselaunch.com/oauth/callback`
7. **Wait for DNS propagation** (5-30 minutes)
8. **Done!**

---

## Testing

After setup:
1. Visit your custom domain
2. Click "Login" or "Continue with Google"
3. You should be redirected to Google OAuth
4. After authorizing, you should be redirected back to your app

