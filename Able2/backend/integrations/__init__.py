"""
External integrations for Able2.
Gmail, Calendar, SearxNG stubs for Phase 1.
"""

from .gmail import GmailClient
from .calendar import CalendarClient
from .searxng import SearxNGClient

__all__ = [
    "GmailClient",
    "CalendarClient",
    "SearxNGClient",
]
