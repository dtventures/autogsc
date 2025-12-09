"""
Vercel serverless function for /autogsc path
This handles all requests to lighthouselaunch.com/autogsc/*
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set environment for subpath deployment
os.environ['APPLICATION_ROOT'] = '/autogsc'
os.environ['SCRIPT_NAME'] = '/autogsc'

# Import Flask app after setting environment
from app_oauth import app

# Vercel Python runtime expects the app to be exported directly
# The @vercel/python builder will wrap this appropriately

