import httpx
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, urlparse
import asyncio
from typing import List, Dict, Set

logger = logging.getLogger(__name__)

async def get_links(url: str, html: str, base_domain: str) -> List[str]:
    """Extracts all internal links from the HTML content."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        link = urljoin(url, a["href"])
        parsed_link = urlparse(link)
        # Only include links that belong to the same domain and are http/https
        if parsed_link.netloc == base_domain and parsed_link.scheme in ["http", "https"]:
            # Remove fragments
            link = link.split("#")[0]
            links.append(link)
    return list(set(links))

def clean_html(html: str) -> str:
    """Cleans HTML content and returns stripped text."""
    soup = BeautifulSoup(html, "html.parser")
    for script_or_style in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        script_or_style.decompose()
    
    text = soup.get_text(separator=" ", strip=True)
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return " ".join(chunk for chunk in chunks if chunk)

async def scrape_website(start_url: str, max_depth: int = 3, max_pages: int = 50) -> List[Dict[str, str]]:
    """
    Scrapes the website using BFS up to max_depth.
    Returns a list of dictionaries with 'url' and 'content'.
    """
    base_domain = urlparse(start_url).netloc
    queue = [(start_url, 0)]
    visited = {start_url}
    results = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        while queue and len(results) < max_pages:
            current_url, depth = queue.pop(0)
            
            try:
                logger.info(f"Scraping: {current_url} at depth {depth}")
                response = await client.get(current_url, headers=headers)
                response.raise_for_status()
                html = response.text
                
                content = clean_html(html)
                if content:
                    results.append({"url": current_url, "content": content})
                
                if depth < max_depth:
                    links = await get_links(current_url, html, base_domain)
                    for link in links:
                        if link not in visited:
                            visited.add(link)
                            queue.append((link, depth + 1))
                            
            except Exception as e:
                logger.error(f"Error scraping {current_url}: {e}")
                continue
                
    return results

