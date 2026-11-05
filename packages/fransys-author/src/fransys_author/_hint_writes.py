"""The author-side writes of a placement.

Types come from `handles` only for annotation, so this module never imports it at run time.
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import AuthoringKey, Id, make_id
from fransys_model.vocab import Item as ModelItem
from fransys_model.vocab import Placement

from ._keys import scoped

if TYPE_CHECKING:
    from fransys_model.kernel import Origin

    from .handles import Group, Location, _Recorder


def _write_placement(
    recorder: _Recorder,
    item_id: Id[ModelItem],
    item_key: AuthoringKey,
    node: Location | Group,
    origin: Origin,
) -> None:
    """One `placement` of `item_id` at `node`, a `+` or `=` node (`group=` on an item)."""
    key = scoped(item_key, "at", *node.key)
    placement = Placement(id=make_id(Placement, key), key=key, item=item_id, node=node.id)
    recorder._add(placement, origin)
