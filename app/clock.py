"""Single source of 'now' — timezone-aware UTC (avoids the deprecated utcnow)."""
from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
