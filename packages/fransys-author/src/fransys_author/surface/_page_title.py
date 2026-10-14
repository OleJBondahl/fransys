"""`d.layout.page_title` names the pages that draw a block, a function or a device."""

from typing import TYPE_CHECKING, Any

from fransys_author._keys import scoped
from fransys_author._origin import caller_origin
from fransys_author.errors import AuthorError
from fransys_author.handles import Group
from fransys_author.surface._device import Device
from fransys_author.surface._strip import TerminalStrip
lazy from fransys_author.handles import Terminal
lazy from fransys_author.surface._handles import Fn
lazy from fransys_model.kernel import make_id
lazy from fransys_model.layout import PageTitle

if TYPE_CHECKING:
    from fransys_author.design import Design as EngineDesign


def _thing(target: object) -> tuple[str, Any]:
    """`(field, engine handle)` of the thing `target` names; anything else is a refusal."""
    if isinstance(target, Group):
        return "block", target
    if isinstance(target, Fn):
        return "function", target._fn
    if isinstance(target, Device):
        return "item", target._item
    if isinstance(target, TerminalStrip):
        return "item", target._strip
    if isinstance(target, Terminal):
        return "item", target
    msg = f"d.layout.page_title takes a block, a function or a device, got {type(target).__name__}"
    raise AuthorError(msg)


def hint_page_title(engine: EngineDesign, target: object, text: str) -> None:
    """Write one `PageTitle` for `target`; an empty text or a second title on it is refused."""
    if not text.strip():
        msg = "d.layout.page_title: the title text is empty"
        raise AuthorError(msg)
    field, handle = _thing(target)
    for record in engine._design._draft.records():
        if isinstance(record, PageTitle) and getattr(record, field) == handle.id:
            msg = "d.layout.page_title: this thing already has a title; a thing takes one"
            raise AuthorError(msg)
    key = scoped(handle.key, "page_title")
    record = PageTitle(id=make_id(PageTitle, key), key=key, text=text, **{field: handle.id})
    engine._design._add(record, caller_origin())
