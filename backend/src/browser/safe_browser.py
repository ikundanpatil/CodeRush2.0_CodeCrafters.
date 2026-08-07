"""High-level safe-browsing entry point: fetch a URL and return structured,
readable page content. Delegates URL safety + raw fetching to fetcher.py.

Never executes scripts found on the page, never executes downloaded content,
and never shells out. The returned text is inert data -- callers (the
orchestrator) are responsible for running it through the prompt-injection
guard before it is ever used in an LLM prompt.
"""

from html.parser import HTMLParser

from src.browser.base import PageContent
from src.browser.fetcher import DEFAULT_MAX_BYTES, DEFAULT_TIMEOUT, fetch

MAX_TEXT_CHARS = 6000

_SKIP_TAGS = {"script", "style", "noscript", "template"}


class _TextExtractor(HTMLParser):
    """Minimal, dependency-free HTML-to-text extractor. Does not execute
    scripts or evaluate any markup -- it only reads text nodes."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._title_chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._in_title:
            self._title_chunks.append(data)
            return
        stripped = data.strip()
        if stripped:
            self._chunks.append(stripped)

    @property
    def text(self) -> str:
        return " ".join(self._chunks)

    @property
    def title(self) -> str:
        return " ".join(self._title_chunks).strip()


def _extract_text(html_bytes: bytes) -> tuple[str, str]:
    html_text = html_bytes.decode("utf-8", errors="replace")
    parser = _TextExtractor()
    try:
        parser.feed(html_text)
    except Exception:
        pass
    return parser.title, parser.text


class SafeBrowser:
    """Fetches a URL and returns readable page content, safely."""

    def fetch_page(
        self,
        url: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> PageContent:
        body, content_type, status_code, truncated = fetch(url, timeout=timeout, max_bytes=max_bytes)

        if "html" in content_type.lower() or not content_type:
            title, text = _extract_text(body)
        else:
            title, text = "", body.decode("utf-8", errors="replace")

        text = " ".join(text.split())
        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS]
            truncated = True

        return PageContent(
            url=url,
            title=title,
            text=text,
            content_type=content_type,
            status_code=status_code,
            truncated=truncated,
        )


safe_browser = SafeBrowser()
