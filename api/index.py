"""
Vercel serverless function entry point
For subdomain deployment: autogsc.lighthouselaunch.com
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import Flask app (no subpath needed for subdomain)
from app_oauth import app

# Vercel Python runtime expects the app to be exported directly
# The @vercel/python builder will wrap this appropriately
