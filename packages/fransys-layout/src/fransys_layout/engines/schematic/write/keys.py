"""The key table the writer reads instead of the model: a plain value.

`read/write_keys.py` builds it from the model's tables; the modules of `write/` import no
vocabulary and look up only here. The key prefix, the page id type and the real-function lookup
of a stage handle, which every record builder shares, live here too.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.defaults import ENGINE_NAME
from fransys_model.layout import PlacementView

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import AuthoringKey, Id

type PageId = tuple[int, int]

PREFIX = ("layout", ENGINE_NAME)


@dataclass(frozen=True, slots=True)
class WriteKeys:
    """Each table record's authoring key, and the facts a stage handle's real function needs."""

    function: Mapping[Id[Any], AuthoringKey]
    port: Mapping[Id[Any], AuthoringKey]
    conductor: Mapping[Id[Any], AuthoringKey]
    item: Mapping[Id[Any], AuthoringKey]
    unit: Mapping[Id[Any], AuthoringKey]
    aspect_node: Mapping[Id[Any], AuthoringKey]
    port_function: Mapping[Id[Any], Id[Any]]
    port_name: Mapping[Id[Any], str]
    item_function: Mapping[Id[Any], Id[Any]]
    # model-0220: each stage handle of a terminal's copy at a wire to the model's id
    copies: Mapping[Id[Any], Id[Any]] = frozendict()


def with_copies(keys: WriteKeys, copies: Mapping[Id[Any], Id[Any]]) -> WriteKeys:
    """`keys` that also name each copy's ports by its model port's key (model-0220)."""
    ports = {alias: keys.port[real] for alias, real in copies.items() if real in keys.port}
    return replace(keys, port={**keys.port, **ports}, copies=copies)


def real_id(keys: WriteKeys, handle: Id[Any]) -> Id[Any]:
    """The model's id of a stage handle: a copy's own, else itself."""
    return keys.copies.get(handle, handle)


def view_of(keys: WriteKeys, handle: Id[Any]) -> PlacementView:
    """The view a stage handle draws: an item view, a pin view (a port handle) or the function."""
    if handle in keys.item_function:
        return PlacementView.ITEM
    return PlacementView.PIN if handle in keys.port_function else PlacementView.FUNCTION


def real_function(keys: WriteKeys, handle: Id[Any]) -> tuple[Id[Any], str | None]:
    """A stage handle's real function, and its pin name when the handle is a pin view."""
    handle = real_id(keys, handle)
    if handle in keys.item_function:  # An item view stands on the item's first function
        return keys.item_function[handle], None
    function = keys.port_function.get(handle)
    if function is None:
        return handle, None
    return function, keys.port_name[handle]
