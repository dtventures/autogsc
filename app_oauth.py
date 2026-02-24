"""
AutoGSC SaaS Version - OAuth-based Authentication
Users login with Google or email/password. Email users can connect GSC from dashboard.
"""
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Thread
import subprocess
import os
import sys
import json
import secrets
import sqlite3

app = Flask(__name__)
# Read secret key from environment or generate one
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# SQLite DB for email/password users
DB_PATH = os.path.join(os.path.dirname(__file__), 'autogsc_users.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                password_hash TEXT,
                gsc_credentials TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()


def get_user_by_email(email):
    with get_db() as conn:
        return conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()


def get_or_create_user(email, name=None):
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not user:
            conn.execute('INSERT INTO users (email, name) VALUES (?, ?)', (email, name))
            conn.commit()
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        return user


init_db()

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
    from flask import request
    import tempfile
    
    # Construct redirect URI from request if not set in environment
    redirect_uri = REDIRECT_URI
    if not redirect_uri or redirect_uri == 'http://localhost:5000/oauth/callback':
        # Try to construct from request
        if request and request.host:
            scheme = request.scheme if hasattr(request, 'scheme') else 'https'
            host = request.host
            redirect_uri = f"{scheme}://{host}/oauth/callback"
    
    if CLIENT_CONFIG:
        # Use config from environment variable
        # Flow.from_client_secrets_file requires a file, so write to temp file
        try:
            # Validate CLIENT_CONFIG structure
            if not isinstance(CLIENT_CONFIG, dict):
                raise ValueError(f"CLIENT_CONFIG must be a dict, got {type(CLIENT_CONFIG)}")
            if 'web' not in CLIENT_CONFIG:
                raise ValueError("CLIENT_CONFIG missing 'web' key. Expected format: {'web': {...}}")
            if 'client_id' not in CLIENT_CONFIG['web']:
                raise ValueError("CLIENT_CONFIG missing 'client_id' in 'web' key")
            if 'client_secret' not in CLIENT_CONFIG['web']:
                raise ValueError("CLIENT_CONFIG missing 'client_secret' in 'web' key")
            
            # Write config to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(CLIENT_CONFIG, f)
                temp_file = f.name
            
            try:
                return Flow.from_client_secrets_file(
                    temp_file,
                    scopes=SCOPES,
                    redirect_uri=redirect_uri
                )
            finally:
                # Clean up temp file (though it will be deleted when process ends)
                try:
                    os.unlink(temp_file)
                except:
                    pass
        except Exception as e:
            raise ValueError(f"Failed to create OAuth flow from CLIENT_CONFIG: {str(e)}") from e
    else:
        # Use config from file (local development)
        if not CLIENT_SECRETS_FILE or not os.path.exists(CLIENT_SECRETS_FILE):
            raise FileNotFoundError(
                f"OAuth client secret file not found: {CLIENT_SECRETS_FILE}\n"
                f"Please set GOOGLE_CLIENT_SECRET environment variable in Render or create client_secret.json for local development.\n"
                f"GOOGLE_CLIENT_SECRET_ENV is set: {GOOGLE_CLIENT_SECRET_ENV is not None}"
            )
        return Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri
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
    """Get credentials from session, loading from DB if needed for email users."""
    if 'credentials' not in session:
        if session.get('auth_method') == 'email' and 'user' in session:
            user = get_user_by_email(session['user']['email'])
            if user and user['gsc_credentials']:
                session['credentials'] = json.loads(user['gsc_credentials'])
        if 'credentials' not in session:
            return None
    return Credentials(**session['credentials'])


@app.route("/")
def index():
    """Main page - show landing page v2 or dashboard."""
    if 'user' in session:
        return render_template("dashboard_oauth.html")
    return render_template("home_v2.html")

@app.route("/debug/oauth-config")
def debug_oauth_config():
    """Debug endpoint to check OAuth configuration (remove in production)."""
    config_status = {
        "CLIENT_CONFIG_set": CLIENT_CONFIG is not None,
        "CLIENT_SECRETS_FILE": CLIENT_SECRETS_FILE if CLIENT_SECRETS_FILE else "Not set",
        "CLIENT_SECRETS_FILE_exists": os.path.exists(CLIENT_SECRETS_FILE) if CLIENT_SECRETS_FILE else False,
        "REDIRECT_URI": REDIRECT_URI,
        "GOOGLE_CLIENT_SECRET_ENV_set": GOOGLE_CLIENT_SECRET_ENV is not None,
        "OAUTHLIB_INSECURE_TRANSPORT": os.environ.get('OAUTHLIB_INSECURE_TRANSPORT'),
    }
    if CLIENT_CONFIG:
        config_status["CLIENT_CONFIG_keys"] = list(CLIENT_CONFIG.keys())
        if 'web' in CLIENT_CONFIG:
            config_status["CLIENT_ID"] = CLIENT_CONFIG['web'].get('client_id', 'Not found')
    return jsonify(config_status)

@app.route("/v2")
def index_v2():
    """Homepage Version 2 (Dark Mode / Terminal)."""
    return render_template("home_v2.html")

@app.route("/privacy")
def privacy():
    """Privacy Policy page (required for OAuth verification)."""
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    """Terms of Service page (required for OAuth verification)."""
    return render_template("terms.html")


@app.route("/login")
def login():
    """Show login page with Google and email/password options."""
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template("login.html")


@app.route("/auth/google")
def auth_google():
    """Start Google OAuth flow."""
    try:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(f"REDIRECT_URI: {REDIRECT_URI}")
        logger.info(f"CLIENT_CONFIG set: {CLIENT_CONFIG is not None}")

        flow = get_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
        import traceback
        error_msg = f"OAuth setup error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        import logging
        logging.error(error_msg)
        return f"""
        <h1>OAuth Configuration Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <h2>Configuration Status:</h2>
        <ul>
            <li>REDIRECT_URI: {REDIRECT_URI}</li>
            <li>CLIENT_CONFIG set: {CLIENT_CONFIG is not None}</li>
            <li>CLIENT_SECRETS_FILE: {CLIENT_SECRETS_FILE}</li>
            <li>CLIENT_SECRETS_FILE exists: {os.path.exists(CLIENT_SECRETS_FILE) if CLIENT_SECRETS_FILE else 'N/A'}</li>
            <li>GOOGLE_CLIENT_SECRET_ENV set: {GOOGLE_CLIENT_SECRET_ENV is not None}</li>
        </ul>
        <h2>Full Traceback:</h2>
        <pre>{traceback.format_exc()}</pre>
        """, 500


@app.route("/register", methods=["GET"])
def register():
    """Show registration page."""
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_post():
    """Create new email/password user."""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')

    if not email or not password:
        return render_template("register.html", error="Email and password are required.", name=name, email=email)
    if password != confirm:
        return render_template("register.html", error="Passwords do not match.", name=name, email=email)
    if len(password) < 6:
        return render_template("register.html", error="Password must be at least 6 characters.", name=name, email=email)

    existing = get_user_by_email(email)
    if existing:
        return render_template("register.html", error="An account with this email already exists.", name=name, email=email)

    password_hash = generate_password_hash(password)
    with get_db() as conn:
        conn.execute('INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)',
                     (email, name or email, password_hash))
        conn.commit()

    session['user'] = {'email': email, 'name': name or email}
    session['auth_method'] = 'email'
    return redirect(url_for('index'))


@app.route("/auth/email-login", methods=["POST"])
def email_login():
    """Login with email and password."""
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    if not email or not password:
        return render_template("login.html", error="Email and password are required.")

    user = get_user_by_email(email)
    if not user or not user['password_hash']:
        return render_template("login.html", error="Invalid email or password.")
    if not check_password_hash(user['password_hash'], password):
        return render_template("login.html", error="Invalid email or password.")

    session['user'] = {'email': user['email'], 'name': user['name'] or user['email']}
    session['auth_method'] = 'email'

    if user['gsc_credentials']:
        session['credentials'] = json.loads(user['gsc_credentials'])

    return redirect(url_for('index'))


@app.route("/connect/gsc")
def connect_gsc():
    """Start GSC OAuth flow for an already-logged-in email user."""
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        flow = get_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['state'] = state
        session['connecting_gsc'] = True
        return redirect(authorization_url)
    except Exception as e:
        import traceback
        return f"<h1>Error starting OAuth</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", 500


@app.route("/oauth/callback")
def oauth_callback():
    """Handle OAuth callback — both new Google login and email-user GSC connection."""
    try:
        flow = get_flow()
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        credentials_dict = credentials_to_dict(credentials)
    except Exception as e:
        import traceback
        error_msg = f"OAuth callback error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return f"<h1>OAuth Callback Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", 500

    # If an email user was connecting GSC, store credentials and return to dashboard
    if session.get('connecting_gsc') and 'user' in session:
        email = session['user']['email']
        with get_db() as conn:
            conn.execute('UPDATE users SET gsc_credentials = ? WHERE email = ?',
                         (json.dumps(credentials_dict), email))
            conn.commit()
        session['credentials'] = credentials_dict
        session.pop('connecting_gsc', None)
        return redirect(url_for('index'))

    # Normal Google login: get user info and set session
    try:
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        google_email = user_info.get('email')
        google_name = user_info.get('name', google_email)
    except Exception:
        google_email = 'unknown'
        google_name = 'User'

    session['credentials'] = credentials_dict
    session['user'] = {'email': google_email, 'name': google_name}
    session['auth_method'] = 'google'

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
    try:
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

    except Exception as e:
        import traceback
        error_msg = f"Scan error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': str(e), 'details': error_msg}), 500


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
    if CLIENT_SECRETS_FILE and not os.path.exists(CLIENT_SECRETS_FILE):
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
    print("  Open: http://localhost:8080")
    print("="*50 + "\n")
    
    app.run(debug=True, port=8080)
