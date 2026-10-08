"""A device with no part (PATCH-0132 E3): `d.device("Q8", None, external=True, pins=(...))`."""

from typing import TYPE_CHECKING

from fransys_author._origin import caller_origin
from fransys_author._partless import box_records, check_partless
from fransys_author.errors import AuthorError
from fransys_author.handles import _item_from_stamped

if TYPE_CHECKING:
    from fransys_author.design import Scope
    from fransys_author.handles import Item


def check_box(
    part: object, *, tag: str | None, external: bool, pins: tuple[str, ...] | None
) -> None:
    """Raise `AuthorError` unless `part` and `pins` agree: `None` needs pins, a part has its own."""
    if part is not None:
        if pins is not None:
            msg = "pins= is for a device with no part; a part names its own pins"
            raise AuthorError(msg)
        return
    check_partless(tag, external=external, call="d.device")
    if pins is None:
        msg = "a device with no part needs pins=: the pin names its box draws"
        raise AuthorError(msg)


def with_box(scope: Scope, item: Item, pins: tuple[str, ...]) -> Item:
    """`item` (part-less) with its one generic function and a port per pin, written to the draft."""
    records = box_records(item.id, item.key, pins)
    scope._design._extend(records, caller_origin())
    return _item_from_stamped(item.key, records, scope._design)
