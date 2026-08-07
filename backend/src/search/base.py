"""Provider-independent web search interface."""

from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    content: str = ""
    source: Optional[str] = None
    score: float = 0.0


class SearchError(Exception):
    """Base class for all search provider failures."""


class SearchConfigError(SearchError):
    """Missing/invalid configuration: unknown provider, missing API key."""


class SearchProviderError(SearchError):
    """The upstream search provider call failed."""


class SearchTimeoutError(SearchError):
    """The search request timed out."""


class SearchProvider(ABC):
    #: True when `content` on returned SearchResults is already full page
    #: text (so callers can skip a separate safe-browser fetch step).
    provides_full_content: bool = False

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        raise NotImplementedError
