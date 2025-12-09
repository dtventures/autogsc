"""
Vercel serverless function entry point
Handles requests at /autogsc/* path
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set application root for subpath deployment
os.environ['APPLICATION_ROOT'] = '/autogsc'
os.environ['SCRIPT_NAME'] = '/autogsc'

from app_oauth import app

# Vercel expects a handler function
def handler(request):
    """Vercel serverless function handler."""
    return app(request.environ, request.start_response)

# Export for Vercel
handler = app

