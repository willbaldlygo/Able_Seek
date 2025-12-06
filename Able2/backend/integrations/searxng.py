"""
SearxNG web search integration for Able2.
Full implementation in Phase 3.
"""

from typing import List, Dict, Any
import requests
from backend.core import settings, get_logger

logger = get_logger("searxng_integration")


class SearxNGClient:
    """SearxNG search client for private web search."""

    def __init__(self):
        """Initialize SearxNG client."""
        self.base_url = settings.searxng_url
        self.enabled = settings.searxng_enabled
        logger.info(f"SearxNG client initialized (enabled={self.enabled})")

    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search web using SearxNG.

        Args:
            query: Search query
            max_results: Max number of results

        Returns:
            List of search results
        """
        if not self.enabled:
            logger.warning("SearxNG is disabled")
            return []

        logger.info(f"SearxNG search: {query}")

        try:
            # SearxNG JSON API
            params = {
                "q": query,
                "format": "json",
                "pageno": 1
            }

            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "engine": item.get("engine", ""),
                    "score": item.get("score", 0)
                })

            logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"SearxNG search failed: {str(e)}")
            return []

    def is_available(self) -> bool:
        """Check if SearxNG is available."""
        if not self.enabled:
            return False

        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except (requests.RequestException, ConnectionError, TimeoutError):
            return False
