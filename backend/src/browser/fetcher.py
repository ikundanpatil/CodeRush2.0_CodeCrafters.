"""Raw HTTP fetching with URL-safety (SSRF) enforcement.

Only plain http(s) requests to public hosts are allowed. No JavaScript
execution, no downloaded-code execution, no shell access -- this module does
a single safe GET and returns raw bytes.
"""

import ipaddress
import socket
from typing import Tuple
from urllib.parse import urljoin, urlsplit

import requests

from src.browser.base import BrowserFetchError, BrowserHTTPError, BrowserTimeoutError, BrowserURLError

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}

DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_BYTES = 300_000
DEFAULT_MAX_REDIRECTS = 3
USER_AGENT = "EvoResearchBot/1.0 (+safe-research-fetcher)"


def _is_unsafe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_url(url: str) -> str:
    """Validate a URL against SSRF/scheme rules. Returns the hostname on success."""
    parts = urlsplit(url)

    scheme = (parts.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise BrowserURLError(f"Unsupported URL scheme '{scheme or '(none)'}'. Only http/https are allowed.")

    hostname = (parts.hostname or "").lower()
    if not hostname:
        raise BrowserURLError("URL has no hostname.")

    if hostname in BLOCKED_HOSTNAMES:
        raise BrowserURLError(f"Access to '{hostname}' is blocked.")

    try:
        ip_direct = ipaddress.ip_address(hostname)
        if _is_unsafe_ip(ip_direct):
            raise BrowserURLError(f"Access to private/internal address '{hostname}' is blocked.")
    except ValueError:
        pass  # not a literal IP; resolve it below

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise BrowserURLError(f"Could not resolve host '{hostname}': {exc}") from exc

    if not addr_infos:
        raise BrowserURLError(f"Could not resolve host '{hostname}'.")

    for info in addr_infos:
        raw_ip = info[4][0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        if _is_unsafe_ip(ip):
            raise BrowserURLError(f"Host '{hostname}' resolves to a blocked private/internal address.")

    return hostname


def fetch(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
) -> Tuple[bytes, str, int, bool]:
    """Fetch a URL safely. Returns (body_bytes, content_type, status_code, truncated).

    Redirects are followed manually (never automatically) so every hop is
    re-validated against the SSRF rules -- an attacker cannot bypass URL
    validation by redirecting a safe URL to an internal address.
    """
    current_url = url
    validate_url(current_url)

    for _ in range(max_redirects + 1):
        try:
            response = requests.get(
                current_url,
                timeout=timeout,
                stream=True,
                allow_redirects=False,
                headers={"User-Agent": USER_AGENT},
            )
        except requests.exceptions.Timeout as exc:
            raise BrowserTimeoutError(f"Timed out fetching '{current_url}': {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise BrowserFetchError(f"Network error fetching '{current_url}': {exc}") from exc

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise BrowserFetchError(f"Redirect from '{current_url}' had no Location header.")
            current_url = urljoin(current_url, location)
            validate_url(current_url)
            continue

        if response.status_code >= 400:
            response.close()
            raise BrowserHTTPError(f"HTTP {response.status_code} fetching '{current_url}'.")

        content_type = response.headers.get("Content-Type", "")
        chunks = []
        total = 0
        truncated_flag = False
        try:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                chunks.append(chunk)
                total += len(chunk)
                if total >= max_bytes:
                    truncated_flag = True
                    break
        finally:
            response.close()

        body = b"".join(chunks)[:max_bytes]
        status_code = response.status_code
        return body, content_type, status_code, truncated_flag

    raise BrowserFetchError(f"Too many redirects starting from '{url}'.")
