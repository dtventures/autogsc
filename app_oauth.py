"""
AutoGSC SaaS Version - OAuth-based Authentication
Users login with Google, no manual setup required.
"""
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from threading import Thread
import subprocess
import os
import sys
import json
import secrets

app = Flask(__name__)
# Read secret key from environment or generate one
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Get application root for subpath deployment (Vercel/Render)
APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/')
if APPLICATION_ROOT and not APPLICATION_ROOT.startswith('/'):
    APPLICATION_ROOT = '/' + APPLICATION_ROOT

# Configure Flask for subpath deployment
if APPLICATION_ROOT != '/':
    app.config['APPLICATION_ROOT'] = APPLICATION_ROOT

# OAuth Configuration - Read from environment or file
# Allow OAuth over HTTP for local development (set to '0' in production)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', '1')

# Get redirect URI from environment or use default
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/oauth/callback')

# Read client secret from environment (Render) or file (local dev)
GOOGLE_CLIENT_SECRET_ENV = os.environ.get('GOOGLE_CLIENT_SECRET')
if GOOGLE_CLIENT_SECRET_ENV:
    # Parse JSON string from environment
    try:
        CLIENT_CONFIG = json.loads(GOOGLE_CLIENT_SECRET_ENV)
        CLIENT_SECRETS_FILE = None
    except json.JSONDecodeError:
        print("Warning: Failed to parse GOOGLE_CLIENT_SECRET from environment, falling back to file")
        CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secret.json")
        CLIENT_CONFIG = None
else:
    # Fall back to file for local development
    CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secret.json")
    CLIENT_CONFIG = None

# Scopes needed for GSC and Indexing API
SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/indexing',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

# In-memory storage (replace with database in production)
user_data = {}


def get_flow():
    """Create OAuth flow from environment variable or file."""
    if CLIENT_CONFIG:
        # Use config from environment variable
        return Flow.from_client_secrets(
            CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
    else:
        # Use config from file (local development)
        return Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )


def credentials_to_dict(credentials):
    """Convert credentials to dictionary for storage."""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


def get_user_credentials():
    """Get credentials from session."""
    if 'credentials' not in session:
        return None
    return Credentials(**session['credentials'])


@app.route("/")
def index():
    """Main page - show login or dashboard."""
    if 'user' in session:
        return render_template("dashboard_oauth.html")
    return render_template("home.html")

@app.route("/v2")
def index_v2():
    """Homepage Version 2 (Dark Mode / Terminal)."""
    return render_template("home_v2.html")


@app.route("/login")
def login():
    """Start OAuth flow."""
    flow = get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['state'] = state
    return redirect(authorization_url)


@app.route("/oauth/callback")
def oauth_callback():
    """Handle OAuth callback."""
    flow = get_flow()
    flow.fetch_token(authorization_response=request.url)
    
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    
    # Get user info
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    
    try:
        # Build a service to get user email
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        session['user'] = {
            'email': user_info.get('email'),
            'name': user_info.get('name', user_info.get('email'))
        }
    except Exception as e:
        session['user'] = {'email': 'unknown', 'name': 'User'}
    
    return redirect(url_for('index'))


@app.route("/logout")
def logout():
    """Clear session."""
    session.clear()
    return redirect(url_for('index'))


@app.route("/api/user")
def api_user():
    """Get current user info."""
    if 'user' not in session:
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'user': session['user']
    })


@app.route("/api/sites")
def api_sites():
    """List all GSC sites the user has access to."""
    credentials = get_user_credentials()
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        service = build('searchconsole', 'v1', credentials=credentials)
        sites = service.sites().list().execute()
        return jsonify(sites.get('siteEntry', []))
    except HttpError as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/site/select", methods=["POST"])
def api_select_site():
    """Select a site to work with."""
    data = request.json
    site_url = data.get('siteUrl')
    sitemap_url = data.get('sitemapUrl')
    
    if not site_url:
        return jsonify({'error': 'Site URL required'}), 400
    
    session['selected_site'] = {
        'site_url': site_url,
        'sitemap_url': sitemap_url or f"{site_url.rstrip('/')}/sitemap.xml"
    }
    
    return jsonify({'success': True})


@app.route("/api/stats")
def api_stats():
    """Get stats for selected site."""
    if 'selected_site' not in session:
        return jsonify({'error': 'No site selected'}), 400
    
    site = session['selected_site']
    
    # For now, return basic info
    # TODO: Integrate with database for full stats
    return jsonify({
        'site_url': site['site_url'],
        'sitemap_url': site['sitemap_url'],
        'total_urls': 0,
        'indexed': 0,
        'pending': 0,
        'unindexed': 0,
        'today_submissions': 0,
        'today_limit': 200
    })


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """Scan sitemap and check indexing status."""
    credentials = get_user_credentials()
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401
    
    if 'selected_site' not in session:
        return jsonify({'error': 'No site selected'}), 400
    
    site = session['selected_site']
    
    # Import sitemap parser
    from sitemap_parser import get_all_urls
    
    # Get all URLs from sitemap
    urls = get_all_urls(site['sitemap_url'])
    
    results = {
        'total': len(urls),
        'indexed': 0,
        'not_indexed': 0,
        'errors': 0,
        'urls': []
    }
    
    # Check each URL's status
    try:
        service = build('searchconsole', 'v1', credentials=credentials)
        
        for url in urls:
            try:
                response = service.urlInspection().index().inspect(
                    body={'inspectionUrl': url, 'siteUrl': site['site_url']}
                ).execute()
                
                result = response.get('inspectionResult', {})
                index_status = result.get('indexStatusResult', {})
                coverage = index_status.get('coverageState', 'Unknown')
                
                is_indexed = 'indexed' in coverage.lower() and 'not' not in coverage.lower()
                
                results['urls'].append({
                    'url': url,
                    'status': 'indexed' if is_indexed else coverage,
                    'indexed': is_indexed
                })
                
                if is_indexed:
                    results['indexed'] += 1
                else:
                    results['not_indexed'] += 1
                    
            except HttpError as e:
                results['errors'] += 1
                results['urls'].append({
                    'url': url,
                    'status': 'error',
                    'indexed': False
                })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify(results)


@app.route("/api/submit", methods=["POST"])
def api_submit():
    """Submit URLs for indexing."""
    credentials = get_user_credentials()
    if not credentials:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    urls = data.get('urls', [])
    
    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400
    
    results = {
        'submitted': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
        service = build('indexing', 'v3', credentials=credentials)
        
        for url in urls[:200]:  # Respect daily limit
            try:
                service.urlNotifications().publish(
                    body={'url': url, 'type': 'URL_UPDATED'}
                ).execute()
                results['submitted'] += 1
            except HttpError as e:
                results['failed'] += 1
                results['errors'].append({'url': url, 'error': str(e)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify(results)


if __name__ == "__main__":
    # Check for client_secret.json
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print("\n" + "="*60)
        print("  SETUP REQUIRED: OAuth Client Secret")
        print("="*60)
        print("""
To enable Google Login, you need to:

1. Go to https://console.cloud.google.com
2. Select your project (or create one)
3. Go to APIs & Services → Credentials
4. Click "Create Credentials" → "OAuth client ID"
5. Choose "Web application"
6. Add these Authorized redirect URIs:
   - http://localhost:5000/oauth/callback
7. Click "Create"
8. Download the JSON file
9. Save it as: client_secret.json in the AutoGSC folder

Then restart this app.
""")
        print("="*60 + "\n")
    
    print("\n" + "="*50)
    print("  AutoGSC SaaS Version")
    print("  Open: http://localhost:5000")
    print("="*50 + "\n")
    
    app.run(debug=True, port=5000)
