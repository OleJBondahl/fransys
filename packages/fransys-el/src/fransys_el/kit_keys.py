"""The key of a kit pick: a function, or a connector pin keyed by its port (el-0014).

A function is drawn as one symbol; a connector draws one symbol per pin view, and the old engine
named that view by the port. Every other module reads the key through these functions.
"""

from typing import TYPE_CHECKING, cast

from electrical_symbols import GENERIC_BOX_KEY
from fransys_model.derive import (
    function_ports,
    function_scopes,
    has_function,
    port_function,
    port_is_unused,
)
from fransys_model.layout import profile_of

from .placement_kit import Pick, PickKey, refuse

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port

__all__ = ["PickKey", "box_ports", "function_of", "held_ports", "hidden_box_ports", "is_known"]


def _function(model: Model, key: PickKey) -> Id[Function] | None:
    """The key as a function when the model has it; a key that is none is a pin's port."""
    as_function = cast("Id[Function]", key)
    return as_function if has_function(model, as_function) else None


def function_of(model: Model, key: PickKey) -> Id[Function]:
    """The function a key draws: itself, or the function of a pin's port."""
    found = _function(model, key) or port_function(model, cast("Id[Port]", key))
    if found is None:
        refuse(f"the model has no function or port {key}", "pick only keys the model has", str(key))
    return found


def held_ports(model: Model, key: PickKey) -> tuple[Id[Port], ...]:
    """The model ports a key's symbol draws: a function's, or the one port of a pin."""
    function = _function(model, key)
    return (cast("Id[Port]", key),) if function is None else function_ports(model, function)


def box_ports(model: Model, key: PickKey) -> tuple[Id[Port], ...]:
    """The ports a generic box draws for a function key: all, but the unused ones where its unit hides them (`derive.port_is_unused`)."""
    function = function_of(model, key)
    ports = function_ports(model, function)
    if not profile_of(model, function_scopes(model, function)[0][0]).hide_unused_pins:
        return ports
    return tuple(p for p in ports if not port_is_unused(model, p))


def hidden_box_ports(model: Model, kit: Mapping[PickKey, Pick]) -> frozenset[Id[Port]]:
    """The ports a generic box of `kit` leaves off as unused (`box_ports`): no pin stands for them, so they are undrawn."""
    return frozenset(
        p
        for key, pick in kit.items()
        if pick.key == GENERIC_BOX_KEY
        for f in (key, *pick.members)
        for p in set(held_ports(model, f)) - set(box_ports(model, f))
    )


def is_known(model: Model, key: PickKey) -> bool:
    """Whether `model` has the function or the port the key names."""
    return _function(model, key) is not None or port_function(model, cast("Id[Port]", key)) is not None
