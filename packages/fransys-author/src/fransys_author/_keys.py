"""Authoring keys: the scope's prefix plus segments the call chose, never a counter (0001)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey


def scoped(prefix: AuthoringKey, *segments: str) -> AuthoringKey:
    """`prefix` followed by `segments`: the key of one record a scope writes directly."""
    return (*prefix, *segments)


def spliced(key: AuthoringKey) -> str:
    """Fold `key` into one segment; length prefixes keep `("a/b", "c")` and `("a", "b/c")` apart."""
    return "/".join(f"{len(segment)}:{segment}" for segment in key)


def sorted_pair(a: AuthoringKey, b: AuthoringKey) -> list[AuthoringKey]:
    """The two keys in sorted order: one record key whichever end the caller names first."""
    return sorted((a, b))
