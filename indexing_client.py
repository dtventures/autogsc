"""
Google Indexing API Client
Submits URLs for indexing via the Indexing API.
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import SERVICE_ACCOUNT_FILE, DAILY_SUBMISSION_LIMIT
from database import get_today_submission_count, record_submission

console = Console()

# API Scopes for Indexing API
SCOPES = ['https://www.googleapis.com/auth/indexing']


class IndexingClient:
    """Google Indexing API Client."""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Indexing API using service account."""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE,
                scopes=SCOPES
            )
            self.service = build('indexing', 'v3', credentials=self.credentials)
            console.print("[green]✓ Connected to Google Indexing API[/green]")
        except Exception as e:
            console.print(f"[red]Failed to authenticate with Indexing API: {e}[/red]")
            raise
    
    def submit_url(self, url: str, action: str = "URL_UPDATED") -> Tuple[bool, str]:
        """
        Submit a single URL for indexing.
        
        Args:
            url: The URL to submit
            action: 'URL_UPDATED' (request indexing) or 'URL_DELETED' (request removal)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            body = {
                'url': url,
                'type': action
            }
            
            response = self.service.urlNotifications().publish(body=body).execute()
            
            # Record successful submission
            record_submission(url, 'success')
            
            return True, f"Submitted: {response.get('urlNotificationMetadata', {}).get('url', url)}"
            
        except HttpError as e:
            error_msg = str(e)
            record_submission(url, 'error', error_msg)
            return False, f"HTTP Error: {error_msg}"
        except Exception as e:
            error_msg = str(e)
            record_submission(url, 'error', error_msg)
            return False, f"Error: {error_msg}"
    
    def get_remaining_quota(self) -> int:
        """Get remaining submissions allowed today."""
        used = get_today_submission_count()
        return max(0, DAILY_SUBMISSION_LIMIT - used)
    
    def submit_batch(self, urls: List[str], dry_run: bool = False) -> Dict:
        """
        Submit multiple URLs for indexing, respecting daily limit.
        
        Args:
            urls: List of URLs to submit
            dry_run: If True, don't actually submit, just show what would be done
        
        Returns:
            Dict with 'submitted', 'failed', 'skipped' counts
        """
        remaining_quota = self.get_remaining_quota()
        
        results = {
            'submitted': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        if remaining_quota == 0:
            console.print("[yellow]Daily quota exhausted. No more submissions allowed today.[/yellow]")
            results['skipped'] = len(urls)
            return results
        
        # Only process up to remaining quota
        urls_to_process = urls[:remaining_quota]
        skipped_count = len(urls) - len(urls_to_process)
        
        if skipped_count > 0:
            console.print(f"[yellow]Will skip {skipped_count} URLs due to daily limit[/yellow]")
            results['skipped'] = skipped_count
        
        if dry_run:
            console.print("[cyan]DRY RUN - No actual submissions will be made[/cyan]")
            for url in urls_to_process:
                console.print(f"  Would submit: {url}")
            results['submitted'] = len(urls_to_process)
            return results
        
        # Submit with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Submitting URLs...", total=len(urls_to_process))
            
            for url in urls_to_process:
                success, message = self.submit_url(url)
                
                if success:
                    results['submitted'] += 1
                    console.print(f"[green]✓[/green] {url}")
                else:
                    results['failed'] += 1
                    results['errors'].append({'url': url, 'error': message})
                    console.print(f"[red]✗[/red] {url}: {message}")
                
                progress.advance(task)
        
        return results


if __name__ == "__main__":
    # Quick test
    client = IndexingClient()
    print(f"Remaining quota today: {client.get_remaining_quota()}")
