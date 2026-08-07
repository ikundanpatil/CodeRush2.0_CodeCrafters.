from src.browser.base import (
    BrowserError,
    BrowserFetchError,
    BrowserHTTPError,
    BrowserTimeoutError,
    BrowserURLError,
    PageContent,
)
from src.browser.safe_browser import SafeBrowser

# Note: intentionally not re-exporting the `safe_browser` singleton here --
# that name would shadow the `src.browser.safe_browser` submodule itself on
# this package's namespace, which breaks `monkeypatch.setattr` (and any
# other attribute-path-based lookup) targeting the submodule. Import the
# singleton directly: `from src.browser.safe_browser import safe_browser`.

__all__ = [
    "SafeBrowser",
    "PageContent",
    "BrowserError",
    "BrowserURLError",
    "BrowserTimeoutError",
    "BrowserHTTPError",
    "BrowserFetchError",
]
