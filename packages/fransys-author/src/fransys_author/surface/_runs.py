"""What a terminal strip checks before it declares a named run (EA9)."""

from typing import Any

from fransys_author.errors import AuthorError

_PAIR = 2  # a bridged range is (first, last)


def check_run(strip: Any, label: object, count: object, bridged: object) -> None:  # noqa: ANN401 -- the strip imports this module, so it cannot be named here
    """Raise `AuthorError` for a bad `label`, `count` or `bridged`, or a label `strip` has."""
    named = f"{strip._tag}.run({label!r})"
    if not isinstance(label, str) or not label:
        msg = f"{strip._tag}.run: the label is a non-empty text, got {label!r}"
        raise AuthorError(msg)
    _check_count(named, count, bridged)
    if label in strip._runs:
        msg = f"{strip._tag} already has a run {label!r}"
        raise AuthorError(msg)
    strip._runs.add(label)


def _check_count(named: str, count: object, bridged: object) -> None:
    if count is None:
        _check_sizeless(named, bridged)
    elif isinstance(count, bool) or not isinstance(count, int) or count < 1:
        msg = f"{named}: the count is an integer from 1, got {count!r}"
        raise AuthorError(msg)
    else:
        _check_bridged(named, count, bridged)


def _check_bridged(named: str, count: int, bridged: object) -> None:
    """Raise `AuthorError` unless `bridged` is a bool or a `(first, last)` inside 1 to `count`."""
    if isinstance(bridged, bool):
        return
    if not (
        isinstance(bridged, tuple)
        and len(bridged) == _PAIR
        and all(type(number) is int for number in bridged)
    ):
        msg = f"{named}: bridged is True, False or a (first, last) pair, got {bridged!r}"
        raise AuthorError(msg)
    first, last = bridged
    if not 1 <= first < last <= count:
        msg = f"{named}: bridged=({first}, {last}) needs 1 <= first < last <= {count}"
        raise AuthorError(msg)


def _check_sizeless(named: str, bridged: object) -> None:
    """Raise `AuthorError` unless `bridged` is `True`: only a bridged run grows unsized (RS)."""
    if bridged is not True:
        msg = f"{named}: a run with no size is bridged=True; give the others a count"
        raise AuthorError(msg)
