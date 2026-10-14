"""A derive query cached per model digest and per argument (O25).

The overview engine reads each unit's level, its folds and its boxes' text for several views. `Memo`
builds each once per digest and argument; two models with an equal digest share the result.
"""

import functools
from typing import Any, Concatenate
lazy from collections.abc import Callable

from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
lazy from fransys_model.kernel import Model

__all__ = ["Memo"]


class Memo[**A, T]:
    """A builder `(Model, *args) -> T`, built once for each digest and `args`."""

    def __init__(self, build: Callable[Concatenate[Model, A], T]) -> None:
        """Wrap `build`, keeping its name and docstring."""
        self._build = build
        self._tables = digest_cached(DIGEST_CACHE_SIZE)(lambda _model: dict[Any, T]())
        functools.update_wrapper(self, build)

    def __call__(self, model: Model, *args: A.args, **kwargs: A.kwargs) -> T:
        """The result for `model` and `args`: held, or built now (an error is not held)."""
        table = self._tables(model)
        key = (args, tuple(sorted(kwargs.items())))
        if key not in table:
            table[key] = self._build(model, *args, **kwargs)
        return table[key]

    def cache_clear(self) -> None:
        """Forget every result: the next call of each digest builds again."""
        self._tables.cache_clear()
