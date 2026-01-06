"""
pycalbuddy - small wrapper around icalBuddy and AppleScript for macOS Calendar access.
"""

from .models import Event
from .service import add_event, list_daily_events, list_weekly_events, update_event

__all__ = [
    "Event",
    "add_event",
    "list_daily_events",
    "list_weekly_events",
    "update_event",
]
