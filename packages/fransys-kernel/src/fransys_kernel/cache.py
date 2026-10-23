"""The one per-digest cache every derived result of a `Model` uses (model-0067)."""

import dataclasses
import functools
from typing import Any, Final
lazy from collections.abc import Callable

# Results kept by each `digest_cached` builder, least recently used out first. Each entry keeps
# its whole `Model` alive, so the bound is also a bound on memory.
DIGEST_CACHE_SIZE: Final = 8


@dataclasses.dataclass(frozen=True, slots=True)
class ByDigest:
    """A `Model` that the cache tells apart by its digest alone.

    The cache tells models apart by digest alone and keeps the model alive for the build.
    """

    digest: str
    model: Any = dataclasses.field(compare=False)


class DigestCached[M, T]:
    """A builder `M -> T`, called through a cache of its last `maxsize` results by digest.

    Equal digests give the identical result, each entry keeping its `Model` alive. An `M` with
    no `digest` (a `Draft.tables()` view, which hashes nothing) is built uncached, every call.
    """

    def __init__(self, build: Callable[[M], T], maxsize: int) -> None:
        """Wrap `build`, keeping its name and docstring."""
        self._build = build
        self._cached = functools.lru_cache(maxsize=maxsize)(lambda keyed: build(keyed.model))
        functools.update_wrapper(self, build)

    def __call__(self, model: M) -> T:
        """The result for `model.digest`: cached, or built now; a view with no digest: built now."""
        digest = getattr(model, "digest", None)
        if digest is None:
            return self._build(model)
        return self._cached(ByDigest(digest, model))

    def cache_clear(self) -> None:
        """Forget every result and the build count: the next call of each digest builds again."""
        self._cached.cache_clear()

    @property
    def builds(self) -> int:
        """How many times the builder has run since the last `cache_clear`."""
        return self._cached.cache_info().misses


def digest_cached[M, T](maxsize: int) -> Callable[[Callable[[M], T]], DigestCached[M, T]]:
    """Decorate a builder `M -> T` so it is cached on `model.digest`, `maxsize` results kept."""

    def decorate(build: Callable[[M], T]) -> DigestCached[M, T]:
        return DigestCached(build, maxsize)

    return decorate
