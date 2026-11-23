"""The text a drawn symbol's tag label prints: a pin's, a terminal's point, a component's, or a run's strip tag."""

from typing import cast

from fransys_model.derive.designation import port_designation
from fransys_model.derive.facts.strips import strip_of
from fransys_model.derive.placement_reads import function_item, has_function, port_function
from fransys_model.derive.tag_text import run_point_text, strip_tag_text, tag_text
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Port, Unit

__all__ = ["printed_strip_tag", "printed_tag"]


def _function(model: Model, key: Id[Function] | Id[Port]) -> Id[Function] | None:
    """The key as a function when the model has it, else the function of a pin's port."""
    function = cast("Id[Function]", key)
    return function if has_function(model, function) else port_function(model, cast("Id[Port]", key))


def printed_tag(model: Model, key: Id[Function] | Id[Port], *, unit: Id[Unit] | None = None, alone: bool = False) -> str:
    """The tag a symbol of `key` (a function, or a connector pin's port) prints in the drawing set of `unit` (`None`: whole model).

    A pin prints its designation (`-X5:2`); a strip terminal its own point (`L2:1`), or, `alone` in its run, its full tag.
    """
    function = cast("Id[Function]", key)
    if not has_function(model, function):
        return port_designation(model, cast("Id[Port]", key), unit=unit)
    if alone or not strip_of(model, function_item(model, function)):
        return tag_text(model, function, unit=unit)
    return run_point_text(model, function)


def printed_strip_tag(model: Model, key: Id[Function] | Id[Port], *, unit: Id[Unit] | None = None) -> str:
    """The strip tag a run of the terminal `key` prints once above it (`-X1`, STRIP-TAG-ONCE)."""
    return strip_tag_text(model, cast("Id[Function]", _function(model, key)), unit=unit)
