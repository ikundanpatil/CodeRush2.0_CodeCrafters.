import os

from src.search.base import SearchConfigError, SearchProvider
from src.search.providers.mock import MockSearchProvider
from src.search.providers.tavily import TavilySearchProvider

_PROVIDERS = {
    "mock": MockSearchProvider,
    "tavily": TavilySearchProvider,
}


def get_search_provider(provider: str | None = None) -> SearchProvider:
    """Return a SearchProvider for the requested provider.

    Reads SEARCH_PROVIDER from the environment when provider is not given.
    Defaults to "mock" so the app and test suite work offline out of the box.
    """
    name = (provider or os.getenv("SEARCH_PROVIDER") or "mock").strip().lower()
    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        raise SearchConfigError(
            f"Unknown SEARCH_PROVIDER '{name}'. Valid options: {', '.join(sorted(_PROVIDERS))}."
        )
    return provider_cls()
