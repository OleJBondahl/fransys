"""The key of a kit pick: a function, or a connector pin keyed by its port (el-0014).

A function is drawn as one symbol; a connector draws one symbol per pin view, and the old engine
named that view by the port. Every other module reads the key through these functions.
"""

from typing import TYPE_CHECKING, cast

from fransys_model.derive import (
    function_item,
    function_ports,
    has_function,
    port_designation,
    port_function,
    run_point_text,
    strip_of,
    strip_tag_text,
    tag_text,
)

from .placement_kit import PickKey, refuse

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port, Unit

__all__ = ["PickKey", "function_of", "held_ports", "is_known", "strip_tag_of", "tag_of"]


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


def is_known(model: Model, key: PickKey) -> bool:
    """Whether `model` has the function or the port the key names."""
    return _function(model, key) is not None or port_function(model, cast("Id[Port]", key)) is not None


def tag_of(model: Model, key: PickKey, *, unit: Id[Unit] | None = None, alone: bool = False) -> str:
    """The tag a symbol prints: a pin's designation (`-X5:2`), a strip terminal's own point (`L2:1`) or, `alone` in its run, its full tag.

    The strip's designation is the run's, printed once above it (`strip_tag_of`, STRIP-TAG-ONCE).
    `unit` is the drawing set's unit: the text its own lists print (`None`: whole model).
    """
    function = _function(model, key)
    if function is None:
        return port_designation(model, cast("Id[Port]", key), unit=unit)
    if alone or not strip_of(model, function_item(model, function)):
        return tag_text(model, function, unit=unit)
    return run_point_text(model, function)


def strip_tag_of(model: Model, key: PickKey, *, unit: Id[Unit] | None = None) -> str:
    """The strip tag a run of the terminal `key` prints once above it (`-X1`)."""
    return strip_tag_text(model, function_of(model, key), unit=unit)
