"""The one per-digest cache every derived result of a `Model` uses (model-0067)."""

import dataclasses
import functools
from typing import Final
lazy from collections.abc import Callable

lazy from .model import Model

# Results kept by each `digest_cached` builder, least recently used out first. Each entry keeps
# its whole `Model` alive, so the bound is also a bound on memory.
DIGEST_CACHE_SIZE: Final = 8


@dataclasses.dataclass(frozen=True, slots=True)
class ByDigest:
    """A `Model` that the cache tells apart by its digest alone.

    The cache tells models apart by digest alone and keeps the model alive for the build.
    """

    digest: str
    model: Model = dataclasses.field(compare=False)


class DigestCached[T]:
    """A builder `Model -> T`, called through a cache of its last `maxsize` results by digest.

    Two models with an equal digest get the identical result; a new digest builds afresh. Each
    entry keeps its `Model` alive. Identity is guaranteed within one thread.
    """

    def __init__(self, build: Callable[[Model], T], maxsize: int) -> None:
        """Wrap `build`, keeping its name and docstring."""
        self._cached = functools.lru_cache(maxsize=maxsize)(lambda keyed: build(keyed.model))
        functools.update_wrapper(self, build)

    def __call__(self, model: Model) -> T:
        """The result for `model.digest`: cached, or built now."""
        return self._cached(ByDigest(model.digest, model))

    def cache_clear(self) -> None:
        """Forget every result and the build count: the next call of each digest builds again."""
        self._cached.cache_clear()

    @property
    def builds(self) -> int:
        """How many times the builder has run since the last `cache_clear`."""
        return self._cached.cache_info().misses


def digest_cached[T](maxsize: int) -> Callable[[Callable[[Model], T]], DigestCached[T]]:
    """Decorate a builder `Model -> T` so it is cached on `model.digest`, `maxsize` results kept."""

    def decorate(build: Callable[[Model], T]) -> DigestCached[T]:
        return DigestCached(build, maxsize)

    return decorate
