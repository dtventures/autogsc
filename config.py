"""
AutoGSC Configuration
Update these values with your own settings.
"""
import os

# Path to your Google Cloud Service Account JSON key file
# Download this from Google Cloud Console -> APIs & Services -> Credentials
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "service-account.json")

# Your website URL as it appears in Google Search Console
# Examples: "https://example.com" or "sc-domain:example.com"
SITE_URL = "sc-domain:lighthouselaunch.com"

# Your sitemap URL
SITEMAP_URL = "https://lighthouselaunch.com/sitemap.xml"

# Google Indexing API limit (don't change unless Google updates this)
DAILY_SUBMISSION_LIMIT = 200

# Database file for tracking submissions
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "autogsc.db")

# How many hours to wait before resubmitting a URL that failed
RESUBMIT_AFTER_HOURS = 48
