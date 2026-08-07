import os
from typing import List

import requests

from src.search.base import (
    SearchConfigError,
    SearchProvider,
    SearchProviderError,
    SearchResult,
    SearchTimeoutError,
)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilySearchProvider(SearchProvider):
    """Real web search via Tavily's search API (designed for AI agents)."""

    def __init__(self, api_key: str | None = None, timeout: float = 15.0):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise SearchConfigError(
                "TAVILY_API_KEY is not set. Set it in your environment or backend/.env."
            )
        self.timeout = timeout

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max(1, min(max_results, 20)),
            "include_answer": False,
            "include_raw_content": False,
        }
        try:
            response = requests.post(TAVILY_SEARCH_URL, json=payload, timeout=self.timeout)
        except requests.exceptions.Timeout as exc:
            raise SearchTimeoutError(f"Tavily search timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise SearchProviderError(f"Network error contacting Tavily: {exc}") from exc

        if response.status_code == 401:
            raise SearchConfigError(f"Invalid Tavily API key: {response.text}")
        if response.status_code == 429:
            raise SearchProviderError(f"Tavily rate limit exceeded: {response.text}")
        if response.status_code >= 400:
            raise SearchProviderError(f"Tavily search failed ({response.status_code}): {response.text}")

        try:
            data = response.json()
        except ValueError as exc:
            raise SearchProviderError(f"Tavily returned a non-JSON response: {exc}") from exc

        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                title=item.get("title", "Untitled"),
                url=item.get("url", ""),
                content=item.get("content", ""),
                source="Tavily",
                score=float(item.get("score", 0.0) or 0.0),
            ))
        return results
