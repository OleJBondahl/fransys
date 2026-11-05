"""The names a net goes by in the router and the reference planner: one home each (layout-0394).

`net_of_key` is the net a wire or fan key carries. `port_key` is the net a pin's end is marked under,
so the router never reads a net's own port end as foreign. `is_lone_cut` is the one predicate for a
cut end alone on its net (R499), read by the fan and the stub.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .values import PinRef


def net_of_key(key: str) -> str:
    """A bundle trunk or fan key `f:N` carries net N: its stems end on it by the bundle convention."""
    return key.removeprefix("f:")


def port_key(net_of: Mapping[PinRef, str], pin: PinRef) -> str:
    """The net of a wired pin, as its wires carry it; a pin of no net gets a sentinel (C12)."""
    return net_of.get(pin) or f"pin:{pin.sym}.{pin.pin}"


def is_lone_cut(*, is_cut: bool, pin_count: int) -> bool:
    """A cut end alone on its net: a bundle fan may take it as a lane (R499)."""
    return is_cut and pin_count == 1
