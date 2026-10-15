"""The three author-side writes of a layout hint or a placement (`d.draw_in`, `d.layout.side`).

Types come from `handles` only for annotation, so this module never imports it at run time.
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import AuthoringKey, Id, make_id
from fransys_model.layout import GroupHint, Side, SideHint
from fransys_model.vocab import Item as ModelItem
from fransys_model.vocab import Placement

from ._keys import scoped

if TYPE_CHECKING:
    from fransys_model.kernel import Origin

    from .handles import Fn, Group, Location, _Recorder


def _write_group_hint(recorder: _Recorder, function: Fn, group: Group, origin: Origin) -> None:
    """Write one `layout.group_hint` for `function` (`d.draw_in`)."""
    key = scoped(function.key, "group_hint")
    hint = GroupHint(id=make_id(GroupHint, key), key=key, function=function.id, group=group.id)
    recorder._add(hint, origin)


def _write_side_hint(recorder: _Recorder, function: Fn, side: Side, origin: Origin) -> None:
    """Write one `layout.side_hint` for the boundary `function` (model-0177, `d.layout.side`)."""
    key = scoped(function.key, "side_hint")
    hint = SideHint(id=make_id(SideHint, key), key=key, function=function.id, side=side)
    recorder._add(hint, origin)


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
