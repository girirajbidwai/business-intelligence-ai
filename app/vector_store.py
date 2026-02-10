import os
import re
import hashlib
from typing import List, Dict
from urllib.parse import urlparse
from pinecone import Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
import time

logger = logging.getLogger(__name__)


def get_index_name(url: str) -> str:
    """Derives a unique, valid Pinecone index name from a URL.
    
    Pinecone rules: lowercase, alphanumeric + hyphens, max 45 chars,
    must start and end with alphanumeric.
    """
    domain = urlparse(url).netloc.lower()
    domain = domain.split(":")[0]  # Remove port
    # Hash for uniqueness, take first 8 chars
    url_hash = hashlib.md5(domain.encode()).hexdigest()[:8]
    # Clean domain: keep only lowercase alphanumeric
    clean = re.sub(r'[^a-z0-9]', '-', domain).strip('-')
    # Truncate and build name
    name = f"idx-{clean}-{url_hash}"
    # Ensure max 45 chars
    name = name[:45].rstrip('-')
    return name


class VectorStoreManager:
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.pc = Pinecone(api_key=self.api_key) if self.api_key else None

    def _ensure_index(self, index_name: str):
        """Ensures a Pinecone Inference index exists for the given name."""
        if not self.pc:
            raise ValueError("Pinecone client not initialized. Check PINECONE_API_KEY.")

        if self.pc.has_index(index_name):
            desc = self.pc.describe_index(index_name)
            # Check if it's an inference index (has embed config)
            if hasattr(desc, 'embed') and desc.embed:
                logger.info(f"Index {index_name} already exists with inference. Ready.")
                return
            else:
                # Standard index - delete and recreate as inference
                logger.warning(f"Index {index_name} is standard. Deleting to recreate with inference...")
                self.pc.delete_index(index_name)
                while self.pc.has_index(index_name):
                    time.sleep(1)

        logger.info(f"Creating NEW inference index: {index_name}")
        try:
            self.pc.create_index_for_model(
                name=index_name,
                cloud="aws",
                region="us-east-1",
                embed={
                    "model": "llama-text-embed-v2",
                    "field_map": {"text": "chunk_text"}
                }
            )
            # Wait for index to be ready
            while not self.pc.describe_index(index_name).status['ready']:
                time.sleep(1)
            logger.info(f"Index {index_name} is ready.")
        except Exception as e:
            if "quota" in str(e).lower() or "MAXIMUM" in str(e).upper():
                logger.error(
                    f"QUOTA EXCEEDED: Free tier allows only 1 index. "
                    f"Delete existing indexes in your Pinecone dashboard. Error: {e}"
                )
            raise e

    async def index_website_content(self, website_data: List[Dict[str, str]]):
        """Chunks website content and upserts records into a dedicated Pinecone Inference index."""
        if not self.pc or not website_data:
            return

        main_url = website_data[0]["url"]
        index_name = get_index_name(main_url)

        logger.info(f"Indexing website into dedicated DB: {index_name}")
        self._ensure_index(index_name)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )

        index = self.pc.Index(index_name)

        for page in website_data:
            url = page.get("url", "unknown")
            content = page.get("content", "")
            if not content:
                logger.warning(f"Skipping empty content for URL: {url}")
                continue

            chunks = text_splitter.split_text(content)
            logger.info(f"Upserting {len(chunks)} chunks for {url}")

            # Build records in the Pinecone Inference format
            # Key: _id (string), chunk_text (the text field mapped in embed config)
            records = []
            for i, chunk in enumerate(chunks):
                records.append({
                    "_id": f"{hashlib.md5(url.encode()).hexdigest()[:12]}-{i}",
                    "chunk_text": chunk,
                    "url": url,
                })

            # Upsert using the Inference API (NOT the standard upsert)
            index.upsert_records("default", records)

        logger.info(f"Indexing complete for {index_name}")

    def query_context(self, url: str, query: str, k: int = 5) -> str:
        """Retrieves relevant context from the dedicated Inference index for the given URL."""
        if not self.pc:
            return ""

        index_name = get_index_name(url)
        if not self.pc.has_index(index_name):
            logger.warning(f"No database found for {url} (expected index: {index_name})")
            return ""

        index = self.pc.Index(index_name)

        try:
            # Search using Pinecone Inference API (NOT the standard query)
            results = index.search(
                namespace="default",
                query={
                    "top_k": k,
                    "inputs": {"text": query}
                }
            )

            context_parts = []
            for hit in results['result']['hits']:
                source_url = hit['fields'].get('url', 'unknown')
                text = hit['fields'].get('chunk_text', '')
                context_parts.append(f"Source [{source_url}]:\n{text}")

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Query error for {index_name}: {e}")
            return ""
