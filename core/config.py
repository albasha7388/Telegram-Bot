"""
Core configuration module for system-wide environment variables and constants.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

raw_archive_channel_id: Optional[str] = os.getenv("ARCHIVE_CHANNEL_ID")
ARCHIVE_CHANNEL_ID: Optional[int] = None
if raw_archive_channel_id and raw_archive_channel_id.strip():
    try:
        ARCHIVE_CHANNEL_ID = int(raw_archive_channel_id.strip())
    except ValueError:
        ARCHIVE_CHANNEL_ID = None
