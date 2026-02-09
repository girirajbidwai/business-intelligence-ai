import httpx
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

async def scrape_homepage(url: str) -> str:
    """
    Scrapes the content of a homepage and returns cleaned text.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            raise ValueError(f"Failed to fetch the website: {str(e)}")

    soup = BeautifulSoup(html, "html.parser")
    
    # Remove script and style elements
    for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
        script_or_style.decompose()

    # Get text
    text = soup.get_text(separator=" ", strip=True)
    
    # Basic cleaning: remove extra whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = " ".join(chunk for chunk in chunks if chunk)
    
    return text[:10000]  # Limit context for LLM
