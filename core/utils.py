"""
Core utility functions for formatting and common system helpers.
"""

from datetime import datetime


def format_timestamp(dt: datetime | None = None) -> str:
    """Format a datetime object to a readable timestamp string (%Y-%m-%d_Time_%H-%M-%S).

    Args:
        dt: Optional datetime instance (defaults to datetime.now()).

    Returns:
        str: Formatted readable timestamp string (e.g., '2026-08-19_Time_14-30-00').
    """
    target_dt = dt or datetime.now()
    return target_dt.strftime("%Y-%m-%d_Time_%H-%M-%S")
