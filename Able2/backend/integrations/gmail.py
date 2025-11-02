"""
Gmail integration stub for Able2.
Full implementation in Phase 2.
"""

from typing import List, Dict, Any
from backend.core import get_logger

logger = get_logger("gmail_integration")


class GmailClient:
    """Gmail API client stub for Phase 2."""

    def __init__(self):
        """Initialize Gmail client."""
        logger.info("Gmail client initialized (Phase 1 stub)")

    async def authenticate(self) -> bool:
        """Authenticate with Gmail API."""
        logger.info("Gmail authentication (Phase 2)")
        return False

    async def fetch_threads(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch email threads."""
        logger.info("Fetch Gmail threads (Phase 2)")
        return []

    async def search_emails(self, query: str) -> List[Dict[str, Any]]:
        """Search emails."""
        logger.info(f"Search Gmail: {query} (Phase 2)")
        return []

    async def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email."""
        logger.info(f"Send Gmail to {to} (Phase 2)")
        return {"sent": False, "message_id": None}
