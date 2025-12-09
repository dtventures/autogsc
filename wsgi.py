"""
WSGI entry point for production deployment
Supports subpath deployment via APPLICATION_ROOT environment variable
"""
import os
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix

from app_oauth import app as application

# Get application root from environment (e.g., '/autogsc' or '/')
application_root = os.environ.get('APPLICATION_ROOT', '/')

# If deploying at subpath, wrap the app
if application_root != '/':
    # Remove trailing slash if present
    application_root = application_root.rstrip('/')
    
    # Create a dispatcher that mounts the app at the subpath
    app = DispatcherMiddleware(
        application,  # The main Flask app
        {application_root: application}  # Mount at subpath
    )
else:
    app = application

# Fix proxy headers for proper URL generation behind reverse proxy
app = ProxyFix(app, x_proto=1, x_host=1)

# Export for WSGI servers
application = app

