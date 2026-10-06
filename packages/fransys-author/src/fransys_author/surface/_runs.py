"""What a terminal strip checks before it declares a named run (EA9)."""

from typing import Any

from fransys_author.errors import AuthorError


def check_run(strip: Any, label: object, count: object, bridged: object) -> None:  # noqa: ANN401 -- the strip imports this module, so it cannot be named here
    """Raise `AuthorError` for a bad `label`, `count` or `bridged`, or a label `strip` has."""
    named = f"{strip._tag}.run({label!r})"
    if not isinstance(label, str) or not label:
        msg = f"{strip._tag}.run: the label is a non-empty text, got {label!r}"
        raise AuthorError(msg)
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        msg = f"{named}: the count is an integer from 1, got {count!r}"
        raise AuthorError(msg)
    if not isinstance(bridged, bool):
        msg = f"{named}: bridged is True or False, got {bridged!r}"
        raise AuthorError(msg)
    if label in strip._runs:
        msg = f"{strip._tag} already has a run {label!r}"
        raise AuthorError(msg)
    strip._runs.add(label)
