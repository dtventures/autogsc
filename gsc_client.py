"""
Google Search Console API Client
Checks indexing status of URLs via the URL Inspection API.
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, Dict
from rich.console import Console

from config import SERVICE_ACCOUNT_FILE, SITE_URL

console = Console()

# API Scopes
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']


class GSCClient:
    """Google Search Console API Client."""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google APIs using service account."""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE,
                scopes=SCOPES
            )
            self.service = build('searchconsole', 'v1', credentials=self.credentials)
            console.print("[green]✓ Connected to Google Search Console API[/green]")
        except Exception as e:
            console.print(f"[red]Failed to authenticate with GSC: {e}[/red]")
            raise
    
    def inspect_url(self, url: str) -> Optional[Dict]:
        """
        Inspect a URL to check its indexing status.
        
        Returns dict with:
        - verdict: 'PASS', 'PARTIAL', 'FAIL', 'NEUTRAL'
        - coverageState: 'Submitted and indexed', 'Discovered - currently not indexed', etc.
        """
        try:
            request_body = {
                'inspectionUrl': url,
                'siteUrl': SITE_URL
            }
            
            response = self.service.urlInspection().index().inspect(
                body=request_body
            ).execute()
            
            result = response.get('inspectionResult', {})
            index_status = result.get('indexStatusResult', {})
            
            return {
                'url': url,
                'verdict': index_status.get('verdict', 'UNKNOWN'),
                'coverageState': index_status.get('coverageState', 'Unknown'),
                'robotsTxtState': index_status.get('robotsTxtState', 'UNKNOWN'),
                'indexingState': index_status.get('indexingState', 'UNKNOWN'),
                'lastCrawlTime': index_status.get('lastCrawlTime'),
                'pageFetchState': index_status.get('pageFetchState', 'UNKNOWN'),
            }
            
        except HttpError as e:
            console.print(f"[red]Error inspecting URL {url}: {e}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Unexpected error inspecting {url}: {e}[/red]")
            return None
    
    def get_indexing_status(self, url: str) -> str:
        """
        Get simplified indexing status for a URL.
        Returns: 'indexed', 'not_indexed', 'error', or the raw coverageState
        """
        result = self.inspect_url(url)
        
        if not result:
            return 'error'
        
        coverage = result.get('coverageState', '')
        
        # Map to simplified status
        if 'Submitted and indexed' in coverage or result.get('verdict') == 'PASS':
            return 'indexed'
        elif 'not indexed' in coverage.lower():
            return coverage  # Return the specific reason
        else:
            return coverage
    
    def list_sitemaps(self) -> list:
        """List all sitemaps submitted to GSC."""
        try:
            response = self.service.sitemaps().list(siteUrl=SITE_URL).execute()
            return response.get('sitemap', [])
        except HttpError as e:
            console.print(f"[red]Error listing sitemaps: {e}[/red]")
            return []


if __name__ == "__main__":
    # Quick test
    client = GSCClient()
    print("GSC Client initialized successfully!")
    
    # Test URL inspection (replace with a real URL from your site)
    # result = client.inspect_url("https://yoursite.com/some-page")
    # print(result)
