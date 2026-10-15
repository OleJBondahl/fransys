"""The one function of k poles on a carrier, else the error that names which."""

from typing import TYPE_CHECKING
lazy from collections.abc import Callable

from fransys_author.errors import AuthorError
from fransys_author.surface._pairing import NO_SIDE_FIX

if TYPE_CHECKING:
    from fransys_author.handles import Fn


def _device_error(label: str, k: int | None, counts: list[tuple[Fn, int]]) -> str:
    fit = " and ".join(sorted(fn.name for fn, count in counts if count == k))
    have = [f"{fn.name} ({count})" for fn, count in counts if count]
    if fit:
        return f"{label}: {fit} both have poles, say which: {label}.<function> in the series"
    if not have:
        return f"{label} has no poles: {NO_SIDE_FIX}"
    return (
        f"{label} has no function of {k} poles; it has: {', '.join(have)}. "
        f"Name the function you mean ({label}.{have[0].split()[0]}), or wire its pins with "
        "d.detail.wire(pin, pin, wire=...)"
    )


def _mount_error(label: str, k: int | None, counts: list[tuple[Fn, int]], where: str) -> str:
    fit = " and ".join(sorted(fn.name for fn, count in counts if count == k))
    if fit:
        return f"{where} has {k} poles; {label} has {fit} with {k} poles: say which"
    has = ", ".join(sorted(f"{fn.name} ({count})" for fn, count in counts)) or "none"
    return (
        f"{where} has {k} poles; {label} has no function of {k} poles; it has: {has}. "
        "Mount it on a carrier function of that pole count"
    )


def carrier_function(
    fns: list[Fn], count: Callable[[Fn], int], k: int | None, label: str, mounted: str | None = None
) -> Fn:
    """The one of `fns` with `k` poles by `count`, else raise; `mounted` None: a series."""
    counts = [(fn, count(fn)) for fn in fns]
    found = [fn for fn, n in counts if n == k]
    if len(found) == 1:
        return found[0]
    msg = (
        _device_error(label, k, counts)
        if mounted is None
        else _mount_error(label, k, counts, mounted)
    )
    raise AuthorError(msg)
