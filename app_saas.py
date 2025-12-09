"""
AutoGSC SaaS - Multi-User Application
Supports multiple users with OAuth login and per-user sites.
"""
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sqlite3
import os
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Allow HTTP for local dev
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# OAuth Config
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secret.json")
SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/indexing',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

DATABASE = os.path.join(os.path.dirname(__file__), "autogsc_saas.db")


# ============== Database ==============

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            credentials TEXT
        );
        
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            site_url TEXT NOT NULL,
            sitemap_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, site_url)
        );
        
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            indexing_status TEXT,
            last_checked TIMESTAMP,
            last_submitted TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(id),
            UNIQUE(site_id, url)
        );
        
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result TEXT,
            FOREIGN KEY (site_id) REFERENCES sites(id)
        );
    ''')
    conn.commit()
    conn.close()


init_db()


# ============== Helpers ==============

def get_or_create_user(email, name=None, credentials=None):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    
    if user:
        if credentials:
            cursor.execute('UPDATE users SET credentials = ? WHERE id = ?', 
                          (credentials, user['id']))
            conn.commit()
    else:
        cursor.execute('INSERT INTO users (email, name, credentials) VALUES (?, ?, ?)',
                      (email, name, credentials))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
    
    conn.close()
    return dict(user)


def get_user_sites(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sites WHERE user_id = ?', (user_id,))
    sites = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sites


def add_user_site(user_id, site_url, sitemap_url=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO sites (user_id, site_url, sitemap_url) VALUES (?, ?, ?)',
            (user_id, site_url, sitemap_url)
        )
        conn.commit()
        site_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute(
            'SELECT id FROM sites WHERE user_id = ? AND site_url = ?',
            (user_id, site_url)
        )
        site_id = cursor.fetchone()['id']
    conn.close()
    return site_id


def get_site_stats(site_id):
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute('SELECT COUNT(*) FROM urls WHERE site_id = ?', (site_id,))
    stats['total_urls'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM urls WHERE site_id = ? AND indexing_status = 'indexed'", (site_id,))
    stats['indexed'] = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM urls 
        WHERE site_id = ? 
        AND indexing_status != 'indexed' 
        AND last_submitted IS NOT NULL
        AND datetime(last_submitted) > datetime('now', '-48 hours')
    ''', (site_id,))
    stats['pending'] = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM urls 
        WHERE site_id = ? 
        AND indexing_status != 'indexed'
        AND (last_submitted IS NULL OR datetime(last_submitted) <= datetime('now', '-48 hours'))
    ''', (site_id,))
    stats['unindexed'] = cursor.fetchone()[0]
    
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) FROM submissions 
        WHERE site_id = ? AND date(submitted_at) = ?
    ''', (site_id, today))
    stats['today_submissions'] = cursor.fetchone()[0]
    
    conn.close()
    return stats


def oauth_exists():
    return os.path.exists(CLIENT_SECRETS_FILE)


def get_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8080/oauth/callback'
    )


def get_credentials():
    if 'user_id' not in session:
        return None
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT credentials FROM users WHERE id = ?', (session['user_id'],))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row['credentials']:
        return None
    
    import json
    creds_dict = json.loads(row['credentials'])
    return Credentials(**creds_dict)


# ============== Routes ==============

@app.route("/")
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template("home.html")


@app.route("/login")
def login():
    if not oauth_exists():
        return render_template("setup_required.html")
    
    flow = get_flow()
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['state'] = state
    return redirect(auth_url)


@app.route("/oauth/callback")
def oauth_callback():
    if not oauth_exists():
        return redirect('/')
    
    import json
    
    flow = get_flow()
    flow.fetch_token(authorization_response=request.url)
    
    credentials = flow.credentials
    creds_dict = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': list(credentials.scopes)
    }
    
    # Get user info
    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()
    
    # Save user
    user = get_or_create_user(
        email=user_info['email'],
        name=user_info.get('name'),
        credentials=json.dumps(creds_dict)
    )
    
    session['user_id'] = user['id']
    session['user_email'] = user['email']
    session['user_name'] = user.get('name')
    
    return redirect('/dashboard')


@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')


@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template("user_dashboard.html")


@app.route("/api/user")
def api_user():
    if 'user_id' not in session:
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'email': session.get('user_email'),
        'name': session.get('user_name')
    })


@app.route("/api/sites")
def api_sites():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    sites = get_user_sites(session['user_id'])
    return jsonify(sites)


@app.route("/api/gsc/sites")
def api_gsc_sites():
    """Get all GSC sites the user has access to."""
    credentials = get_credentials()
    if not credentials:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        service = build('searchconsole', 'v1', credentials=credentials)
        result = service.sites().list().execute()
        return jsonify(result.get('siteEntry', []))
    except HttpError as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/sites/add", methods=["POST"])
def api_add_site():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    site_url = data.get('site_url')
    sitemap_url = data.get('sitemap_url')
    
    if not site_url:
        return jsonify({'error': 'site_url required'}), 400
    
    site_id = add_user_site(session['user_id'], site_url, sitemap_url)
    session['current_site_id'] = site_id
    
    return jsonify({'success': True, 'site_id': site_id})


@app.route("/api/sites/<int:site_id>/stats")
def api_site_stats(site_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    stats = get_site_stats(site_id)
    stats['today_limit'] = 200
    return jsonify(stats)


@app.route("/api/sites/<int:site_id>/scan", methods=["POST"])
def api_scan_site(site_id):
    """Scan a site's sitemap and check indexing status."""
    from sitemap_parser import get_all_urls
    
    credentials = get_credentials()
    if not credentials:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get site info
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sites WHERE id = ?', (site_id,))
    site_row = cursor.fetchone()
    
    if not site_row:
        return jsonify({'error': 'Site not found'}), 404
    
    site = dict(site_row)
    
    # Get URLs from sitemap
    urls = get_all_urls(site['sitemap_url'])
    
    results = {'total': len(urls), 'indexed': 0, 'not_indexed': 0, 'urls': []}
    
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
                
                is_indexed = 'Submitted and indexed' in coverage
                status = 'indexed' if is_indexed else coverage
                
                # Save to database
                cursor.execute('''
                    INSERT INTO urls (site_id, url, indexing_status, last_checked)
                    VALUES (?, ?, ?, datetime('now'))
                    ON CONFLICT(site_id, url) DO UPDATE SET
                        indexing_status = excluded.indexing_status,
                        last_checked = datetime('now')
                ''', (site_id, url, status))
                
                results['urls'].append({'url': url, 'status': status, 'indexed': is_indexed})
                
                if is_indexed:
                    results['indexed'] += 1
                else:
                    results['not_indexed'] += 1
                    
            except HttpError as e:
                results['urls'].append({'url': url, 'status': 'error', 'indexed': False})
        
        conn.commit()
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
    
    return jsonify(results)


@app.route("/api/sites/<int:site_id>/submit", methods=["POST"])
def api_submit_urls(site_id):
    """Submit unindexed URLs for indexing."""
    credentials = get_credentials()
    if not credentials:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    urls = data.get('urls', [])
    
    if not urls:
        return jsonify({'error': 'No URLs to submit'}), 400
    
    results = {'submitted': 0, 'failed': 0}
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        service = build('indexing', 'v3', credentials=credentials)
        
        for url in urls[:200]:  # Respect 200/day limit
            try:
                service.urlNotifications().publish(
                    body={'url': url, 'type': 'URL_UPDATED'}
                ).execute()
                
                # Log submission
                cursor.execute('''
                    INSERT INTO submissions (site_id, url, result)
                    VALUES (?, ?, 'success')
                ''', (site_id, url))
                
                # Update URL record
                cursor.execute('''
                    UPDATE urls SET last_submitted = datetime('now')
                    WHERE site_id = ? AND url = ?
                ''', (site_id, url))
                
                results['submitted'] += 1
                
            except HttpError as e:
                cursor.execute('''
                    INSERT INTO submissions (site_id, url, result)
                    VALUES (?, ?, ?)
                ''', (site_id, url, f'error: {str(e)}'))
                results['failed'] += 1
        
        conn.commit()
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
    
    return jsonify(results)



@app.route("/api/metadata", methods=["POST"])
def api_metadata():
    """Fetch metadata (title, favicon, image) for a given URL."""
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
        
    if not url.startswith('http'):
        url = 'https://' + url
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Title
        title = None
        if soup.title:
            title = soup.title.string
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content')
        
        # Description
        description = None
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        if desc_meta:
            description = desc_meta.get('content')
        if not description:
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                description = og_desc.get('content')

        # Favicon
        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        favicon = None
        if icon_link:
            favicon = urljoin(url, icon_link.get('href'))
        else:
            favicon = urljoin(url, '/favicon.ico')
            
        # Image
        image = None
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image = urljoin(url, og_image.get('content'))
            
        return jsonify({
            'title': title,
            'description': description,
            'favicon': favicon,
            'image': image,
            'url': url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  AutoGSC SaaS Version")
    print("  Open: http://localhost:8080")
    print("="*50)
    
    if not oauth_exists():
        print("""
⚠️  OAuth not configured yet!

To enable Google Login:
1. Go to https://console.cloud.google.com
2. APIs & Services → Credentials
3. Create OAuth Client ID (Web application)
4. Add redirect URI: http://localhost:8080/oauth/callback
5. Download JSON → Save as client_secret.json
""")
    
    app.run(debug=True, port=8080)
