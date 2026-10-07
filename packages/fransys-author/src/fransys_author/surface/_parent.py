"""What `d.device(..., parent=)` takes: a device or a strip, and a clear refusal for the rest."""

from typing import TYPE_CHECKING, cast

from fransys_author.errors import AuthorError
from fransys_author.handles import Item, Strip, Terminal

if TYPE_CHECKING:
    from fransys_author.surface.design import Design

_TAKES = "parent= takes a device or a strip"


def parent_item(design: Design, parent: object) -> Strip:
    """The strip to nest under, or an `AuthorError` naming what `parent=` takes (not a device)."""
    if isinstance(parent, Terminal):
        strip = design._engine._strip_key(parent)
        named = f"; give its strip {'/'.join(strip)}" if strip is not None else ""
        msg = f"{_TAKES}; a terminal is neither{named}"
        raise AuthorError(msg)
    as_parent = getattr(parent, "_as_parent", None)  # a strip says what it is; a run refuses
    if as_parent is None:
        msg = f"{_TAKES}, not a {type(parent).__name__}"
        raise AuthorError(msg)
    return cast("Strip", as_parent())


def cable_parent_item(parent: object) -> Item:
    """The device item a cable is fitted to, or an `AuthorError` naming what `parent=` takes."""
    item = getattr(parent, "_item", None)
    if item is None or isinstance(parent, Terminal):
        kind = {"TerminalStrip": "strip", "Run": "run", "Terminal": "terminal"}.get(
            type(parent).__name__, type(parent).__name__
        )
        msg = f"parent= takes a device, not a {kind}"
        raise AuthorError(msg)
    return cast("Item", item)
