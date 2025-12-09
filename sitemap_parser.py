"""
Sitemap Parser Module
Fetches and parses XML sitemaps to extract all URLs.
"""
import requests
import xml.etree.ElementTree as ET
from typing import List
from rich.console import Console

console = Console()


def fetch_sitemap(sitemap_url: str) -> str:
    """Fetch sitemap XML content from URL."""
    try:
        response = requests.get(sitemap_url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        console.print(f"[red]Error fetching sitemap: {e}[/red]")
        return ""


def parse_sitemap(xml_content: str) -> List[str]:
    """Parse sitemap XML and extract all URLs."""
    urls = []
    
    if not xml_content:
        return urls
    
    try:
        root = ET.fromstring(xml_content)
        
        # Handle namespace (sitemaps typically use this namespace)
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        
        # Check if this is a sitemap index (contains other sitemaps)
        sitemap_refs = root.findall(".//ns:sitemap/ns:loc", namespace)
        
        if sitemap_refs:
            # This is a sitemap index - recursively fetch each sitemap
            console.print(f"[yellow]Found sitemap index with {len(sitemap_refs)} sitemaps[/yellow]")
            for sitemap_ref in sitemap_refs:
                nested_url = sitemap_ref.text
                console.print(f"  Fetching: {nested_url}")
                nested_content = fetch_sitemap(nested_url)
                urls.extend(parse_sitemap(nested_content))
        else:
            # This is a regular sitemap - extract URLs
            url_elements = root.findall(".//ns:url/ns:loc", namespace)
            for url_elem in url_elements:
                if url_elem.text:
                    urls.append(url_elem.text.strip())
    
    except ET.ParseError as e:
        console.print(f"[red]Error parsing sitemap XML: {e}[/red]")
    
    return urls


def get_all_urls(sitemap_url: str) -> List[str]:
    """Main function: fetch sitemap and return all URLs."""
    console.print(f"[blue]Fetching sitemap: {sitemap_url}[/blue]")
    xml_content = fetch_sitemap(sitemap_url)
    urls = parse_sitemap(xml_content)
    console.print(f"[green]Found {len(urls)} URLs in sitemap[/green]")
    return urls


if __name__ == "__main__":
    # Quick test
    from config import SITEMAP_URL
    urls = get_all_urls(SITEMAP_URL)
    for url in urls[:10]:
        print(url)
