#!/usr/bin/env python3
"""
AutoGSC - Automatic Google Search Console Indexer

A tool that automatically detects unindexed pages and submits them
to Google's Indexing API.

Usage:
    python main.py scan      # Scan sitemap and check indexing status
    python main.py submit    # Submit unindexed URLs
    python main.py status    # Show current status
    python main.py run       # Full automated run (scan + submit)
"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config import SITEMAP_URL, SITE_URL, DAILY_SUBMISSION_LIMIT
from sitemap_parser import get_all_urls
from database import upsert_url, get_unindexed_urls, get_stats, get_today_submission_count
from gsc_client import GSCClient
from indexing_client import IndexingClient

console = Console()


@click.group()
def cli():
    """AutoGSC - Automatic Google Search Console Indexer"""
    pass


@cli.command()
@click.option('--sitemap', default=None, help='Sitemap URL (overrides config)')
def scan(sitemap):
    """Scan sitemap and check indexing status for all URLs."""
    sitemap_url = sitemap or SITEMAP_URL
    
    console.print(Panel.fit(
        f"[bold blue]Scanning: {sitemap_url}[/bold blue]",
        title="AutoGSC Scan"
    ))
    
    # Fetch all URLs from sitemap
    urls = get_all_urls(sitemap_url)
    
    if not urls:
        console.print("[red]No URLs found in sitemap![/red]")
        return
    
    # Initialize GSC client
    try:
        gsc = GSCClient()
    except Exception as e:
        console.print(f"[red]Failed to connect to GSC: {e}[/red]")
        console.print("[yellow]Make sure your service-account.json is in the project folder.[/yellow]")
        return
    
    # Check each URL
    indexed_count = 0
    not_indexed_count = 0
    error_count = 0
    
    console.print(f"\n[cyan]Checking indexing status for {len(urls)} URLs...[/cyan]\n")
    
    for i, url in enumerate(urls, 1):
        status = gsc.get_indexing_status(url)
        upsert_url(url, status)
        
        if status == 'indexed':
            indexed_count += 1
            symbol = "[green]✓[/green]"
        elif status == 'error':
            error_count += 1
            symbol = "[yellow]?[/yellow]"
        else:
            not_indexed_count += 1
            symbol = "[red]✗[/red]"
        
        console.print(f"  {symbol} [{i}/{len(urls)}] {url[:60]}... -> {status}")
    
    # Summary
    console.print("\n" + "="*60)
    console.print(f"[green]Indexed:[/green] {indexed_count}")
    console.print(f"[red]Not Indexed:[/red] {not_indexed_count}")
    console.print(f"[yellow]Errors:[/yellow] {error_count}")
    console.print("="*60)


@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be submitted without actually submitting')
@click.option('--limit', default=None, type=int, help='Max URLs to submit (default: use daily quota)')
def submit(dry_run, limit):
    """Submit unindexed URLs to Google Indexing API."""
    console.print(Panel.fit(
        "[bold blue]Submitting Unindexed URLs[/bold blue]",
        title="AutoGSC Submit"
    ))
    
    # Get unindexed URLs from database
    unindexed = get_unindexed_urls()
    
    if not unindexed:
        console.print("[green]No unindexed URLs to submit![/green]")
        return
    
    console.print(f"[cyan]Found {len(unindexed)} unindexed URLs[/cyan]")
    
    # Apply limit if specified
    if limit:
        unindexed = unindexed[:limit]
        console.print(f"[yellow]Limited to {limit} URLs[/yellow]")
    
    # Initialize Indexing client
    try:
        indexer = IndexingClient()
    except Exception as e:
        console.print(f"[red]Failed to connect to Indexing API: {e}[/red]")
        return
    
    # Check quota
    remaining = indexer.get_remaining_quota()
    console.print(f"[cyan]Remaining daily quota: {remaining}/{DAILY_SUBMISSION_LIMIT}[/cyan]\n")
    
    if remaining == 0 and not dry_run:
        console.print("[yellow]Daily quota exhausted. Try again tomorrow![/yellow]")
        return
    
    # Submit
    results = indexer.submit_batch(unindexed, dry_run=dry_run)
    
    # Summary
    console.print("\n" + "="*60)
    console.print(f"[green]Submitted:[/green] {results['submitted']}")
    console.print(f"[red]Failed:[/red] {results['failed']}")
    console.print(f"[yellow]Skipped (quota):[/yellow] {results['skipped']}")
    console.print("="*60)


@cli.command()
def status():
    """Show current status and statistics."""
    stats = get_stats()
    today_used = get_today_submission_count()
    
    table = Table(title="AutoGSC Status", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Site", SITE_URL)
    table.add_row("Total URLs tracked", str(stats['total_urls']))
    table.add_row("Indexed", str(stats['indexed']))
    table.add_row("Not Indexed", str(stats['unindexed']))
    table.add_row("Today's Submissions", f"{today_used}/{DAILY_SUBMISSION_LIMIT}")
    table.add_row("Total Submissions (all time)", str(stats['total_submissions']))
    
    console.print(table)


@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be done without actually doing it')
def run(dry_run):
    """Full automated run: scan sitemap and submit unindexed URLs."""
    console.print(Panel.fit(
        "[bold blue]AutoGSC Full Run[/bold blue]",
        title="🚀 AutoGSC"
    ))
    
    # Step 1: Scan
    console.print("\n[bold]Step 1: Scanning sitemap...[/bold]\n")
    
    urls = get_all_urls(SITEMAP_URL)
    if not urls:
        console.print("[red]No URLs found in sitemap![/red]")
        return
    
    try:
        gsc = GSCClient()
    except Exception as e:
        console.print(f"[red]Failed to connect to GSC: {e}[/red]")
        return
    
    not_indexed = []
    for url in urls:
        status = gsc.get_indexing_status(url)
        upsert_url(url, status)
        if status != 'indexed' and status != 'error':
            not_indexed.append(url)
            console.print(f"  [red]✗[/red] {url[:70]}...")
        else:
            console.print(f"  [green]✓[/green] {url[:70]}...")
    
    console.print(f"\n[cyan]Found {len(not_indexed)} unindexed URLs[/cyan]")
    
    if not not_indexed:
        console.print("[green]All URLs are indexed! Nothing to do.[/green]")
        return
    
    # Step 2: Submit
    console.print("\n[bold]Step 2: Submitting unindexed URLs...[/bold]\n")
    
    try:
        indexer = IndexingClient()
    except Exception as e:
        console.print(f"[red]Failed to connect to Indexing API: {e}[/red]")
        return
    
    results = indexer.submit_batch(not_indexed, dry_run=dry_run)
    
    # Final summary
    console.print("\n" + "="*60)
    console.print(Panel.fit(
        f"[green]Submitted: {results['submitted']}[/green]\n"
        f"[red]Failed: {results['failed']}[/red]\n"
        f"[yellow]Skipped: {results['skipped']}[/yellow]",
        title="Run Complete"
    ))


if __name__ == "__main__":
    cli()
