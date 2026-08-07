"""Safe browser interfaces: fetching an external URL and returning structured,
readable page content. See fetcher.py for URL-safety/SSRF checks and
safe_browser.py for the fetch + text-extraction orchestration."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class PageContent(BaseModel):
    url: str
    title: str = ""
    text: str = ""
    content_type: str = ""
    status_code: Optional[int] = None
    truncated: bool = False
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BrowserError(Exception):
    """Base class for all safe-browser failures."""


class BrowserURLError(BrowserError):
    """The URL failed safety validation (unsupported scheme, private/loopback IP, etc.)."""


class BrowserTimeoutError(BrowserError):
    """Fetching the page timed out."""


class BrowserHTTPError(BrowserError):
    """The server returned an HTTP error status."""


class BrowserFetchError(BrowserError):
    """A network-level error occurred while fetching the page."""
